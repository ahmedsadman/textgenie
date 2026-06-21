from fastapi import HTTPException
from sqlalchemy.orm import Session as DBSession

from app.models import Category, User
from app.schemas import CategoryCreateRequest, CategoryUpdateRequest


def list_categories(db: DBSession, user: User) -> list[Category]:
    return (
        db.query(Category)
        .filter(Category.user_id == user.id)
        .order_by(Category.name)
        .all()
    )


def create_category(db: DBSession, user: User, data: CategoryCreateRequest) -> Category:
    name = data.name.strip().lower()
    existing = (
        db.query(Category)
        .filter(Category.user_id == user.id, Category.name == name)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Category already exists")

    category = Category(name=name, user_id=user.id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(
    db: DBSession, user: User, category_id: int, data: CategoryUpdateRequest
) -> Category:
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == user.id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    name = data.name.strip().lower()
    conflict = (
        db.query(Category)
        .filter(
            Category.user_id == user.id,
            Category.name == name,
            Category.id != category_id,
        )
        .first()
    )
    if conflict:
        raise HTTPException(status_code=409, detail="Category already exists")

    category.name = name
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: DBSession, user: User, category_id: int) -> None:
    category = (
        db.query(Category)
        .filter(Category.id == category_id, Category.user_id == user.id)
        .first()
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    db.delete(category)
    db.commit()
