from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.models import LLMUsage, Message, User
from app.schemas import (
    AdminUsageBucket,
    AdminUsageSummary,
    AdminUserUsageDetailResponse,
    BucketSize,
    UserResponse,
)

MAX_USER_IDS = 100


def _default_bucket(from_date: date, to_date: date) -> BucketSize:
    span = (to_date - from_date).days
    if span <= 45:
        return "day"
    if span <= 180:
        return "week"
    return "month"


def _bucket_key(d: date, bucket: BucketSize) -> date:
    if bucket == "month":
        return date(d.year, d.month, 1)
    if bucket == "week":
        return d - timedelta(days=d.weekday())  # Monday
    return d


def list_users(
    db: DBSession, *, page: int, page_size: int
) -> tuple[list[UserResponse], int]:
    total = db.query(func.count(User.id)).scalar() or 0
    offset = (page - 1) * page_size
    rows = (
        db.query(User)
        .order_by(User.created_at.desc())
        .limit(page_size)
        .offset(offset)
        .all()
    )
    return [UserResponse.model_validate(u) for u in rows], total


def get_usage_summary(
    db: DBSession, user_ids: list[int]
) -> dict[int, AdminUsageSummary]:
    if not user_ids:
        return {}
    if len(user_ids) > MAX_USER_IDS:
        raise HTTPException(status_code=400, detail="too many user_ids")

    cutoff = datetime.now(timezone.utc).date() - timedelta(days=30)
    token_sum = (
        LLMUsage.input_tokens + LLMUsage.cached_input_tokens + LLMUsage.output_tokens
    )

    lifetime_stmt = (
        select(LLMUsage.user_id, func.sum(LLMUsage.cost_micros), func.sum(token_sum))
        .where(LLMUsage.user_id.in_(user_ids))
        .group_by(LLMUsage.user_id)
    )
    recent_stmt = (
        select(LLMUsage.user_id, func.sum(LLMUsage.cost_micros), func.sum(token_sum))
        .where(LLMUsage.user_id.in_(user_ids), LLMUsage.usage_date >= cutoff)
        .group_by(LLMUsage.user_id)
    )

    result: dict[int, AdminUsageSummary] = {
        uid: AdminUsageSummary(
            lifetime_cost_micros=0,
            lifetime_tokens=0,
            last30d_cost_micros=0,
            last30d_tokens=0,
        )
        for uid in user_ids
    }
    for uid, cost, tokens in db.execute(lifetime_stmt).all():
        result[uid].lifetime_cost_micros = int(cost or 0)
        result[uid].lifetime_tokens = int(tokens or 0)
    for uid, cost, tokens in db.execute(recent_stmt).all():
        result[uid].last30d_cost_micros = int(cost or 0)
        result[uid].last30d_tokens = int(tokens or 0)
    return result


def get_user_usage_detail(
    db: DBSession,
    user_id: int,
    *,
    from_date: date,
    to_date: date,
    bucket: BucketSize | None,
) -> AdminUserUsageDetailResponse:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")

    resolved_bucket = bucket or _default_bucket(from_date, to_date)

    message_count = (
        db.query(func.count(Message.id)).filter(Message.user_id == user_id).scalar()
        or 0
    )

    token_sum = (
        LLMUsage.input_tokens + LLMUsage.cached_input_tokens + LLMUsage.output_tokens
    )
    rows = (
        db.query(LLMUsage.usage_date, LLMUsage.cost_micros, token_sum)
        .filter(
            LLMUsage.user_id == user_id,
            LLMUsage.usage_date >= from_date,
            LLMUsage.usage_date <= to_date,
        )
        .order_by(LLMUsage.usage_date.asc())
        .all()
    )

    buckets: dict[date, AdminUsageBucket] = {}
    for usage_date, cost, tokens in rows:
        key = _bucket_key(usage_date, resolved_bucket)
        b = buckets.get(key)
        if b is None:
            b = AdminUsageBucket(bucket_start=key, cost_micros=0, tokens=0)
            buckets[key] = b
        b.cost_micros += int(cost or 0)
        b.tokens += int(tokens or 0)

    series = sorted(buckets.values(), key=lambda b: b.bucket_start)
    return AdminUserUsageDetailResponse(
        series=series,
        message_count=int(message_count),
        bucket=resolved_bucket,
    )


def delete_user(db: DBSession, admin: User, target_id: int) -> None:
    if target_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    target = db.get(User, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(target)
    db.commit()
