import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import GEMINI_API_KEY
from app.database import SessionLocal
from app.models import Category, Message, User
from app.schemas import WebhookPayload
from app.services.llm.base import MessageParseResult
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


def _parse(
    message_content: str,
    sender: str,
    categories: list[Category],
    banks: list[str] | None = None,
) -> MessageParseResult:
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping message parsing")
        return MessageParseResult()

    category_names = [c.name for c in categories]
    try:
        provider = get_llm_provider()
        return provider.parse_message(message_content, sender, category_names, banks)
    except Exception:
        logger.error("LLM message parsing failed", exc_info=True)
        return MessageParseResult()


def process_webhook(db: DBSession, token: str, payload: WebhookPayload) -> Message:
    user = db.query(User).filter(User.webhook_token == token).first()
    if not user:
        logger.error("Webhook received with invalid token: %s", token)
        raise HTTPException(status_code=404, detail="Invalid webhook token")

    logger.info("Webhook received for user_id=%d, sender='%s'", user.id, payload.sender)

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

        categories = (
            db.query(Category).filter(Category.user_id == message.user_id).all()
        )

        result = _parse(message.content, message.sender, categories)

        if result.category:
            category = next((c for c in categories if c.name == result.category), None)
            if category:
                message.category_id = category.id
                logger.info(
                    "Message id=%d categorized as '%s'", message_id, category.name
                )

        db.commit()
        if not result.category:
            logger.info("Message id=%d remains uncategorized", message_id)
    except Exception:
        logger.error(
            "Background parsing failed for message %d",
            message_id,
            exc_info=True,
        )
    finally:
        db.close()
