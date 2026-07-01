import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import GEMINI_API_KEY
from app.database import SessionLocal
from app.models import Bank, Category, Message, Transaction, User
from app.schemas import WebhookPayload
from app.services import metadata_blacklist, transfer_matcher
from app.services.categories import DefaultCategory, _categories_filter
from app.services.llm.base import MetadataResult
from app.services.llm.provider import get_llm_provider

logger = logging.getLogger(__name__)


def _parse_timestamp(timestamp: int | None) -> datetime:
    if timestamp is None:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
    except (ValueError, OSError, OverflowError):
        logger.warning("Failed to parse timestamp: %s", timestamp)
        return datetime.now(timezone.utc)


def _categorize(content: str, sender: str, categories: list[str]) -> str | None:
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping categorization")
        return None
    try:
        return get_llm_provider().categorize(content, sender, categories)
    except Exception:
        logger.error("LLM categorize failed", exc_info=True)
        return None


def _extract_metadata(content: str, sender: str, banks: list[str]) -> MetadataResult:
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping metadata extraction")
        return MetadataResult()
    try:
        return get_llm_provider().extract_metadata(content, sender, banks)
    except Exception:
        logger.error("LLM metadata extraction failed", exc_info=True)
        return MetadataResult()


def process_webhook(db: DBSession, token: str, payload: WebhookPayload) -> Message:
    user = db.query(User).filter(User.webhook_token == token).first()
    if not user:
        logger.error("Webhook received with invalid token: %s", token)
        raise HTTPException(status_code=404, detail="Invalid webhook token")

    logger.info(
        "Webhook received for user_id=%d, payload=%s",
        user.id,
        payload.model_dump_json(),
    )

    received_at = _parse_timestamp(payload.timestamp)

    message = Message(
        sender=payload.sender,
        content=payload.content,
        received_at=received_at,
        category_id=None,
        user_id=user.id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    logger.info("Message created id=%d", message.id)
    return message


def parse_message(message_id: int) -> None:
    db = SessionLocal()
    new_transfer_tx_id: int | None = None
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            logger.error("Background parsing: message %d not found", message_id)
            return

        user = db.query(User).filter(User.id == message.user_id).first()
        if not user:
            logger.error("Background parsing: user %d not found", message.user_id)
            return

        category = _categorize_and_assign(db, message)

        if _should_extract_metadata(message, user, category):
            new_transfer_tx_id = _extract_and_apply_metadata(db, message, user)

        db.commit()
    except Exception:
        logger.error(
            "Background parsing failed for message %d",
            message_id,
            exc_info=True,
        )
        return
    finally:
        db.close()

    if new_transfer_tx_id is not None:
        transfer_matcher.schedule_transfer_match(new_transfer_tx_id)


def _categorize_and_assign(db: DBSession, message: Message) -> Category | None:
    """Categorize the message via LLM and assign category_id on the model."""
    categories = db.query(Category).filter(_categories_filter(message.user_id)).all()
    category_name = _categorize(
        message.content, message.sender, [c.name for c in categories]
    )
    if not category_name:
        return None
    category = next((c for c in categories if c.name == category_name), None)
    if category:
        message.category_id = category.id
        logger.info("Message id=%d categorized as '%s'", message.id, category.name)
    return category


def _should_extract_metadata(
    message: Message, user: User, category: Category | None
) -> bool:
    if category is None or category.name != DefaultCategory.TRANSACTION.value:
        logger.info(
            "Message id=%d category is not '%s'; skipping metadata extraction",
            message.id,
            DefaultCategory.TRANSACTION.value,
        )
        return False

    if metadata_blacklist.contains(message.sender, user.metadata_blacklist):
        logger.info(
            "Message id=%d sender '%s' is in metadata blacklist; "
            "skipping metadata extraction",
            message.id,
            message.sender,
        )
        return False

    return True


def _extract_and_apply_metadata(
    db: DBSession, message: Message, user: User
) -> int | None:
    """Return the new transaction id if it was a transfer (for deferred matching)."""
    banks = db.query(Bank).filter(Bank.user_id == user.id).all()
    if not banks:
        logger.info(
            "Message id=%d user has no banks; skipping metadata extraction",
            message.id,
        )
        return None

    metadata = _extract_metadata(
        message.content, message.sender, [b.name for b in banks]
    )
    bank = _match_bank(banks, metadata.bank)
    _update_bank_balance(bank, metadata, message)
    new_tx = _record_transaction(db, user, bank, metadata, message)
    if new_tx is not None and new_tx.type == "transfer":
        return new_tx.id
    return None


def _match_bank(banks: list[Bank], name: str | None) -> Bank | None:
    if not name:
        return None
    return next((b for b in banks if b.name.lower() == name.lower()), None)


def _update_bank_balance(
    bank: Bank | None, metadata: MetadataResult, message: Message
) -> None:
    if not bank or metadata.balance is None:
        return
    if bank.last_balance_at is not None and message.received_at <= bank.last_balance_at:
        return
    bank.last_balance = metadata.balance
    bank.last_balance_at = message.received_at
    logger.info(
        "Bank id=%d balance updated to %s from message id=%d",
        bank.id,
        metadata.balance,
        message.id,
    )


def _record_transaction(
    db: DBSession,
    user: User,
    bank: Bank | None,
    metadata: MetadataResult,
    message: Message,
) -> Transaction | None:
    if not metadata.amount or not metadata.transaction_type:
        return None

    existing = (
        db.query(Transaction).filter(Transaction.message_id == message.id).first()
    )
    if existing is not None:
        logger.info(
            "Transaction already exists for message id=%d; skipping insert",
            message.id,
        )
        return None

    tx = Transaction(
        user_id=user.id,
        message_id=message.id,
        bank_id=bank.id if bank else None,
        amount=metadata.amount,
        type=metadata.transaction_type,
        date=message.received_at,
    )
    db.add(tx)
    db.flush()  # populate tx.id while keeping the outer transaction open
    logger.info(
        "Transaction recorded for message id=%d: %s %s (tx id=%d)",
        message.id,
        metadata.transaction_type,
        metadata.amount,
        tx.id,
    )
    return tx
