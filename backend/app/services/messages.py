import logging

from fastapi import HTTPException
from sqlalchemy import or_, text
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import joinedload

from app.models import Message, User

logger = logging.getLogger(__name__)


def list_messages(
    db: DBSession,
    user: User,
    page: int,
    page_size: int,
    category_ids: list[int] | None = None,
    search: str | None = None,
) -> tuple[list[Message], int]:
    query = (
        db.query(Message)
        .options(joinedload(Message.category))
        .filter(Message.user_id == user.id)
    )

    if category_ids:
        # 0 is a sentinel for "uncategorized" (NULL category_id).
        # SQL IN() never matches NULL, so IS NULL must be a separate condition.
        filters = []
        real_ids = [cid for cid in category_ids if cid != 0]
        if real_ids:
            filters.append(Message.category_id.in_(real_ids))
        if 0 in category_ids:
            filters.append(Message.category_id.is_(None))
        query = query.filter(or_(*filters))

    if search:
        dialect = db.bind.dialect.name
        if dialect == "mysql":
            # LIMITATION: Default FULLTEXT parser uses whitespace word boundaries.
            # Works for English and space-delimited scripts, but some unicode texts like
            # Bengali or Chinese may not be tokenized correctly.
            query = query.filter(
                text("MATCH(sender, content) AGAINST(:q IN NATURAL LANGUAGE MODE)")
            ).params(q=search)
        else:
            pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Message.sender.contains(pattern),
                    Message.content.contains(pattern),
                )
            )

    total = query.count()
    offset = (page - 1) * page_size
    messages = (
        query.order_by(Message.received_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return messages, total


def delete_message(db: DBSession, user: User, message_id: int) -> None:
    message = (
        db.query(Message)
        .filter(Message.id == message_id, Message.user_id == user.id)
        .first()
    )
    if not message:
        logger.error("Message not found: id=%d, user_id=%d", message_id, user.id)
        raise HTTPException(status_code=404, detail="Message not found")

    db.delete(message)
    db.commit()
    logger.info("Message deleted: id=%d", message_id)
