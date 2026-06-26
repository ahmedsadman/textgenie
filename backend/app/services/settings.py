import logging
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.config import WEBHOOK_BASE_URL
from app.models import User
from app.services import metadata_blacklist

logger = logging.getLogger(__name__)


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
