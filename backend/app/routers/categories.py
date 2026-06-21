from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.database import get_db
from app.models import User
from app.schemas import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
    MessageResponse,
)
from app.services.auth import get_current_user
from app.services.categories import (
    create_category,
    delete_category,
    list_categories,
    update_category,
)

router = APIRouter(prefix="/api/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def get_categories(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return list_categories(db, user)


@router.post("", response_model=CategoryResponse, status_code=201)
def create(
    data: CategoryCreateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return create_category(db, user, data)


@router.put("/{category_id}", response_model=CategoryResponse)
def update(
    category_id: int,
    data: CategoryUpdateRequest,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    return update_category(db, user, category_id, data)


@router.delete("/{category_id}", response_model=MessageResponse)
def delete(
    category_id: int,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    delete_category(db, user, category_id)
    return MessageResponse(message="Category deleted")
