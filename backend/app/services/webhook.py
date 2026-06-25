import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import GEMINI_API_KEY
from app.database import SessionLocal
from app.models import Bank, Category, Message, User
from app.schemas import WebhookPayload
from app.services.categories import _categories_filter
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
    categories: list[str],
    banks: list[str],
) -> MessageParseResult:
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping message parsing")
        return MessageParseResult()

    try:
        provider = get_llm_provider()
        return provider.parse_message(message_content, sender, categories, banks)
    except Exception:
        logger.error("LLM message parsing failed", exc_info=True)
        return MessageParseResult()


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

        categories = (
            db.query(Category).filter(_categories_filter(message.user_id)).all()
        )
        banks = db.query(Bank).filter(Bank.user_id == message.user_id).all()

        result = _parse(
            message.content,
            message.sender,
            [c.name for c in categories],
            [b.name for b in banks],
        )

        if result.category:
            category = next((c for c in categories if c.name == result.category), None)
            if category:
                message.category_id = category.id
                logger.info(
                    "Message id=%d categorized as '%s'", message_id, category.name
                )

        if result.bank and result.balance is not None:
            bank = next(
                (b for b in banks if b.name.lower() == result.bank.lower()), None
            )
            if bank and (
                bank.last_balance_at is None
                or message.received_at > bank.last_balance_at
            ):
                bank.last_balance = result.balance
                bank.last_balance_at = message.received_at
                logger.info(
                    "Bank id=%d balance updated to %s from message id=%d",
                    bank.id,
                    result.balance,
                    message_id,
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
