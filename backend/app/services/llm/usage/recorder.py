"""Persist LLM usage per user/day/provider/model.

Called from within an already-background task (parse_message), so a synchronous
DB write is fine. Errors are logged and swallowed so LLM/webhook flow never
fails on a broken usage row.
"""

import logging
from datetime import date, datetime, timezone

from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session as DBSession

from app.database import SessionLocal
from app.models import LLMUsage
from app.services.llm.usage.event import LLMUsageEvent
from app.services.llm.usage.prices import compute_cost_micros

logger = logging.getLogger(__name__)


def record(db: DBSession, user_id: int, event: LLMUsageEvent) -> None:
    """Atomic UPSERT on (user_id, today, provider, model).

    Aggregates tokens/cost into the existing row via a single dialect-native
    INSERT ... ON CONFLICT/DUPLICATE KEY statement — safe under concurrent
    writes for the same key.
    """
    values = {
        "user_id": user_id,
        "usage_date": date.today(),
        "provider": event.provider,
        "model": event.model,
        "input_tokens": event.input_tokens,
        "cached_input_tokens": event.cached_input_tokens,
        "output_tokens": event.output_tokens,
        "request_count": 1,
        "cost_micros": compute_cost_micros(
            event.provider,
            event.model,
            event.input_tokens,
            event.cached_input_tokens,
            event.output_tokens,
        ),
        "updated_at": datetime.now(timezone.utc),
    }

    dialect = db.bind.dialect.name
    if dialect == "mysql":
        stmt = mysql_insert(LLMUsage).values(**values)
        inserted = stmt.inserted
        stmt = stmt.on_duplicate_key_update(
            input_tokens=LLMUsage.input_tokens + inserted.input_tokens,
            cached_input_tokens=LLMUsage.cached_input_tokens
            + inserted.cached_input_tokens,
            output_tokens=LLMUsage.output_tokens + inserted.output_tokens,
            request_count=LLMUsage.request_count + 1,
            cost_micros=LLMUsage.cost_micros + inserted.cost_micros,
            updated_at=inserted.updated_at,
        )
    elif dialect == "sqlite":
        stmt = sqlite_insert(LLMUsage).values(**values)
        excluded = stmt.excluded
        stmt = stmt.on_conflict_do_update(
            index_elements=["user_id", "usage_date", "provider", "model"],
            set_={
                "input_tokens": LLMUsage.input_tokens + excluded.input_tokens,
                "cached_input_tokens": LLMUsage.cached_input_tokens
                + excluded.cached_input_tokens,
                "output_tokens": LLMUsage.output_tokens + excluded.output_tokens,
                "request_count": LLMUsage.request_count + 1,
                "cost_micros": LLMUsage.cost_micros + excluded.cost_micros,
                "updated_at": excluded.updated_at,
            },
        )
    else:
        raise RuntimeError(f"llm usage recorder: unsupported dialect {dialect!r}")

    db.execute(stmt)
    db.commit()


def record_from_current_session(user_id: int, event: LLMUsageEvent) -> None:
    """Open a fresh session, record, close. Never raises."""
    db = SessionLocal()
    try:
        record(db, user_id, event)
    except Exception:
        logger.error(
            "llm usage record failed (user_id=%s, provider=%s, model=%s)",
            user_id,
            event.provider,
            event.model,
            exc_info=True,
        )
    finally:
        db.close()
