"""Direct-DB factory helpers for tests that need to bypass the HTTP layer"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session as DBSession

from app.models import Bank, Bill, Message, Transaction, User
from app.services.llm.base import BillMetadataResult, MetadataResult


def make_user(db: DBSession, *, email: str = "t@example.com") -> User:
    user = User(
        name="Test",
        email=email,
        password_hash="x",
        webhook_token=email,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_bank(
    db: DBSession,
    user: User,
    name: str,
    *,
    account_type: str = "deposit",
    card_digits: str | None = None,
) -> Bank:
    bank = Bank(
        name=name,
        user_id=user.id,
        account_type=account_type,
        card_digits=card_digits,
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return bank


def make_message(
    db: DBSession,
    user: User,
    *,
    sender: str,
    received_at: datetime,
    content: str | None = None,
) -> Message:
    msg = Message(
        sender=sender,
        content=content if content is not None else f"{sender} msg",
        received_at=received_at,
        user_id=user.id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def make_transaction(
    db: DBSession,
    user: User,
    *,
    amount: str | Decimal,
    type: str,
    date: datetime,
    bank: Bank | None = None,
    paired_with_id: int | None = None,
    sender: str = "X",
    original_amount: str | Decimal | None = None,
    original_currency: str | None = None,
) -> Transaction:
    """Create a Transaction along with its backing Message row.

    `amount` is written to `normalized_amount`. `original_amount` /
    `original_currency` default to None to mimic pre-migration rows.
    """
    msg = make_message(db, user, sender=sender, received_at=date)
    tx = Transaction(
        user_id=user.id,
        message_id=msg.id,
        bank_id=bank.id if bank is not None else None,
        normalized_amount=Decimal(str(amount)),
        original_amount=(
            Decimal(str(original_amount)) if original_amount is not None else None
        ),
        original_currency=original_currency,
        type=type,
        date=date,
        paired_with_id=paired_with_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def make_bill(
    db: DBSession,
    user: User,
    *,
    normalized_total_due: str | Decimal,
    received_at: datetime,
    bank: Bank | None = None,
    statement_period: date | None = None,
    sender: str = "BILL",
    normalized_currency: str = "BDT",
    original_amount: str | Decimal | None = None,
    original_currency: str | None = None,
    message: Message | None = None,
) -> Bill:
    """Create a Bill along with (unless provided) its backing Message row."""
    if message is None:
        message = make_message(db, user, sender=sender, received_at=received_at)
    bill = Bill(
        user_id=user.id,
        bank_id=bank.id if bank is not None else None,
        message_id=message.id,
        normalized_total_due=Decimal(str(normalized_total_due)),
        normalized_currency=normalized_currency,
        original_amount=(
            Decimal(str(original_amount)) if original_amount is not None else None
        ),
        original_currency=original_currency,
        statement_period=statement_period,
    )
    db.add(bill)
    db.commit()
    db.refresh(bill)
    return bill


def make_mock_provider(
    category=None,
    metadata=None,
    bill_metadata=None,
    categorize_raises=None,
    extract_raises=None,
    extract_bill_raises=None,
):
    """Build a stub LLM provider for parse_message orchestration tests.

    - category: value returned by provider.categorize()
    - metadata: MetadataResult returned by provider.extract_metadata()
    - bill_metadata: BillMetadataResult returned by provider.extract_bill_metadata()
    - *_raises: Exception instances to raise instead
    """
    md = metadata if metadata is not None else MetadataResult()
    bill_md = bill_metadata if bill_metadata is not None else BillMetadataResult()

    def _categorize(self, *a, **k):
        if categorize_raises is not None:
            raise categorize_raises
        return category

    def _extract(self, *a, **k):
        if extract_raises is not None:
            raise extract_raises
        return md

    def _extract_bill(self, *a, **k):
        if extract_bill_raises is not None:
            raise extract_bill_raises
        return bill_md

    return type(
        "MockProvider",
        (),
        {
            "categorize": _categorize,
            "extract_metadata": _extract,
            "extract_bill_metadata": _extract_bill,
        },
    )()
