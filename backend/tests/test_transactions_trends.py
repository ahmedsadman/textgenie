from datetime import datetime, timezone

from app.models import User
from tests.conftest import register_and_login
from tests.factories import make_transaction


def _trends(client):
    return client.get("/api/transactions/trends")


def _current_user(db):
    return db.query(User).first()


def _month_dt(offset: int, day: int = 15) -> datetime:
    """A datetime `offset` calendar months from the current month.

    Trend windows are computed relative to *today*, so tests seed data by
    month offset rather than fixed dates. recent = [-3, -2, -1],
    prior = [-6, -5, -4], and the current (partial) month (offset 0) is
    excluded from every window.
    """
    now = datetime.now(timezone.utc)
    total = now.year * 12 + (now.month - 1) + offset
    year, month = divmod(total, 12)
    return datetime(year, month + 1, day, tzinfo=timezone.utc)


def _month_first_iso(offset: int) -> str:
    return _month_dt(offset, day=1).date().isoformat()


def _seed_months(db, user, offsets, *, type, amount):
    for offset in offsets:
        make_transaction(db, user, amount=amount, type=type, date=_month_dt(offset))


PRIOR = (-6, -5, -4)
RECENT = (-3, -2, -1)


def test_trends_no_transactions_returns_new_zeros(client, db):
    register_and_login(client)
    body = _trends(client).json()

    assert body["window_months"] == 3
    assert len(body["spark_months"]) == 6
    assert body["income"] == {
        "recent_avg": "0.00",
        "prior_avg": "0.00",
        "change_pct": None,
        "direction": "new",
        "spark": ["0.00"] * 6,
    }
    assert body["savings_rate"] == {
        "recent": None,
        "prior": None,
        "change_pp": None,
        "direction": "new",
        "spark": [None] * 6,
    }


def test_trends_spark_months_are_last_six_complete_months(client, db):
    register_and_login(client)
    body = _trends(client).json()
    expected = [_month_first_iso(o) for o in range(-6, 0)]
    assert body["spark_months"] == expected


def test_trends_income_up(client, db):
    register_and_login(client)
    user = _current_user(db)
    _seed_months(db, user, PRIOR, type="income", amount="4000.00")
    _seed_months(db, user, RECENT, type="income", amount="5000.00")

    income = _trends(client).json()["income"]
    assert income["recent_avg"] == "5000.00"
    assert income["prior_avg"] == "4000.00"
    assert income["change_pct"] == "25.0"
    assert income["direction"] == "up"


def test_trends_spend_up_is_red_worthy_direction(client, db):
    register_and_login(client)
    user = _current_user(db)
    _seed_months(db, user, PRIOR, type="expense", amount="1000.00")
    _seed_months(db, user, RECENT, type="expense", amount="1200.00")

    spend = _trends(client).json()["spend"]
    assert spend["recent_avg"] == "1200.00"
    assert spend["prior_avg"] == "1000.00"
    assert spend["change_pct"] == "20.0"
    assert spend["direction"] == "up"


def test_trends_small_change_reads_as_flat(client, db):
    register_and_login(client)
    user = _current_user(db)
    _seed_months(db, user, PRIOR, type="income", amount="5000.00")
    _seed_months(db, user, RECENT, type="income", amount="5050.00")

    income = _trends(client).json()["income"]
    assert income["change_pct"] == "1.0"  # below the 2% flat band
    assert income["direction"] == "flat"


def test_trends_empty_prior_is_new(client, db):
    register_and_login(client)
    user = _current_user(db)
    _seed_months(db, user, RECENT, type="income", amount="5000.00")

    income = _trends(client).json()["income"]
    assert income["direction"] == "new"
    assert income["change_pct"] is None
    # In-history divisor: recent counts only the 3 real months, not padded.
    assert income["recent_avg"] == "5000.00"


def test_trends_thin_prior_is_new(client, db):
    register_and_login(client)
    user = _current_user(db)
    # Only one in-history prior month (offset -4); prior needs >= 2 to trust.
    _seed_months(db, user, (-4,), type="income", amount="4000.00")
    _seed_months(db, user, RECENT, type="income", amount="5000.00")

    income = _trends(client).json()["income"]
    assert income["direction"] == "new"
    assert income["change_pct"] is None


