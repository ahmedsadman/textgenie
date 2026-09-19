from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Literal

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import aliased

from app.constants import TransactionType
from app.models import Bank, Message, Transaction, User
from app.schemas import (
    MonthlySummaryBucket,
    SavingsRateTrend,
    TransactionResponse,
    TransactionTotals,
    TransactionTrendsResponse,
    TrendMetric,
)

# Trend window sizing and the "flat" (no meaningful change) thresholds.
WINDOW_MONTHS = 3
SPARK_MONTHS = 6
FLAT_PCT = Decimal("2.0")  # income/spend: |change%| below this reads as steady
FLAT_PP = Decimal("1.0")  # savings rate: |change in points| below this is steady

_CENTS = Decimal("0.01")
_PCT = Decimal("0.1")
_RATE = Decimal("0.0001")
_ZERO_PAIR = (Decimal("0.00"), Decimal("0.00"))


def _base_query(
    db: DBSession,
    user: User,
    from_date: datetime | None,
    to_date: datetime | None,
):
    query = db.query(Transaction).filter(Transaction.user_id == user.id)
    if from_date is not None:
        query = query.filter(Transaction.date >= from_date)
    if to_date is not None:
        query = query.filter(Transaction.date <= to_date)
    return query


def _income_expense_sum_cols():
    """Labeled `income`/`expense` sum columns; transfers contribute 0.

    Used by the range totals in `list_transactions`.
    """
    income = func.coalesce(
        func.sum(
            case(
                (Transaction.type == "income", Transaction.normalized_amount),
                else_=0,
            )
        ),
        0,
    ).label("income")
    expense = func.coalesce(
        func.sum(
            case(
                (Transaction.type == "expense", Transaction.normalized_amount),
                else_=0,
            )
        ),
        0,
    ).label("expense")
    return income, expense


def _add_months(d: date, n: int) -> date:
    """First-of-month `n` months from `d` (`n` may be negative)."""
    total = d.year * 12 + (d.month - 1) + n
    year, month = divmod(total, 12)
    return date(year, month + 1, 1)


def _month_range(start: date, end: date):
    month = start
    while month <= end:
        yield month
        month = _add_months(month, 1)


