from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models import Bank, Bill, Message, Transaction, User
from app.schemas import BillResponse


def list_bills(
    db: DBSession,
    user: User,
    *,
    page: int,
    page_size: int,
    bank_id: int | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> tuple[list[BillResponse], int]:
    base = (
        db.query(Bill)
        .join(Message, Message.id == Bill.message_id)
        .filter(Bill.user_id == user.id)
    )
    if bank_id is not None:
        base = base.filter(Bill.bank_id == bank_id)
    if from_date is not None:
        base = base.filter(Message.received_at >= from_date)
    if to_date is not None:
        base = base.filter(Message.received_at <= to_date)

    total = base.with_entities(func.count(Bill.id)).scalar() or 0

    offset = (page - 1) * page_size
    rows = (
        base.outerjoin(Bank, Bank.id == Bill.bank_id)
        .with_entities(
            Bill.id,
            Bill.message_id,
            Message.sender,
            Message.received_at,
            Bill.bank_id,
            Bank.name.label("bank_name"),
            Bill.normalized_total_due,
            Bill.normalized_currency,
            Bill.original_amount,
            Bill.original_currency,
            Bill.statement_period,
            Bill.paid_at,
            Bill.created_at,
        )
        .order_by(Message.received_at.desc(), Bill.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    if not rows:
        return [], total

    bill_ids = [r.id for r in rows]
    link_rows = (
        db.query(Transaction.bill_id, Transaction.id)
        .filter(Transaction.bill_id.in_(bill_ids))
        .all()
    )
    links: dict[int, list[int]] = {bid: [] for bid in bill_ids}
    for bill_id, tx_id in link_rows:
        links[bill_id].append(tx_id)

    bills = [_row_to_response(row, links.get(row.id, [])) for row in rows]
    return bills, total


def get_bill(db: DBSession, user: User, bill_id: int) -> BillResponse:
    row = (
        db.query(Bill)
        .join(Message, Message.id == Bill.message_id)
        .outerjoin(Bank, Bank.id == Bill.bank_id)
        .filter(Bill.id == bill_id, Bill.user_id == user.id)
        .with_entities(
            Bill.id,
            Bill.message_id,
            Message.sender,
            Message.received_at,
            Bill.bank_id,
            Bank.name.label("bank_name"),
            Bill.normalized_total_due,
            Bill.normalized_currency,
            Bill.original_amount,
            Bill.original_currency,
            Bill.statement_period,
            Bill.paid_at,
            Bill.created_at,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Bill not found")

    link_ids = [
        tx_id
        for (tx_id,) in db.query(Transaction.id)
        .filter(Transaction.bill_id == row.id)
        .all()
    ]
    return _row_to_response(row, link_ids)


def unlink_transactions(
    db: DBSession, user: User, bill_id: int, tx_ids: list[int]
) -> BillResponse:
    bill = db.query(Bill).filter(Bill.id == bill_id, Bill.user_id == user.id).first()
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found")

    if tx_ids:
        transactions = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user.id,
                Transaction.id.in_(tx_ids),
                Transaction.bill_id == bill.id,
            )
            .all()
        )
        for tx in transactions:
            tx.bill_id = None
            if tx.paired_with_id is not None:
                counterpart = (
                    db.query(Transaction)
                    .filter(Transaction.id == tx.paired_with_id)
                    .first()
                )
                if counterpart is not None and counterpart.bill_id == bill.id:
                    counterpart.bill_id = None

    remaining = (
        db.query(func.count(Transaction.id))
        .filter(Transaction.bill_id == bill.id)
        .scalar()
        or 0
    )
    if remaining == 0:
        bill.paid_at = None

    db.commit()
    return get_bill(db, user, bill_id)


def _row_to_response(row, linked_transaction_ids: list[int]) -> BillResponse:
    return BillResponse(
        id=row.id,
        message_id=row.message_id,
        sender=row.sender,
        received_at=row.received_at,
        bank_id=row.bank_id,
        bank_name=row.bank_name,
        normalized_total_due=row.normalized_total_due,
        normalized_currency=row.normalized_currency,
        original_amount=row.original_amount,
        original_currency=row.original_currency,
        statement_period=row.statement_period,
        paid_at=row.paid_at,
        linked_transaction_ids=linked_transaction_ids,
        created_at=row.created_at,
    )
