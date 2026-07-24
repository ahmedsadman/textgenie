from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import User
from app.schemas import (
    AdminListUsersResponse,
    AdminUsageSummary,
    AdminUserUsageDetailResponse,
    BucketSize,
)
from app.services.admin import (
    MAX_USER_IDS,
    delete_user,
    get_usage_summary,
    get_user_usage_detail,
    list_users,
)
from app.services.auth import require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _parse_user_ids(raw: str) -> list[int]:
    if not raw.strip():
        return []
    ids: list[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            ids.append(int(token))
        except ValueError:
            raise HTTPException(status_code=400, detail="user_ids must be integers")
    if len(ids) > MAX_USER_IDS:
        raise HTTPException(status_code=400, detail="too many user_ids")
    return ids


@router.get("/users", response_model=AdminListUsersResponse)
def get_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: DBSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    users, total = list_users(db, page=page, page_size=page_size)
    return AdminListUsersResponse(
        users=users, total=total, page=page, page_size=page_size
    )


@router.get("/usage/summary", response_model=dict[int, AdminUsageSummary])
def get_usage_summary_endpoint(
    user_ids: str = Query("", description="comma-separated user IDs"),
    db: DBSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return get_usage_summary(db, _parse_user_ids(user_ids))


@router.get("/users/{user_id}/usage", response_model=AdminUserUsageDetailResponse)
def get_user_usage(
    user_id: int,
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
    bucket: BucketSize | None = Query(None),
    db: DBSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    today = datetime.now(timezone.utc).date()
    from_date = from_ or today - timedelta(days=365)
    to_date = to or today
    if to_date < from_date:
        raise HTTPException(status_code=400, detail="'to' must be on or after 'from'")
    return get_user_usage_detail(
        db, user_id, from_date=from_date, to_date=to_date, bucket=bucket
    )


@router.delete("/users/{user_id}", status_code=204)
def delete_admin_user(
    user_id: int,
    db: DBSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    delete_user(db, admin, user_id)
