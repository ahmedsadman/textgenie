import logging
import uuid

from sqlalchemy.orm import Session as DBSession

from app.config import WEBHOOK_BASE_URL
from app.models import User

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
