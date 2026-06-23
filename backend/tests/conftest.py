from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.services.webhook import parse_message

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(bind=engine)


def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


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
            patch("app.services.webhook.get_llm_provider", return_value=provider),
            patch("app.services.webhook.GEMINI_API_KEY", "fake-key"),
            patch("app.services.webhook.SessionLocal", TestSessionLocal),
        ):
            parse_message(message_id)

    return _run
