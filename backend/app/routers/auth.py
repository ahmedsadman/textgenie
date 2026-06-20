from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as DBSession

from app.config import COOKIE_NAME
from app.database import get_db
from app.models import User
from app.schemas import (
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    UserResponse,
)
from app.services.auth import (
    authenticate_user,
    create_session,
    create_user,
    delete_session,
    extend_session,
    get_current_user,
    get_session_by_token,
    is_session_expired,
    set_session_cookie,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: DBSession = Depends(get_db)):
    return create_user(db, data)


@router.post("/login", response_model=UserResponse)
def login(data: LoginRequest, response: Response, db: DBSession = Depends(get_db)):
    user = authenticate_user(db, data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_session(db, user.id)
    set_session_cookie(response, token)
    return user


@router.post("/logout", response_model=MessageResponse)
def logout(request: Request, response: Response, db: DBSession = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = get_session_by_token(db, token)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    delete_session(db, session)
    response.delete_cookie(key=COOKIE_NAME, path="/api")
    return MessageResponse(message="Logged out successfully")


@router.post("/extend", response_model=MessageResponse)
def extend(request: Request, response: Response, db: DBSession = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = get_session_by_token(db, token)
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if is_session_expired(session):
        delete_session(db, session)
        raise HTTPException(status_code=401, detail="Session expired")

    extend_session(db, session)
    set_session_cookie(response, token)
    return MessageResponse(message="Session extended")


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
