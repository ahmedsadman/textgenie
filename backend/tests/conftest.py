import hashlib
import os
from unittest.mock import patch

os.environ["GEMINI_API_KEY"] = ""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Category
from app.services.categories import DefaultCategory
from app.services.webhook import parse_message

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=engine)


def _fast_hashpw(password: bytes, salt: bytes) -> bytes:
    return hashlib.sha256(password).hexdigest().encode()


def _fast_checkpw(password: bytes, hashed: bytes) -> bool:
    return hashlib.sha256(password).hexdigest().encode() == hashed


_TABLE_NAMES = [t.name for t in reversed(Base.metadata.sorted_tables)]


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True, scope="session")
def _create_schema():
    Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def setup_db():
    db = TestSessionLocal()
    for default in DefaultCategory:
        db.add(Category(name=default.value, user_id=None))
    db.commit()
    db.close()
    yield
    with engine.connect() as conn:
        for table in _TABLE_NAMES:
            conn.execute(text(f"DELETE FROM {table}"))
        conn.commit()


@pytest.fixture(autouse=True)
def _fast_bcrypt():
    with (
        patch("bcrypt.hashpw", side_effect=_fast_hashpw),
        patch("bcrypt.checkpw", side_effect=_fast_checkpw),
    ):
        yield


@pytest.fixture()
def db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client():
    return TestClient(app)


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


def get_webhook_token(client):
    response = client.get("/api/settings/webhook")
    return response.json()["webhook_token"]


def create_message(client, token, sender="1234", content="hello", timestamp=None):
    payload = {"sender": sender, "content": content}
    if timestamp is not None:
        payload["timestamp"] = timestamp
    return client.post(f"/api/webhook/{token}", json=payload)


@pytest.fixture()
def run_message_parse():
    def _run(message_id, provider):
        with (
            patch("app.services.webhook.build_provider", return_value=provider),
            patch("app.services.webhook.GEMINI_API_KEY", "fake-key"),
            patch("app.services.webhook.SessionLocal", TestSessionLocal),
            patch("app.services.llm.usage.recorder.SessionLocal", TestSessionLocal),
        ):
            parse_message(message_id)

    return _run
