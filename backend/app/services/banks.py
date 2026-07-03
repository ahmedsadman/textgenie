from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.constants import CREDIT, DEPOSIT
from app.models import Bank, User
from app.schemas import BankCreateRequest, BankUpdateRequest


def list_banks(db: DBSession, user: User) -> list[Bank]:
    return db.query(Bank).filter(Bank.user_id == user.id).order_by(Bank.name).all()


def get_bank_by_name(db: DBSession, user_id: int, name: str) -> Bank | None:
    return (
        db.query(Bank)
        .filter(Bank.user_id == user_id, func.lower(Bank.name) == name.strip().lower())
        .first()
    )


def create_bank(db: DBSession, user: User, data: BankCreateRequest) -> Bank:
    name = data.name.strip()
    if get_bank_by_name(db, user.id, name):
        raise HTTPException(status_code=409, detail="Bank already exists")

    # BankCreateRequest guarantees credit ⇒ card_digits and deposit ⇒ no card_digits.
    bank = Bank(
        name=name,
        user_id=user.id,
        account_type=data.account_type,
        card_digits=data.card_digits,
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


def update_bank(
    db: DBSession, user: User, bank_id: int, data: BankUpdateRequest
) -> Bank:
    """PATCH semantics: only fields present in `data` are applied.

    Same-request shape conflicts (credit+last_balance, deposit+card_digits) are
    caught upstream by BankUpdateRequest.
    """
    bank = db.query(Bank).filter(Bank.id == bank_id, Bank.user_id == user.id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    # The type the bank will have after this PATCH.
    effective_type = data.account_type or bank.account_type

    if data.name is not None:
        name = data.name.strip()
        conflict = (
            db.query(Bank)
            .filter(
                Bank.user_id == user.id,
                func.lower(Bank.name) == name.lower(),
                Bank.id != bank_id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(status_code=409, detail="Bank already exists")
        bank.name = name

    if data.last_balance is not None:
        if effective_type == CREDIT:
            raise HTTPException(
                status_code=400,
                detail="Credit accounts cannot have a balance",
            )
        bank.last_balance = data.last_balance
        bank.last_balance_at = datetime.now(timezone.utc)

    if data.card_digits is not None:
        if effective_type == DEPOSIT:
            raise HTTPException(
                status_code=400,
                detail="Deposit accounts cannot have a card number",
            )
        bank.card_digits = data.card_digits

    # Type flip: enforce the destination's invariants and clear the field that
    # no longer belongs. Idempotent when the type is unchanged.
    if data.account_type is not None:
        if data.account_type == CREDIT:
            if not bank.card_digits:
                raise HTTPException(
                    status_code=400,
                    detail="Credit accounts require a card number",
                )
            bank.last_balance = None
            bank.last_balance_at = None
        else:
            bank.card_digits = None
        bank.account_type = data.account_type

    db.commit()
    db.refresh(bank)
    return bank


def delete_bank(db: DBSession, user: User, bank_id: int) -> None:
    bank = db.query(Bank).filter(Bank.id == bank_id, Bank.user_id == user.id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    db.delete(bank)
    db.commit()
