from tests.conftest import create_message, get_webhook_token, register_and_login


def test_webhook_creates_message(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = create_message(client, token, sender="Bank", content="You paid $50")
    assert response.status_code == 202
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
    assert response.status_code == 202

    messages = client.get("/api/messages").json()["messages"]
    assert "2024-06-21" in messages[0]["received_at"]


def test_webhook_falls_back_when_no_timestamp(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = create_message(client, token)
    assert response.status_code == 202

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["received_at"] is not None


def test_webhook_falls_back_on_invalid_timestamp(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = create_message(client, token, timestamp=-999999999999999)
    assert response.status_code == 202

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["received_at"] is not None


def test_webhook_categorizes_with_llm(client, run_categorization):
    register_and_login(client)
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token, sender="Bank", content="You paid $50")

    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    mock_provider = type(
        "MockProvider", (), {"categorize_message": lambda self, *a: "finance"}
    )()
    run_categorization(message_id, mock_provider)

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["category"]["name"] == "finance"


def test_webhook_uncategorized_when_llm_returns_none(client, run_categorization):
    register_and_login(client)
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token)

    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    mock_provider = type(
        "MockProvider", (), {"categorize_message": lambda self, *a: None}
    )()
    run_categorization(message_id, mock_provider)

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["category"] is None


def test_webhook_uncategorized_when_no_categories(client):
    register_and_login(client)
    token = get_webhook_token(client)
    create_message(client, token)

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["category"] is None


def test_webhook_uncategorized_when_llm_fails(client, run_categorization):
    register_and_login(client)
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token)

    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    def _raise(*a):
        raise RuntimeError("LLM down")

    mock_provider = type("MockProvider", (), {"categorize_message": _raise})()
    run_categorization(message_id, mock_provider)

    messages = client.get("/api/messages").json()["messages"]
    assert messages[0]["category"] is None


def test_webhook_creates_message_with_unicode(client):
    register_and_login(client)
    token = get_webhook_token(client)
    response = create_message(client, token, sender="বাবা", content="শুভ জন্মদিন 🎂")
    assert response.status_code == 202

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
