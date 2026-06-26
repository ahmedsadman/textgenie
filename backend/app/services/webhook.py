import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import GEMINI_API_KEY
from app.database import SessionLocal
from app.models import Bank, Category, Message, User
from app.schemas import WebhookPayload
from app.services import metadata_blacklist
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
    try:
        message = db.query(Message).filter(Message.id == message_id).first()
        if not message:
            logger.error("Background parsing: message %d not found", message_id)
            return

        user = db.query(User).filter(User.id == message.user_id).first()
        if not user:
            logger.error("Background parsing: user %d not found", message.user_id)
            return

        categories = (
            db.query(Category).filter(_categories_filter(message.user_id)).all()
        )

        # Step 1: categorize
        category_name = _categorize(
            message.content, message.sender, [c.name for c in categories]
        )
        category = None
        if category_name:
            category = next((c for c in categories if c.name == category_name), None)
            if category:
                message.category_id = category.id
                logger.info(
                    "Message id=%d categorized as '%s'", message_id, category.name
                )

        # Step 2: gate metadata extraction
        if category is None or category.name != DefaultCategory.TRANSACTION.value:
            logger.info(
                "Message id=%d category is not '%s'; skipping metadata extraction",
                message_id,
                DefaultCategory.TRANSACTION.value,
            )
            db.commit()
            return

        if metadata_blacklist.contains(message.sender, user.metadata_blacklist):
            logger.info(
                "Message id=%d sender '%s' is in metadata blacklist; "
                "skipping metadata extraction",
                message_id,
                message.sender,
            )
            db.commit()
            return

        banks = db.query(Bank).filter(Bank.user_id == message.user_id).all()
        if not banks:
            logger.info(
                "Message id=%d user has no banks; skipping metadata extraction",
                message_id,
            )
            db.commit()
            return

        metadata = _extract_metadata(
            message.content, message.sender, [b.name for b in banks]
        )

        if metadata.bank and metadata.balance is not None:
            bank = next(
                (b for b in banks if b.name.lower() == metadata.bank.lower()), None
            )
            if bank and (
                bank.last_balance_at is None
                or message.received_at > bank.last_balance_at
            ):
                bank.last_balance = metadata.balance
                bank.last_balance_at = message.received_at
                logger.info(
                    "Bank id=%d balance updated to %s from message id=%d",
                    bank.id,
                    metadata.balance,
                    message_id,
                )

        db.commit()
    except Exception:
        logger.error(
            "Background parsing failed for message %d",
            message_id,
            exc_info=True,
        )
    finally:
        db.close()
