import re
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

from app.models import Bank, BankSender, BankTemplate, User
from app.schemas import BankCreateRequest, BankResponse, BankUpdateRequest
from app.services.template_parser import normalize

_BALANCE_VAR = re.compile(r"\{\{balance\}\}")
_MAX_SENDERS = 3


def _validate_templates(templates: list[str]) -> None:
    for tmpl in templates:
        count = len(_BALANCE_VAR.findall(tmpl))
        if count > 1:
            raise HTTPException(
                status_code=422,
                detail="Each template must contain {{balance}} at most once",
            )


def _sync_senders(db: DBSession, bank: Bank, senders: list[str]) -> None:
    if len(senders) > _MAX_SENDERS:
        raise HTTPException(
            status_code=422,
            detail=f"A bank can have at most {_MAX_SENDERS} sender names",
        )
    bank.senders.clear()
    db.flush()
    for name in senders:
        stripped = name.strip()
        if stripped:
            bank.senders.append(BankSender(name=stripped))


def _sync_templates(db: DBSession, bank: Bank, templates: list[str]) -> None:
    _validate_templates(templates)
    bank.templates.clear()
    db.flush()
    for tmpl in templates:
        stripped = tmpl.strip()
        if stripped:
            bank.templates.append(BankTemplate(template=normalize(stripped)))


def _bank_query(db: DBSession, user_id: int) -> list[Bank]:
    return (
        db.query(Bank)
        .filter(Bank.user_id == user_id)
        .options(selectinload(Bank.senders), selectinload(Bank.templates))
        .order_by(Bank.name)
        .all()
    )


def to_response(bank: Bank) -> BankResponse:
    return BankResponse(
        id=bank.id,
        name=bank.name,
        senders=[s.name for s in bank.senders],
        templates=[t.template for t in bank.templates],
        last_balance=bank.last_balance,
        last_balance_at=bank.last_balance_at,
        created_at=bank.created_at,
    )


def list_banks(db: DBSession, user: User) -> list[BankResponse]:
    banks = _bank_query(db, user.id)
    return [to_response(b) for b in banks]


def get_bank_by_name(db: DBSession, user_id: int, name: str) -> Bank | None:
    return (
        db.query(Bank)
        .filter(Bank.user_id == user_id, func.lower(Bank.name) == name.strip().lower())
        .first()
    )


def create_bank(db: DBSession, user: User, data: BankCreateRequest) -> BankResponse:
    name = data.name.strip()
    if get_bank_by_name(db, user.id, name):
        raise HTTPException(status_code=409, detail="Bank already exists")

    bank = Bank(name=name, user_id=user.id)
    db.add(bank)
    db.flush()

    if data.senders:
        _sync_senders(db, bank, data.senders)
    if data.templates:
        _sync_templates(db, bank, data.templates)

    db.commit()
    db.refresh(bank)
    return to_response(bank)


def update_bank(
    db: DBSession, user: User, bank_id: int, data: BankUpdateRequest
) -> BankResponse:
    bank = (
        db.query(Bank)
        .filter(Bank.id == bank_id, Bank.user_id == user.id)
        .options(selectinload(Bank.senders), selectinload(Bank.templates))
        .first()
    )
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

    if data.senders is not None:
        _sync_senders(db, bank, data.senders)

    if data.templates is not None:
        _sync_templates(db, bank, data.templates)

    db.commit()
    db.refresh(bank)
    return to_response(bank)


def delete_bank(db: DBSession, user: User, bank_id: int) -> None:
    bank = db.query(Bank).filter(Bank.id == bank_id, Bank.user_id == user.id).first()
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    db.delete(bank)
    db.commit()
