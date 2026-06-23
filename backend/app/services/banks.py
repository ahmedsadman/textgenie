from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models import Bank, User
from app.schemas import BankCreateRequest, BankUpdateRequest


def list_banks(db: DBSession, user: User) -> list[Bank]:
    return db.query(Bank).filter(Bank.user_id == user.id).order_by(Bank.name).all()


def total_balance(banks: list[Bank]) -> Decimal:
    return sum(
        (b.last_balance for b in banks if b.last_balance is not None),
        start=Decimal("0"),
    )


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

    bank = Bank(name=name, user_id=user.id)
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


def update_bank(
    db: DBSession, user: User, bank_id: int, data: BankUpdateRequest
) -> Bank:
    bank = db.query(Bank).filter(Bank.id == bank_id, Bank.user_id == user.id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

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
        bank.last_balance = data.last_balance
        bank.last_balance_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(bank)
    return bank


def delete_bank(db: DBSession, user: User, bank_id: int) -> None:
    bank = db.query(Bank).filter(Bank.id == bank_id, Bank.user_id == user.id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    db.delete(bank)
    db.commit()
