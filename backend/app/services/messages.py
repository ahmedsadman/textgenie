import logging

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import joinedload

from app.models import Message, User

SENDERS_LIMIT = 100

# Characters with special meaning in MySQL FULLTEXT BOOLEAN MODE. Stripped from
# user tokens before we wrap them with our own '+' and '*' operators, so a user
# typing '+' or '*' can't change the query semantics or trigger a syntax error.
_BOOLEAN_OPERATOR_CHARS = str.maketrans("", "", '+-><()~*"@')

logger = logging.getLogger(__name__)


def _search_tokens(search: str) -> list[str]:
    """Whitespace-split the query and strip BOOLEAN MODE operator chars."""
    cleaned = (raw.translate(_BOOLEAN_OPERATOR_CHARS) for raw in search.split())
    return [t for t in cleaned if t]


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
        tokens = _search_tokens(search)
        if tokens:
            dialect = db.bind.dialect.name
            if dialect == "mysql":
                # BOOLEAN MODE with '+tok*' per token: each token is required (AND)
                # and matches any indexed word that starts with it, so "tran" finds
                # "transaction". Note: InnoDB's innodb_ft_min_token_size defaults to
                # 3, so 1-2 char tokens are silently ignored by the index.
                boolean_query = " ".join(f"+{t}*" for t in tokens)
                query = query.filter(
                    text("MATCH(sender, content) AGAINST(:q IN BOOLEAN MODE)")
                ).params(q=boolean_query)
            else:
                # SQLite/Postgres fallback used in tests. Match each token as a
                # word-prefix in either field: at start of string OR after a space.
                per_token = [
                    or_(
                        Message.sender.like(f"{t}%"),
                        Message.sender.like(f"% {t}%"),
                        Message.content.like(f"{t}%"),
                        Message.content.like(f"% {t}%"),
                    )
                    for t in tokens
                ]
                query = query.filter(and_(*per_token))

    total = query.count()
    offset = (page - 1) * page_size
    messages = (
        query.order_by(Message.received_at.desc()).offset(offset).limit(page_size).all()
    )

    return messages, total


def list_senders(db: DBSession, user: User, limit: int = SENDERS_LIMIT) -> list[str]:
    """Distinct senders for a user, ordered by most-recently-seen first."""
    rows = (
        db.query(Message.sender, func.max(Message.received_at).label("last_seen"))
        .filter(Message.user_id == user.id)
        .group_by(Message.sender)
        .order_by(func.max(Message.received_at).desc())
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]


def get_message(db: DBSession, user: User, message_id: int) -> Message:
    message = (
        db.query(Message)
        .filter(Message.id == message_id, Message.user_id == user.id)
        .first()
    )
    if not message:
        logger.error("Message not found: id=%d, user_id=%d", message_id, user.id)
        raise HTTPException(status_code=404, detail="Message not found")
    return message


def delete_message(db: DBSession, user: User, message_id: int) -> None:
    message = get_message(db, user, message_id)
    db.delete(message)
    db.commit()
    logger.info("Message deleted: id=%d", message_id)
