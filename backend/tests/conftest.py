import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

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
