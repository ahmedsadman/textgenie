import logging
import uuid
from typing import get_args

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import WEBHOOK_BASE_URL
from app.constants import Currency
from app.models import Bank, User
from app.services import metadata_blacklist

logger = logging.getLogger(__name__)

_VALID_CURRENCIES = frozenset(get_args(Currency))


def get_webhook_settings(user: User) -> dict:
    return {
        "webhook_url": f"{WEBHOOK_BASE_URL}/api/webhook/{user.webhook_token}",
        "webhook_token": user.webhook_token,
    }


def regenerate_webhook_token(db: DBSession, user: User) -> dict:
    user.webhook_token = str(uuid.uuid4())
    db.commit()
    db.refresh(user)
    logger.info("Webhook token regenerated for user_id=%d", user.id)
    return get_webhook_settings(user)


def get_metadata_blacklist(user: User) -> list[str]:
    return metadata_blacklist.parse(user.metadata_blacklist)


def get_currency(user: User) -> str:
    return user.normalized_currency


def update_currency(db: DBSession, user: User, currency: str) -> str:
    if currency not in _VALID_CURRENCIES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported currency: {currency!r}"
        )
    if currency == user.normalized_currency:
        return user.normalized_currency
    user.normalized_currency = currency
    # Cached bank balances were recorded under the previous currency and are
    # no longer meaningful. Clear them; the next matching-currency SMS will
    # refresh them.
    cleared = (
        db.query(Bank)
        .filter(Bank.user_id == user.id, Bank.last_balance.is_not(None))
        .update(
            {Bank.last_balance: None, Bank.last_balance_at: None},
            synchronize_session=False,
        )
    )
    db.commit()
    db.refresh(user)
    logger.info(
        "Normalized currency updated to %s for user_id=%d (cleared %d bank balances)",
        currency,
        user.id,
        cleared,
    )
    return user.normalized_currency


def update_metadata_blacklist(
    db: DBSession, user: User, senders: list[str]
) -> list[str]:
    for sender in senders:
        if metadata_blacklist.DELIMITER in sender:
            raise HTTPException(
                status_code=400,
                detail=f"Sender names cannot contain '{metadata_blacklist.DELIMITER}'",
            )
    serialized = metadata_blacklist.serialize(senders)
    user.metadata_blacklist = serialized or None
    db.commit()
    db.refresh(user)
    logger.info(
        "Metadata blacklist updated for user_id=%d (%d senders)",
        user.id,
        len(metadata_blacklist.parse(user.metadata_blacklist)),
    )
    return metadata_blacklist.parse(user.metadata_blacklist)
