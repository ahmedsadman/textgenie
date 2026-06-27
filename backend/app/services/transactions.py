from datetime import datetime
from decimal import Decimal

from sqlalchemy import case, func
from sqlalchemy.orm import Session as DBSession

from app.models import Bank, Message, Transaction, User
from app.schemas import TransactionResponse, TransactionTotals


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


def list_transactions(
    db: DBSession,
    user: User,
    *,
    page: int,
    page_size: int,
    from_date: datetime | None,
    to_date: datetime | None,
) -> tuple[list[TransactionResponse], int, TransactionTotals]:
    base = _base_query(db, user, from_date, to_date)

    total = base.with_entities(func.count(Transaction.id)).scalar() or 0

    sums = base.with_entities(
        func.coalesce(
            func.sum(case((Transaction.type == "income", Transaction.amount), else_=0)),
            0,
        ).label("income"),
        func.coalesce(
            func.sum(
                case((Transaction.type == "expense", Transaction.amount), else_=0)
            ),
            0,
        ).label("expense"),
    ).one()
    totals = TransactionTotals(
        income=Decimal(str(sums.income)),
        expense=Decimal(str(sums.expense)),
    )

    offset = (page - 1) * page_size
    rows = (
        _base_query(db, user, from_date, to_date)
        .join(Message, Message.id == Transaction.message_id)
        .outerjoin(Bank, Bank.id == Transaction.bank_id)
        .with_entities(
            Transaction.id,
            Transaction.message_id,
            Transaction.bank_id,
            Bank.name.label("bank_name"),
            Message.sender,
            Transaction.amount,
            Transaction.type,
            Transaction.date,
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    transactions = [
        TransactionResponse(
            id=row.id,
            message_id=row.message_id,
            bank_id=row.bank_id,
            bank_name=row.bank_name,
            sender=row.sender,
            amount=row.amount,
            type=row.type,
            date=row.date,
        )
        for row in rows
    ]

    return transactions, total, totals
