import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DBSession

from app.config import (
    COOKIE_NAME,
    COOKIE_SECURE,
    SESSION_CLEANUP_INTERVAL_SECONDS,
    SESSION_DURATION_HOURS,
)
from app.database import SessionLocal, get_db
from app.models import Session, User
from app.schemas import ChangePasswordRequest, RegisterRequest, UpdateProfileRequest


def _ensure_utc(dt: datetime) -> datetime:
    """Normalize a datetime to UTC-aware (SQLite returns naive datetimes)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_user(db: DBSession, data: RegisterRequest) -> User:
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        webhook_token=str(uuid.uuid4()),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(db: DBSession, user: User, data: UpdateProfileRequest) -> User:
    user.name = data.name
    db.commit()
    db.refresh(user)
    return user


def change_user_password(
    db: DBSession, user: User, data: ChangePasswordRequest
) -> None:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if verify_password(data.new_password, user.password_hash):
        raise HTTPException(
            status_code=400, detail="New password must differ from current"
        )
    user.password_hash = hash_password(data.new_password)
    db.commit()


def authenticate_user(db: DBSession, email: str, password: str) -> User | None:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user


def create_session(db: DBSession, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    session = Session(
        token_hash=hash_token(token),
        user_id=user_id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SESSION_DURATION_HOURS),
    )
    db.add(session)
    db.commit()
    return token


def get_session_by_token(db: DBSession, token: str) -> Session | None:
    return db.query(Session).filter(Session.token_hash == hash_token(token)).first()


def delete_session(db: DBSession, session: Session) -> None:
    db.delete(session)
    db.commit()


def extend_session(db: DBSession, session: Session) -> None:
    session.expires_at = datetime.now(timezone.utc) + timedelta(
        hours=SESSION_DURATION_HOURS
    )
    db.commit()


def is_session_expired(session: Session) -> bool:
    return _ensure_utc(session.expires_at) < datetime.now(timezone.utc)


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/api",
        max_age=SESSION_DURATION_HOURS * 3600,
        secure=COOKIE_SECURE,
    )


def get_current_user(request: Request, db: DBSession = Depends(get_db)) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = get_session_by_token(db, token)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if _ensure_utc(session.expires_at) < datetime.now(timezone.utc):
        delete_session(db, session)
        raise HTTPException(status_code=401, detail="Session expired")

    user = db.query(User).filter(User.id == session.user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def delete_expired_sessions(db: DBSession) -> int:
    now = datetime.now(timezone.utc)
    count = db.query(Session).filter(Session.expires_at < now).delete()
    db.commit()
    return count


async def cleanup_expired_sessions():
    import asyncio

    while True:
        await asyncio.sleep(SESSION_CLEANUP_INTERVAL_SECONDS)
        db = SessionLocal()
        try:
            delete_expired_sessions(db)
        finally:
            db.close()
