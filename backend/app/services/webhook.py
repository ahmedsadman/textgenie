import logging
import re
from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import GEMINI_API_KEY
from app.constants import CREDIT
from app.database import SessionLocal
from app.models import Bank, Bill, Category, Message, Transaction, User
from app.schemas import WebhookPayload
from app.services import bill_payment_matcher, metadata_blacklist, transfer_matcher
from app.services.categories import DefaultCategory, _categories_filter
from app.services.llm.base import BillMetadataResult, MetadataResult
from app.services.llm.provider import get_llm_provider
from app.services.llm.usage import LLMUsageEvent, record_from_current_session

logger = logging.getLogger(__name__)


def _parse_timestamp(timestamp: int | None) -> datetime:
    if timestamp is None:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
    except (ValueError, OSError, OverflowError):
        logger.warning("Failed to parse timestamp: %s", timestamp)
        return datetime.now(timezone.utc)


def _usage_callback(user_id: int):
    def _cb(event: LLMUsageEvent) -> None:
        record_from_current_session(user_id, event)

    return _cb


def _categorize(
    content: str, sender: str, categories: list[str], user_id: int
) -> str | None:
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping categorization")
        return None
    try:
        return get_llm_provider().categorize(
            content, sender, categories, on_usage=_usage_callback(user_id)
        )
    except Exception:
        logger.error("LLM categorize failed", exc_info=True)
        return None


def _extract_metadata(
    content: str,
    sender: str,
    banks: list[str],
    normalized_currency: str,
    user_id: int,
) -> MetadataResult:
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping metadata extraction")
        return MetadataResult()
    try:
        return get_llm_provider().extract_metadata(
            content,
            sender,
            banks,
            normalized_currency,
            on_usage=_usage_callback(user_id),
        )
    except Exception:
        logger.error("LLM metadata extraction failed", exc_info=True)
        return MetadataResult()


def _extract_bill_metadata(
    content: str,
    sender: str,
    banks: list[str],
    normalized_currency: str,
    user_id: int,
) -> BillMetadataResult:
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not configured — skipping bill extraction")
        return BillMetadataResult()
    try:
        return get_llm_provider().extract_bill_metadata(
            content,
            sender,
            banks,
            normalized_currency,
            on_usage=_usage_callback(user_id),
        )
    except Exception:
        logger.error("LLM bill extraction failed", exc_info=True)
        return BillMetadataResult()


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
    new_bill_id: int | None = None
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
        category_name = category.name if category else None

        if _sender_blacklisted(message, user):
            db.commit()
            return

        if category_name == DefaultCategory.TRANSACTION.value:
            new_transfer_tx_id = _extract_and_apply_metadata(db, message, user)
        elif category_name == DefaultCategory.BILL.value:
            new_bill_id = _handle_bill_message(db, message, user)
        else:
            logger.info(
                "Message id=%d category '%s' does not require extraction",
                message.id,
                category_name,
            )

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
    if new_bill_id is not None:
        bill_payment_matcher.schedule_bill_payment_match(new_bill_id)


def _categorize_and_assign(db: DBSession, message: Message) -> Category | None:
    """Categorize the message via LLM and assign category_id on the model."""
    categories = db.query(Category).filter(_categories_filter(message.user_id)).all()
    category_name = _categorize(
        message.content,
        message.sender,
        [c.name for c in categories],
        message.user_id,
    )
    if not category_name:
        return None
    category = next((c for c in categories if c.name == category_name), None)
    if category:
        message.category_id = category.id
        logger.info("Message id=%d categorized as '%s'", message.id, category.name)
    return category


def _sender_blacklisted(message: Message, user: User) -> bool:
    if metadata_blacklist.contains(message.sender, user.metadata_blacklist):
        logger.info(
            "Message id=%d sender '%s' is in metadata blacklist; skipping extraction",
            message.id,
            message.sender,
        )
        return True
    return False


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
        message.content,
        message.sender,
        [b.name for b in banks],
        user.normalized_currency,
        user.id,
    )

    bank = _match_credit_card(banks, message.content) or _match_bank(
        banks, metadata.bank
    )
    _update_bank_balance(bank, metadata, message, user)
    new_tx = _record_transaction(db, user, bank, metadata, message)

    if new_tx is not None and new_tx.type == "transfer":
        return new_tx.id
    return None


