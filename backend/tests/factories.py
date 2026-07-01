"""Direct-DB factory helpers for tests that need to bypass the HTTP layer"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session as DBSession

from app.models import Bank, Message, Transaction, User
from app.services.llm.base import MetadataResult


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


def make_bank(db: DBSession, user: User, name: str) -> Bank:
    bank = Bank(name=name, user_id=user.id)
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
) -> Transaction:
    """Create a Transaction along with its backing Message row.

    Every Transaction has a NOT NULL message_id, so the helper builds
    the Message implicitly — callers rarely care about the message when
    unit-testing transaction behavior.
    """
    msg = make_message(db, user, sender=sender, received_at=date)
    tx = Transaction(
        user_id=user.id,
        message_id=msg.id,
        bank_id=bank.id if bank is not None else None,
        amount=Decimal(str(amount)),
        type=type,
        date=date,
        paired_with_id=paired_with_id,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def make_mock_provider(
    category=None, metadata=None, categorize_raises=None, extract_raises=None
):
    """Build a stub LLM provider for parse_message orchestration tests.

    - category: value returned by provider.categorize()
    - metadata: MetadataResult returned by provider.extract_metadata()
    - categorize_raises / extract_raises: Exception instances to raise instead
    """
    md = metadata if metadata is not None else MetadataResult()

    def _categorize(self, *a, **k):
        if categorize_raises is not None:
            raise categorize_raises
        return category

    def _extract(self, *a, **k):
        if extract_raises is not None:
            raise extract_raises
        return md

    return type(
        "MockProvider",
        (),
        {"categorize": _categorize, "extract_metadata": _extract},
    )()
