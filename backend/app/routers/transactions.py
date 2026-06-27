from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import User
from app.schemas import PaginatedTransactionsResponse
from app.services.auth import get_current_user
from app.services.transactions import list_transactions

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=PaginatedTransactionsResponse)
def get_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    transactions, total, totals = list_transactions(
        db,
        user,
        page=page,
        page_size=page_size,
        from_date=from_date,
        to_date=to_date,
    )
    return PaginatedTransactionsResponse(
        transactions=transactions,
        total=total,
        page=page,
        page_size=page_size,
        totals=totals,
    )
