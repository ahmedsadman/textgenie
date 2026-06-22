from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import User
from app.schemas import WebhookSettingsResponse
from app.services.auth import get_current_user
from app.services.settings import get_webhook_settings, regenerate_webhook_token

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("/webhook", response_model=WebhookSettingsResponse)
def get_webhook(
    user: User = Depends(get_current_user),
):
    return get_webhook_settings(user)


@router.post("/webhook/regenerate", response_model=WebhookSettingsResponse)
def regenerate_webhook(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return regenerate_webhook_token(db, user)
