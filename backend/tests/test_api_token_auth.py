"""Token auth for read-only finance endpoints.

The per-user ``webhook_token`` doubles as a read-only mobile API key supplied
via ``Authorization: Bearer <token>``. These tests verify the bearer path,
the cookie regression, error handling, user isolation, and that write
endpoints stay cookie-only.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app
from app.models import User
from tests.conftest import get_webhook_token, register_and_login
from tests.factories import make_bank, make_bill, make_message, make_transaction


def _dt(year, month, day=1):
    return datetime(year, month, day, tzinfo=timezone.utc)


def _anon():
    """A client with no session cookie, exercising the bearer path only."""
    return TestClient(app)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _seed(db, user):
    """Seed one deposit bank, a credit card + bill, and a transaction."""
    make_bank(db, user, "Checking", account_type="deposit")
    card = make_bank(db, user, "Visa", account_type="credit", card_digits="1234|5678")
    bill = make_bill(
        db,
        user,
        normalized_total_due="500.00",
        received_at=_dt(2025, 1),
        bank=card,
        statement_period=_dt(2025, 1).date(),
    )
    tx = make_transaction(db, user, amount="100.00", type="expense", date=_dt(2025, 1))
    return bill, tx


def test_bearer_accepted_on_read_only_finance_endpoints(client, db):
    register_and_login(client)
    token = get_webhook_token(client)
    user = db.query(User).first()
    bill, tx = _seed(db, user)

    anon = _anon()
    endpoints = [
        "/api/banks",
        "/api/transactions",
        "/api/transactions/summary",
        "/api/transactions/trends",
        "/api/bills",
        f"/api/bills/{bill.id}",
        "/api/settings/currency",
        f"/api/messages/{tx.message_id}",
    ]
    for path in endpoints:
        response = anon.get(path, headers=_auth(token))
        assert response.status_code == 200, path


def test_cookie_still_accepted_on_finance_endpoints(client, db):
    # Web regression: the logged-in cookie path must keep working.
    register_and_login(client)
    user = db.query(User).first()
    _seed(db, user)

    for path in ("/api/banks", "/api/transactions", "/api/settings/currency"):
        assert client.get(path).status_code == 200, path


def test_invalid_bearer_returns_401(client, db):
    register_and_login(client)
    response = _anon().get("/api/banks", headers=_auth("not-a-real-token"))
    assert response.status_code == 401


def test_invalid_bearer_does_not_fall_through_to_cookie(client, db):
    # A bad bearer token must 401 even when a valid session cookie is present.
    register_and_login(client)
    response = client.get("/api/banks", headers=_auth("not-a-real-token"))
    assert response.status_code == 401


def test_empty_bearer_returns_401():
    response = _anon().get("/api/banks", headers={"Authorization": "Bearer "})
    assert response.status_code == 401


def test_missing_auth_returns_401():
    response = _anon().get("/api/banks")
    assert response.status_code == 401


def test_bearer_isolated_by_user(client, db):
    register_and_login(client, email="user1@example.com")
    token1 = get_webhook_token(client)
    user1 = db.query(User).filter(User.email == "user1@example.com").first()
    make_bank(db, user1, "OnlyUser1Bank", account_type="deposit")

    register_and_login(client, email="user2@example.com")
    token2 = get_webhook_token(client)

    anon = _anon()
    names1 = [b["name"] for b in anon.get("/api/banks", headers=_auth(token1)).json()]
    names2 = [b["name"] for b in anon.get("/api/banks", headers=_auth(token2)).json()]
    assert "OnlyUser1Bank" in names1
    assert names2 == []


def test_single_message_ownership_across_users(client, db):
    register_and_login(client, email="owner@example.com")
    owner = db.query(User).filter(User.email == "owner@example.com").first()
    message = make_message(db, owner, sender="BANK", received_at=_dt(2025, 1))

    register_and_login(client, email="other@example.com")
    other_token = get_webhook_token(client)

    response = _anon().get(f"/api/messages/{message.id}", headers=_auth(other_token))
    assert response.status_code == 404


def test_write_endpoint_rejects_bearer(client, db):
    register_and_login(client)
    token = get_webhook_token(client)

    response = _anon().post(
        "/api/banks",
        json={"name": "New Bank", "account_type": "deposit"},
        headers=_auth(token),
    )
    assert response.status_code == 401
