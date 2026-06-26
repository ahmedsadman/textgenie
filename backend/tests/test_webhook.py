from unittest.mock import patch

from app.services.webhook import parse_message
from tests.conftest import (
    TestSessionLocal,
    create_message,
    get_webhook_token,
    make_mock_provider,
    register_and_login,
)


def test_webhook_creates_message(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = create_message(client, token, sender="Bank", content="You paid $50")
    assert response.status_code == 201
    assert response.json()["message"] == "Message received"

    messages = client.get("/api/messages").json()["messages"]
    assert len(messages) == 1
    assert messages[0]["sender"] == "Bank"
    assert messages[0]["content"] == "You paid $50"


def test_webhook_invalid_token(client):
    response = create_message(client, "invalid-token")
    assert response.status_code == 404


def test_webhook_parses_unix_ms_timestamp(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = create_message(client, token, timestamp=1719000000000)
    assert response.status_code == 201

    messages = client.get("/api/messages").json()["messages"]
    received_at = messages[0]["received_at"]
    assert "2024-06-21" in received_at
    assert received_at.endswith("+00:00") or received_at.endswith("Z")


def test_webhook_falls_back_when_no_timestamp(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = create_message(client, token)
    assert response.status_code == 201

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["received_at"] is not None


def test_webhook_falls_back_on_invalid_timestamp(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = create_message(client, token, timestamp=-999999999999999)
    assert response.status_code == 201

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["received_at"] is not None


def test_webhook_categorizes_with_llm(client, run_message_parse):
    register_and_login(client)
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token, sender="Bank", content="You paid $50")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, make_mock_provider(category="finance"))

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["category"]["name"] == "finance"


def test_webhook_uncategorized_when_llm_returns_none(client, run_message_parse):
    register_and_login(client)
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token)
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, make_mock_provider(category=None))

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["category"] is None


def test_webhook_uncategorized_when_no_categories(client):
    register_and_login(client)
    token = get_webhook_token(client)
    create_message(client, token)

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["category"] is None


def test_webhook_uncategorized_when_llm_fails(client, run_message_parse):
    register_and_login(client)
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token)
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(
        message_id,
        make_mock_provider(categorize_raises=RuntimeError("LLM down")),
    )

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["category"] is None


def test_parse_message_skips_llm_in_testsuite(client):
    register_and_login(client)
    client.post("/api/categories", json={"name": "transaction"})
    token = get_webhook_token(client)
    create_message(client, token, sender="BRAC", content="Balance: 500")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    with (
        patch("app.services.webhook.get_llm_provider") as mock_get_provider,
        patch("app.services.webhook.SessionLocal", TestSessionLocal),
    ):
        parse_message(message_id)

    mock_get_provider.assert_not_called()
    msg = client.get("/api/messages").json()["messages"][0]
    assert msg["category"] is None


def test_webhook_creates_message_with_unicode(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = create_message(client, token, sender="বাবা", content="শুভ জন্মদিন 🎂")
    assert response.status_code == 201

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["sender"] == "বাবা"
    assert messages[0]["content"] == "শুভ জন্মদিন 🎂"


def test_webhook_validates_payload_missing_sender(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = client.post(f"/api/webhook/{token}", json={"content": "hello"})
    assert response.status_code == 422


def test_webhook_validates_payload_missing_content(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = client.post(f"/api/webhook/{token}", json={"sender": "1234"})
    assert response.status_code == 422
