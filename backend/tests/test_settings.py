from tests.conftest import (
    create_message,
    get_webhook_token,
    register_and_login,
)


def test_get_webhook_settings(client):
    register_and_login(client)
    response = client.get("/api/settings/webhook")
    assert response.status_code == 200
    data = response.json()
    assert "webhook_url" in data
    assert "webhook_token" in data
    assert data["webhook_token"] in data["webhook_url"]


def test_get_webhook_unauthenticated(client):
    response = client.get("/api/settings/webhook")
    assert response.status_code == 401


def test_regenerate_token(client):
    register_and_login(client)
    old_token = get_webhook_token(client)
    response = client.post("/api/settings/webhook/regenerate")
    assert response.status_code == 200
    new_token = response.json()["webhook_token"]
    assert new_token != old_token


def test_regenerate_invalidates_old_token(client):
    register_and_login(client)
    old_token = get_webhook_token(client)

    client.post("/api/settings/webhook/regenerate")

    response = create_message(client, old_token)
    assert response.status_code == 404


def test_regenerate_new_token_works(client):
    register_and_login(client)
    client.post("/api/settings/webhook/regenerate")
    new_token = get_webhook_token(client)

    response = create_message(client, new_token)
    assert response.status_code == 201


def test_regenerate_unauthenticated(client):
    response = client.post("/api/settings/webhook/regenerate")
    assert response.status_code == 401


# --- Currency ---


def test_get_currency_default_is_bdt(client):
    register_and_login(client)
    response = client.get("/api/settings/currency")
    assert response.status_code == 200
    assert response.json() == {"currency": "BDT"}


def test_get_currency_unauthenticated(client):
    response = client.get("/api/settings/currency")
    assert response.status_code == 401


def test_put_currency_persists(client):
    register_and_login(client)
    response = client.put("/api/settings/currency", json={"currency": "USD"})
    assert response.status_code == 200
    assert response.json() == {"currency": "USD"}
    assert client.get("/api/settings/currency").json() == {"currency": "USD"}


def test_put_currency_rejects_unknown_value(client):
    register_and_login(client)
    response = client.put("/api/settings/currency", json={"currency": "XYZ"})
    assert response.status_code == 422  # pydantic Literal validation


def test_put_currency_rejects_missing_value(client):
    register_and_login(client)
    response = client.put("/api/settings/currency", json={})
    assert response.status_code == 422


def test_put_currency_unauthenticated(client):
    response = client.put("/api/settings/currency", json={"currency": "USD"})
    assert response.status_code == 401


def test_put_currency_change_clears_bank_balances(client):
    from decimal import Decimal

    from app.services.llm.base import MetadataResult
    from tests.conftest import create_message
    from tests.factories import make_mock_provider

    register_and_login(client)
    bank_id = client.post("/api/banks", json={"name": "BRAC"}).json()["id"]
    token = get_webhook_token(client)

    # Seed a balance under the default BDT preference.
    create_message(client, token, sender="BRAC", content="Balance: 1500")
    from unittest.mock import patch

    from app.services.webhook import parse_message
    from tests.conftest import TestSessionLocal

    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    provider = make_mock_provider(
        category="transaction",
        metadata=MetadataResult(
            bank="BRAC", balance=Decimal("1500"), original_currency="BDT"
        ),
    )
    with (
        patch("app.services.webhook.build_provider", return_value=provider),
        patch("app.services.webhook.GEMINI_API_KEY", "fake-key"),
        patch("app.services.webhook.SessionLocal", TestSessionLocal),
    ):
        parse_message(message_id)

    assert (
        next(b for b in client.get("/api/banks").json() if b["id"] == bank_id)[
            "last_balance"
        ]
        == "1500.00"
    )

    # Switch preference. Balance should be cleared.
    client.put("/api/settings/currency", json={"currency": "USD"})
    bank = next(b for b in client.get("/api/banks").json() if b["id"] == bank_id)
    assert bank["last_balance"] is None
    assert bank["last_balance_at"] is None


def test_put_currency_same_value_does_not_clear_balances(client):
    from decimal import Decimal
    from unittest.mock import patch

    from app.services.llm.base import MetadataResult
    from app.services.webhook import parse_message
    from tests.conftest import TestSessionLocal, create_message
    from tests.factories import make_mock_provider

    register_and_login(client)
    bank_id = client.post("/api/banks", json={"name": "BRAC"}).json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="Balance: 500")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    provider = make_mock_provider(
        category="transaction",
        metadata=MetadataResult(
            bank="BRAC", balance=Decimal("500"), original_currency="BDT"
        ),
    )
    with (
        patch("app.services.webhook.build_provider", return_value=provider),
        patch("app.services.webhook.GEMINI_API_KEY", "fake-key"),
        patch("app.services.webhook.SessionLocal", TestSessionLocal),
    ):
        parse_message(message_id)

    client.put("/api/settings/currency", json={"currency": "BDT"})  # unchanged
    bank = next(b for b in client.get("/api/banks").json() if b["id"] == bank_id)
    assert bank["last_balance"] == "500.00"


def test_put_currency_does_not_mutate_existing_transactions(client):
    from decimal import Decimal
    from unittest.mock import patch

    from app.services.llm.base import MetadataResult
    from app.services.webhook import parse_message
    from tests.conftest import TestSessionLocal, create_message
    from tests.factories import make_mock_provider

    register_and_login(client)
    client.post("/api/banks", json={"name": "BRAC"})
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="debit 50 BDT")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    provider = make_mock_provider(
        category="transaction",
        metadata=MetadataResult(
            bank="BRAC",
            balance=Decimal("100"),
            amount=Decimal("50"),
            transaction_type="expense",
            original_currency="BDT",
        ),
    )
    with (
        patch("app.services.webhook.build_provider", return_value=provider),
        patch("app.services.webhook.GEMINI_API_KEY", "fake-key"),
        patch("app.services.webhook.SessionLocal", TestSessionLocal),
    ):
        parse_message(message_id)

    txns_before = client.get("/api/transactions").json()["transactions"]
    assert txns_before[0]["normalized_currency"] == "BDT"

    client.put("/api/settings/currency", json={"currency": "USD"})

    txns_after = client.get("/api/transactions").json()["transactions"]
    assert txns_after[0]["normalized_currency"] == "BDT"
    assert txns_after[0]["normalized_amount"] == "50.00"