def test_trends_in_history_divisor_new_user_headline_not_understated(client, db):
    register_and_login(client)
    user = _current_user(db)
    # Only one month of history: headline must be 5000, not 5000/3.
    _seed_months(db, user, (-1,), type="income", amount="5000.00")

    income = _trends(client).json()["income"]
    assert income["recent_avg"] == "5000.00"
    assert income["direction"] == "new"


def test_trends_five_month_user_gets_accurate_badge_not_inflated(client, db):
    register_and_login(client)
    user = _current_user(db)
    # First txn at offset -5: prior window [-6,-5,-4] has 2 in-history months.
    # Income is flat 5000 every month -> steady, NOT a fake +50% from a
    # pre-history zero at -6 dragging the prior average.
    _seed_months(db, user, (-5, -4, -3, -2, -1), type="income", amount="5000.00")

    income = _trends(client).json()["income"]
    assert income["prior_avg"] == "5000.00"
    assert income["recent_avg"] == "5000.00"
    assert income["change_pct"] == "0.0"
    assert income["direction"] == "flat"


def test_trends_savings_rate_up(client, db):
    register_and_login(client)
    user = _current_user(db)
    for offset in PRIOR:
        make_transaction(
            db, user, amount="1000.00", type="income", date=_month_dt(offset)
        )
        make_transaction(
            db, user, amount="800.00", type="expense", date=_month_dt(offset)
        )
    for offset in RECENT:
        make_transaction(
            db, user, amount="1000.00", type="income", date=_month_dt(offset)
        )
        make_transaction(
            db, user, amount="700.00", type="expense", date=_month_dt(offset)
        )

    rate = _trends(client).json()["savings_rate"]
    assert rate["prior"] == "0.2000"
    assert rate["recent"] == "0.3000"
    assert rate["change_pp"] == "10.0"
    assert rate["direction"] == "up"


def test_trends_savings_rate_spark_negative_and_zero_income(client, db):
    register_and_login(client)
    user = _current_user(db)
    # -6: income 0, expense 100 -> rate spark None (zero income)
    make_transaction(db, user, amount="100.00", type="expense", date=_month_dt(-6))
    # -5: income 100, expense 150 -> rate spark -0.5 (spent more than earned)
    make_transaction(db, user, amount="100.00", type="income", date=_month_dt(-5))
    make_transaction(db, user, amount="150.00", type="expense", date=_month_dt(-5))

    spark = _trends(client).json()["savings_rate"]["spark"]
    assert len(spark) == 6
    assert spark[0] is None  # -6, zero income
    assert spark[1] == "-0.5000"  # -5, negative rate


def test_trends_excludes_transfers(client, db):
    register_and_login(client)
    user = _current_user(db)
    _seed_months(db, user, RECENT, type="income", amount="1000.00")
    # A transfer must not inflate income nor stretch the history span.
    make_transaction(db, user, amount="9999.00", type="transfer", date=_month_dt(-1))
    make_transaction(db, user, amount="9999.00", type="transfer", date=_month_dt(-6))

    income = _trends(client).json()["income"]
    assert income["recent_avg"] == "1000.00"
    # first_month is the earliest income/expense (-3), so prior stays empty.
    assert income["direction"] == "new"


def test_trends_current_partial_month_excluded(client, db):
    register_and_login(client)
    user = _current_user(db)
    _seed_months(db, user, RECENT, type="income", amount="1000.00")
    # Huge current-month income must not leak into the recent window.
    make_transaction(db, user, amount="99999.00", type="income", date=_month_dt(0))

    income = _trends(client).json()["income"]
    assert income["recent_avg"] == "1000.00"
    assert "99999" not in "".join(income["spark"])


def test_trends_isolated_by_user(client, db):
    register_and_login(client, email="user1@example.com")
    user1 = db.query(User).filter(User.email == "user1@example.com").first()
    _seed_months(db, user1, RECENT, type="income", amount="1000.00")

    register_and_login(client, email="user2@example.com")
    income = _trends(client).json()["income"]
    assert income["recent_avg"] == "0.00"
    assert income["direction"] == "new"


def test_trends_unauthenticated(client):
    assert _trends(client).status_code == 401
