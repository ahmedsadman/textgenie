from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.schemas import MessageResponse, WebhookPayload
from app.services.webhook import parse_message, process_webhook

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


@router.post("/{token}", response_model=MessageResponse, status_code=201)
def receive_message(
    token: str,
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
):
    message = process_webhook(db, token, payload)
    background_tasks.add_task(parse_message, message.id)
    return MessageResponse(message="Message received")
