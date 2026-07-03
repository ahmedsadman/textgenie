from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import User
from app.schemas import (
    BankCreateRequest,
    BankResponse,
    BankUpdateRequest,
    MessageResponse,
)
from app.services.auth import get_current_user
from app.services.banks import (
    create_bank,
    delete_bank,
    list_banks,
    update_bank,
)

router = APIRouter(prefix="/api/banks", tags=["banks"])


@router.get("", response_model=list[BankResponse])
def get_banks(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return list_banks(db, user)


@router.post("", response_model=BankResponse, status_code=201)
def create(
    data: BankCreateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return create_bank(db, user, data)


@router.patch("/{bank_id}", response_model=BankResponse)
def update(
    bank_id: int,
    data: BankUpdateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return update_bank(db, user, bank_id, data)


@router.delete("/{bank_id}", response_model=MessageResponse)
def delete(
    bank_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    delete_bank(db, user, bank_id)
    return MessageResponse(message="Bank deleted")