def _monthly_income_expense(
    db: DBSession,
    user: User,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> dict[date, tuple[Decimal, Decimal]]:
    """Sum (income, expense) per calendar month, keyed by first-of-month.

    Transfers excluded. Only months with activity appear — callers gap-fill.
    Shared by the summary graph and the trends computation (DRY).
    """
    rows = (
        _base_query(db, user, from_date, to_date)
        .filter(Transaction.type.in_(("income", "expense")))
        .with_entities(
            Transaction.date,
            Transaction.type,
            Transaction.normalized_amount,
        )
        .all()
    )

    buckets: dict[date, list[Decimal]] = {}
    for tx_date, tx_type, amount in rows:
        d = tx_date.date()
        key = date(d.year, d.month, 1)
        bucket = buckets.setdefault(key, [Decimal("0.00"), Decimal("0.00")])
        if tx_type == "income":
            bucket[0] += amount
        else:
            bucket[1] += amount
    return {month: (inc, exp) for month, (inc, exp) in buckets.items()}


def monthly_summary(
    db: DBSession,
    user: User,
    from_date: datetime | None,
    to_date: datetime | None,
) -> list[MonthlySummaryBucket]:
    """Monthly-bucketed income/expense series with gap-filled months.

    Transfers are excluded (consistent with the totals behavior). When there
    is activity, every month between the lower and upper bound is emitted so
    the line stays continuous; months with no activity get income=0, expense=0.
    Returns an empty list when no income/expense transactions match — the
    caller renders an empty state rather than a flat zero line.
    """
    month_totals = _monthly_income_expense(db, user, from_date, to_date)
    if not month_totals:
        return []

    lower_month = (
        date(from_date.year, from_date.month, 1)
        if from_date is not None
        else min(month_totals)
    )
    upper_month = (
        date(to_date.year, to_date.month, 1)
        if to_date is not None
        else max(month_totals)
    )

    return [
        MonthlySummaryBucket(
            month_start=month,
            income=month_totals.get(month, _ZERO_PAIR)[0],
            expense=month_totals.get(month, _ZERO_PAIR)[1],
        )
        for month in _month_range(lower_month, upper_month)
    ]


def _direction(change: Decimal | None, flat: Decimal) -> str:
    """Map a signed change to a badge direction, honoring the flat band.

    `None` means the prior baseline was empty or too thin to trust — the
    clients render a "new" chip instead of claiming a trend.
    """
    if change is None:
        return "new"
    if abs(change) < flat:
        return "flat"
    return "up" if change > 0 else "down"


def _window_average(
    idx: int,
    window: list[date],
    month_totals: dict[date, tuple[Decimal, Decimal]],
    first_month: date | None,
) -> tuple[Decimal, int]:
    """Average of income (idx=0) or expense (idx=1) over the in-history months
    of `window`. Divides by the count of months at/after the user's first
    transaction, so pre-history zero months never drag the average down."""
    total = Decimal("0")
    n = 0
    for month in window:
        if first_month is None or month < first_month:
            continue
        n += 1
        total += month_totals.get(month, _ZERO_PAIR)[idx]
    avg = (total / n).quantize(_CENTS) if n else Decimal("0.00")
    return avg, n


def _window_rate(
    window: list[date],
    month_totals: dict[date, tuple[Decimal, Decimal]],
    first_month: date | None,
) -> tuple[Decimal | None, int]:
    """Aggregate savings rate (income-expense)/income over the in-history months
    of `window`. Returns (None, n) when window income is zero. The ratio is
    naturally immune to pre-history zero months (a zero month adds 0 to both
    sums)."""
    sum_income = Decimal("0")
    sum_expense = Decimal("0")
    n = 0
    for month in window:
        if first_month is None or month < first_month:
            continue
        n += 1
        inc, exp = month_totals.get(month, _ZERO_PAIR)
        sum_income += inc
        sum_expense += exp
    if sum_income == 0:
        return None, n
    return ((sum_income - sum_expense) / sum_income).quantize(_RATE), n


def _amount_metric(
    idx: int,
    recent_window: list[date],
    prior_window: list[date],
    spark_window: list[date],
    month_totals: dict[date, tuple[Decimal, Decimal]],
    first_month: date | None,
) -> TrendMetric:
    recent_avg, _ = _window_average(idx, recent_window, month_totals, first_month)
    prior_avg, prior_n = _window_average(idx, prior_window, month_totals, first_month)
    if prior_n < 2 or prior_avg == 0:
        change_pct = None
    else:
        change_pct = ((recent_avg - prior_avg) / prior_avg * 100).quantize(_PCT)
    return TrendMetric(
        recent_avg=recent_avg,
        prior_avg=prior_avg,
        change_pct=change_pct,
        direction=_direction(change_pct, FLAT_PCT),
        spark=[
            month_totals.get(m, _ZERO_PAIR)[idx].quantize(_CENTS) for m in spark_window
        ],
    )


def _savings_rate_trend(
    recent_window: list[date],
    prior_window: list[date],
    spark_window: list[date],
    month_totals: dict[date, tuple[Decimal, Decimal]],
    first_month: date | None,
) -> SavingsRateTrend:
    recent, _ = _window_rate(recent_window, month_totals, first_month)
    prior, prior_n = _window_rate(prior_window, month_totals, first_month)
    if prior is None or recent is None or prior_n < 2:
        change_pp = None
    else:
        change_pp = ((recent - prior) * 100).quantize(_PCT)
    spark: list[Decimal | None] = []
    for month in spark_window:
        inc, exp = month_totals.get(month, _ZERO_PAIR)
        spark.append(((inc - exp) / inc).quantize(_RATE) if inc > 0 else None)
    return SavingsRateTrend(
        recent=recent,
        prior=prior,
        change_pp=change_pp,
        direction=_direction(change_pp, FLAT_PP),
        spark=spark,
    )


def spending_trends(db: DBSession, user: User) -> TransactionTrendsResponse:
    """3-month trend view: income/mo, spend/mo and savings rate — each with a
    recent-vs-prior badge and a SPARK_MONTHS sparkline. Windows are the last
    complete calendar months (the current partial month is excluded)."""
    month_totals = _monthly_income_expense(db, user)
    first_month = min(month_totals) if month_totals else None

    today = datetime.now(timezone.utc).date()
    current_month = date(today.year, today.month, 1)
    # Oldest -> newest, excluding the current partial month.
    spark_window = [
        _add_months(current_month, offset) for offset in range(-SPARK_MONTHS, 0)
    ]
    prior_window = spark_window[:WINDOW_MONTHS]
    recent_window = spark_window[WINDOW_MONTHS:]

    return TransactionTrendsResponse(
        window_months=WINDOW_MONTHS,
        spark_months=spark_window,
        income=_amount_metric(
            0, recent_window, prior_window, spark_window, month_totals, first_month
        ),
        spend=_amount_metric(
            1, recent_window, prior_window, spark_window, month_totals, first_month
        ),
        savings_rate=_savings_rate_trend(
            recent_window, prior_window, spark_window, month_totals, first_month
        ),
    )


def list_transactions(
    db: DBSession,
    user: User,
    *,
    page: int,
    page_size: int,
    from_date: datetime | None,
    to_date: datetime | None,
    types: list[TransactionType] | None = None,
    sort_by: Literal["date", "amount"] = "date",
    sort_dir: Literal["asc", "desc"] = "desc",
) -> tuple[list[TransactionResponse], int, TransactionTotals]:
    base = _base_query(db, user, from_date, to_date)

    # Totals scoped to date range only; type filter ignored; transfers excluded.
    income_col, expense_col = _income_expense_sum_cols()
    sums = base.with_entities(income_col, expense_col).one()
    totals = TransactionTotals(
        income=Decimal(str(sums.income)),
        expense=Decimal(str(sums.expense)),
    )

    filtered = base
    if types:
        filtered = filtered.filter(Transaction.type.in_(types))

    total = filtered.with_entities(func.count(Transaction.id)).scalar() or 0

    primary_col = (
        Transaction.normalized_amount if sort_by == "amount" else Transaction.date
    )
    primary_order = primary_col.asc() if sort_dir == "asc" else primary_col.desc()

    paired = aliased(Transaction)
    offset = (page - 1) * page_size
    rows = (
        filtered.join(Message, Message.id == Transaction.message_id)
        .outerjoin(Bank, Bank.id == Transaction.bank_id)
        .outerjoin(paired, paired.id == Transaction.paired_with_id)
        .with_entities(
            Transaction.id,
            Transaction.message_id,
            Transaction.bank_id,
            Bank.name.label("bank_name"),
            Bank.account_type.label("bank_account_type"),
            Message.sender,
            Transaction.normalized_amount,
            Transaction.normalized_currency,
            Transaction.original_amount,
            Transaction.original_currency,
            Transaction.type,
            Transaction.date,
            Transaction.paired_with_id,
            paired.message_id.label("paired_with_message_id"),
            Transaction.bill_id,
        )
        .order_by(primary_order, Transaction.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    transactions = [_row_to_response(row) for row in rows]

    return transactions, total, totals


def get_transaction_response(
    db: DBSession, user: User, transaction_id: int
) -> TransactionResponse:
    """Fetch a single transaction in the same shape as list_transactions."""
    paired = aliased(Transaction)
    row = (
        db.query(Transaction)
        .filter(Transaction.user_id == user.id, Transaction.id == transaction_id)
        .join(Message, Message.id == Transaction.message_id)
        .outerjoin(Bank, Bank.id == Transaction.bank_id)
        .outerjoin(paired, paired.id == Transaction.paired_with_id)
        .with_entities(
            Transaction.id,
            Transaction.message_id,
            Transaction.bank_id,
            Bank.name.label("bank_name"),
            Bank.account_type.label("bank_account_type"),
            Message.sender,
            Transaction.normalized_amount,
            Transaction.normalized_currency,
            Transaction.original_amount,
            Transaction.original_currency,
            Transaction.type,
            Transaction.date,
            Transaction.paired_with_id,
            paired.message_id.label("paired_with_message_id"),
            Transaction.bill_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _row_to_response(row)


def update_transaction(
    db: DBSession, user: User, transaction_id: int, new_type: TransactionType
) -> TransactionResponse:
    """Change a transaction's type. When flipping AWAY from 'transfer'
    while paired, unlink both sides (but leave the counterpart's type
    alone — the user only spoke for this side)."""
    tx = (
        db.query(Transaction)
        .filter(
            Transaction.id == transaction_id,
            Transaction.user_id == user.id,
        )
        .first()
    )
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if tx.type == new_type:
        return get_transaction_response(db, user, transaction_id)

    if tx.type == "transfer":
        counterpart = None
        if tx.paired_with_id is not None:
            counterpart = (
                db.query(Transaction)
                .filter(Transaction.id == tx.paired_with_id)
                .first()
            )
            if counterpart is not None:
                counterpart.paired_with_id = None
                counterpart.bill_id = None
            tx.paired_with_id = None
        tx.bill_id = None

    tx.type = new_type
    db.commit()
    return get_transaction_response(db, user, transaction_id)


def _row_to_response(row) -> TransactionResponse:
    return TransactionResponse(
        id=row.id,
        message_id=row.message_id,
        bank_id=row.bank_id,
        bank_name=row.bank_name,
        bank_account_type=row.bank_account_type,
        sender=row.sender,
        normalized_amount=row.normalized_amount,
        normalized_currency=row.normalized_currency,
        original_amount=row.original_amount,
        original_currency=row.original_currency,
        type=row.type,
        date=row.date,
        paired_with_id=row.paired_with_id,
        paired_with_message_id=row.paired_with_message_id,
        bill_id=row.bill_id,
    )
