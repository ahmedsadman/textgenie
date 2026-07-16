from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import User
from app.schemas import BillResponse, BillUpdateRequest, PaginatedBillsResponse
from app.services.auth import get_current_user
from app.services.bills import get_bill, list_bills, unlink_transactions

router = APIRouter(prefix="/api/bills", tags=["bills"])


@router.get("", response_model=PaginatedBillsResponse)
def get_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    bank_id: int | None = Query(None),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    bills, total = list_bills(
        db,
        user,
        page=page,
        page_size=page_size,
        bank_id=bank_id,
        from_date=from_date,
        to_date=to_date,
    )
    return PaginatedBillsResponse(
        bills=bills, total=total, page=page, page_size=page_size
    )


@router.get("/{bill_id}", response_model=BillResponse)
def get_single_bill(
    bill_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return get_bill(db, user, bill_id)


@router.patch("/{bill_id}", response_model=BillResponse)
def patch_bill(
    bill_id: int,
    body: BillUpdateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return unlink_transactions(db, user, bill_id, body.unlink_transaction_ids or [])