def _match_bank(banks: list[Bank], name: str | None) -> Bank | None:
    if not name:
        return None
    return next((b for b in banks if b.name.lower() == name.lower()), None)


def _match_credit_card(banks: list[Bank], content: str) -> Bank | None:
    for bank in banks:
        if bank.account_type != CREDIT or not bank.card_digits:
            continue
        first4, _, last4 = bank.card_digits.partition("|")
        if not first4 or not last4:
            continue
        pattern = rf"{first4}[\dXx*\s\-]{{0,16}}{last4}"
        if re.search(pattern, content, re.IGNORECASE):
            return bank
    return None


def _update_bank_balance(
    bank: Bank | None, metadata: MetadataResult, message: Message, user: User
) -> None:
    if not bank or metadata.balance is None:
        return
    if bank.account_type == CREDIT:
        logger.info(
            "Bank id=%d is a credit account; skipping balance update "
            "from message id=%d",
            bank.id,
            message.id,
        )
        return
    if (
        metadata.original_currency is not None
        and metadata.original_currency != user.normalized_currency
    ):
        logger.info(
            "Message id=%d original currency %s differs from user's normalized "
            "currency %s; skipping balance update on bank id=%d",
            message.id,
            metadata.original_currency,
            user.normalized_currency,
            bank.id,
        )
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


def _handle_bill_message(db: DBSession, message: Message, user: User) -> int | None:
    credit_banks = (
        db.query(Bank)
        .filter(Bank.user_id == user.id, Bank.account_type == CREDIT)
        .all()
    )
    if not credit_banks:
        logger.info(
            "Message id=%d user has no credit banks; skipping bill extraction",
            message.id,
        )
        return None

    metadata = _extract_bill_metadata(
        message.content,
        message.sender,
        [b.name for b in credit_banks],
        user.normalized_currency,
        user.id,
    )
    if metadata.normalized_total_due is None:
        logger.info(
            "Message id=%d bill extraction returned no normalized_total_due; skipping",
            message.id,
        )
        return None

    bank = _match_bank(credit_banks, metadata.bank)
    bill = _record_bill(db, user, bank, metadata, message)
    return bill.id if bill else None


def _record_bill(
    db: DBSession,
    user: User,
    bank: Bank | None,
    metadata: BillMetadataResult,
    message: Message,
) -> Bill | None:
    existing = db.query(Bill).filter(Bill.message_id == message.id).first()
    if existing is not None:
        logger.info(
            "Bill already exists for message id=%d; skipping insert", message.id
        )
        return None

    statement_period: date | None = None
    if metadata.statement_month is not None and metadata.statement_year is not None:
        statement_period = date(metadata.statement_year, metadata.statement_month, 1)

    if bank is not None and statement_period is not None:
        duplicate = (
            db.query(Bill)
            .filter(
                Bill.user_id == user.id,
                Bill.bank_id == bank.id,
                Bill.statement_period == statement_period,
            )
            .first()
        )
        if duplicate is not None:
            logger.info(
                "Bill for user_id=%d bank_id=%d period=%s already exists "
                "(id=%d); skipping insert for message id=%d",
                user.id,
                bank.id,
                statement_period,
                duplicate.id,
                message.id,
            )
            return None

    bill = Bill(
        user_id=user.id,
        bank_id=bank.id if bank else None,
        message_id=message.id,
        normalized_total_due=metadata.normalized_total_due,
        normalized_currency=user.normalized_currency,
        original_amount=metadata.original_amount,
        original_currency=metadata.original_currency,
        statement_period=statement_period,
    )
    db.add(bill)
    db.flush()
    logger.info(
        "Bill recorded for message id=%d: normalized_total_due=%s period=%s bank_id=%s "
        "(bill id=%d)",
        message.id,
        metadata.normalized_total_due,
        statement_period,
        bank.id if bank else None,
        bill.id,
    )
    return bill


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
        normalized_amount=metadata.amount,
        normalized_currency=user.normalized_currency,
        original_amount=metadata.original_amount,
        original_currency=metadata.original_currency,
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
