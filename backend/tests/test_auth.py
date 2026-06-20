from datetime import datetime, timedelta, timezone

from app.config import COOKIE_NAME
from app.models import Session, User
from app.services.auth import delete_expired_sessions, hash_password, hash_token


def register(
    client, name="Test User", email="test@example.com", password="password123"
):
    return client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password},
    )


def login(client, email="test@example.com", password="password123"):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def register_and_login(
    client, name="Test User", email="test@example.com", password="password123"
):
    register(client, name=name, email=email, password=password)
    return login(client, email=email, password=password)


def test_register_success(client):
    response = register(client)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email(client):
    register(client)
    response = register(client)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"]


def test_register_missing_fields(client):
    response = client.post("/api/auth/register", json={"email": "test@example.com"})
    assert response.status_code == 422


def test_register_invalid_email(client):
    response = register(client, email="not-an-email")
    assert response.status_code == 422


def test_register_short_password(client):
    response = register(client, password="short")
    assert response.status_code == 422


def test_login_success(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert COOKIE_NAME in response.cookies


def test_login_wrong_password(client):
    register(client)
    response = login(client, password="wrongpassword")
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_nonexistent_email(client):
    response = login(client, email="nobody@example.com")
    assert response.status_code == 401
    assert "Invalid email or password" in response.json()["detail"]


def test_login_missing_fields(client):
    response = client.post("/api/auth/login", json={})
    assert response.status_code == 422


def test_logout_success(client, db):
    register_and_login(client)
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"
    assert db.query(Session).count() == 0


def test_logout_without_session(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 401


def test_me_authenticated(client):
    register_and_login(client)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_me_unauthenticated(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_expired_session(client, db):
    register_and_login(client)
    session = db.query(Session).first()
    session.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()

    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_extend_session(client, db):
    register_and_login(client)
    session_before = db.query(Session).first()
    expires_before = session_before.expires_at

    response = client.post("/api/auth/extend")
    assert response.status_code == 200
    assert response.json()["message"] == "Session extended"

    db.refresh(session_before)
    assert session_before.expires_at > expires_before


def test_extend_unauthenticated(client):
    response = client.post("/api/auth/extend")
    assert response.status_code == 401


def test_delete_expired_sessions(db):
    user = User(
        name="Test",
        email="test@example.com",
        password_hash=hash_password("password123"),
    )
    db.add(user)
    db.commit()

    expired_session = Session(
        token_hash=hash_token("expired-token"),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    valid_session = Session(
        token_hash=hash_token("valid-token"),
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )
    db.add_all([expired_session, valid_session])
    db.commit()

    count = delete_expired_sessions(db)
    assert count == 1
    assert db.query(Session).count() == 1
    remaining = db.query(Session).first()
    assert remaining.token_hash == hash_token("valid-token")
