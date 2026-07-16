import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.constants import CREDIT, DEPOSIT, AccountType
from app.models import Bank, User
from app.schemas import BankCreateRequest, BankUpdateRequest

logger = logging.getLogger(__name__)


def list_banks(db: DBSession, user: User) -> list[Bank]:
    return db.query(Bank).filter(Bank.user_id == user.id).order_by(Bank.name).all()


def get_bank_by_name(db: DBSession, user_id: int, name: str) -> Bank | None:
    return (
        db.query(Bank)
        .filter(Bank.user_id == user_id, func.lower(Bank.name) == name.strip().lower())
        .first()
    )


def _get_user_bank_or_404(db: DBSession, user_id: int, bank_id: int) -> Bank:
    bank = db.query(Bank).filter(Bank.id == bank_id, Bank.user_id == user_id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
    return bank


def _ensure_name_available(
    db: DBSession, user_id: int, name: str, exclude_id: int | None = None
) -> None:
    query = db.query(Bank).filter(
        Bank.user_id == user_id, func.lower(Bank.name) == name.lower()
    )
    if exclude_id is not None:
        query = query.filter(Bank.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=409, detail="Bank already exists")


def create_bank(db: DBSession, user: User, data: BankCreateRequest) -> Bank:
    name = data.name.strip()
    _ensure_name_available(db, user.id, name)

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


def _apply_name(db: DBSession, bank: Bank, name: str) -> None:
    stripped = name.strip()
    _ensure_name_available(db, bank.user_id, stripped, exclude_id=bank.id)
    bank.name = stripped


def _apply_last_balance(
    bank: Bank, effective_type: AccountType, value: Decimal
) -> None:
    if effective_type == CREDIT:
        raise HTTPException(
            status_code=400, detail="Credit accounts cannot have a balance"
        )
    bank.last_balance = value
    bank.last_balance_at = datetime.now(timezone.utc)


def _apply_card_digits(bank: Bank, effective_type: AccountType, value: str) -> None:
    if effective_type == DEPOSIT:
        raise HTTPException(
            status_code=400, detail="Deposit accounts cannot have a card number"
        )
    bank.card_digits = value


def _apply_account_type(bank: Bank, new_type: AccountType) -> None:
    """Enforce the destination type's invariants. Idempotent when unchanged."""
    if new_type == CREDIT:
        if not bank.card_digits:
            raise HTTPException(
                status_code=400, detail="Credit accounts require a card number"
            )
        bank.last_balance = None
        bank.last_balance_at = None
    else:
        bank.card_digits = None
    bank.account_type = new_type


def update_bank(
    db: DBSession, user: User, bank_id: int, data: BankUpdateRequest
) -> Bank:
    bank = _get_user_bank_or_404(db, user.id, bank_id)
    effective_type: AccountType = data.account_type or bank.account_type

    if data.name is not None:
        _apply_name(db, bank, data.name)
    if data.last_balance is not None:
        _apply_last_balance(bank, effective_type, data.last_balance)
    if data.card_digits is not None:
        _apply_card_digits(bank, effective_type, data.card_digits)
    if data.account_type is not None:
        _apply_account_type(bank, data.account_type)

    db.commit()
    db.refresh(bank)
    return bank


def delete_bank(db: DBSession, user: User, bank_id: int) -> None:
    bank = _get_user_bank_or_404(db, user.id, bank_id)
    db.delete(bank)
    db.commit()


def match_bank_by_sender(banks: list[Bank], sender: str) -> Bank | None:
    if not sender:
        return None
    s = sender.strip().lower()
    if not s:
        return None

    matches = [
        b
        for b in banks
        if b.account_type == CREDIT
        and b.name
        and (b.name.lower() in s or s in b.name.lower())
    ]
    if not matches:
        return None

    matches.sort(key=lambda b: len(b.name), reverse=True)
    if len(matches) > 1 and len(matches[0].name) == len(matches[1].name):
        logger.info(
            "Ambiguous sender->card match for '%s': %s",
            sender,
            [b.name for b in matches],
        )
        return None
    return matches[0]
