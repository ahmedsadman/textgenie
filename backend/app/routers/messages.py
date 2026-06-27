from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import User
from app.schemas import MessageResponse, PaginatedMessagesResponse, SmsMessageResponse
from app.services.auth import get_current_user
from app.services.messages import (
    delete_message,
    get_message,
    list_messages,
    list_senders,
)

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("", response_model=PaginatedMessagesResponse)
def get_messages(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category_ids: list[int] | None = Query(None),
    search: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    messages, total = list_messages(db, user, page, page_size, category_ids, search)
    return PaginatedMessagesResponse(
        messages=messages,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/senders", response_model=list[str])
def get_senders(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return list_senders(db, user)


@router.get("/{message_id}", response_model=SmsMessageResponse)
def get(
    message_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return get_message(db, user, message_id)


@router.delete("/{message_id}", response_model=MessageResponse)
def delete(
    message_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    delete_message(db, user, message_id)
    return MessageResponse(message="Message deleted")
