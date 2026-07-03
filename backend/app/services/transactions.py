from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import case, func
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import aliased

from app.constants import TransactionType
from app.models import Bank, Message, Transaction, User
from app.schemas import (
    TransactionResponse,
    TransactionTotals,
)


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

    # Transfers are intentionally excluded from both totals (they are
    # neither real income nor real expense — just money moving between
    # the user's own accounts).
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

    paired = aliased(Transaction)
    offset = (page - 1) * page_size
    rows = (
        _base_query(db, user, from_date, to_date)
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
            Transaction.amount,
            Transaction.type,
            Transaction.date,
            Transaction.paired_with_id,
            paired.message_id.label("paired_with_message_id"),
        )
        .order_by(Transaction.date.desc(), Transaction.id.desc())
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
            Transaction.amount,
            Transaction.type,
            Transaction.date,
            Transaction.paired_with_id,
            paired.message_id.label("paired_with_message_id"),
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

    if tx.type == "transfer" and tx.paired_with_id is not None:
        counterpart = (
            db.query(Transaction).filter(Transaction.id == tx.paired_with_id).first()
        )
        if counterpart is not None:
            counterpart.paired_with_id = None
        tx.paired_with_id = None

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
        amount=row.amount,
        type=row.type,
        date=row.date,
        paired_with_id=row.paired_with_id,
        paired_with_message_id=row.paired_with_message_id,
    )
