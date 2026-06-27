from tests.conftest import (
    create_message,
    get_webhook_token,
    make_mock_provider,
    register_and_login,
)


def _setup_user_with_messages(client, count=3):
    register_and_login(client)
    token = get_webhook_token(client)
    for i in range(count):
        create_message(client, token, sender=f"Sender{i}", content=f"Message {i}")
    return token


def test_list_messages(client):
    _setup_user_with_messages(client, count=3)
    response = client.get("/api/messages")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["messages"]) == 3
    assert data["page"] == 1


def test_list_messages_pagination(client):
    _setup_user_with_messages(client, count=3)
    response = client.get("/api/messages?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["messages"]) == 2
    assert data["page"] == 1

    response2 = client.get("/api/messages?page=2&page_size=2")
    data2 = response2.json()
    assert len(data2["messages"]) == 1
    assert data2["page"] == 2


def test_list_messages_filter_by_category(client, run_message_parse):
    register_and_login(client)
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token, sender="Bank", content="Paid $50")
    create_message(client, token, sender="Mom", content="Hi there")

    messages = client.get("/api/messages").json()["messages"]
    bank_msg_id = next(m["id"] for m in messages if m["sender"] == "Bank")

    run_message_parse(bank_msg_id, make_mock_provider(category="finance"))

    cats = client.get("/api/categories").json()
    finance_id = next(c["id"] for c in cats if c["name"] == "finance")

    response = client.get(f"/api/messages?category_ids={finance_id}")
    data = response.json()
    assert data["total"] == 1
    assert data["messages"][0]["category"]["name"] == "finance"


def test_list_messages_filter_uncategorized(client):
    _setup_user_with_messages(client, count=2)
    response = client.get("/api/messages?category_ids=0")
    data = response.json()
    assert data["total"] == 2
    for msg in data["messages"]:
        assert msg["category"] is None


def test_list_messages_filter_multiple_categories(client, run_message_parse):
    register_and_login(client)
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token, sender="Bank", content="Paid $50")
    create_message(client, token, sender="Mom", content="Hi there")

    messages = client.get("/api/messages").json()["messages"]
    bank_msg_id = next(m["id"] for m in messages if m["sender"] == "Bank")

    run_message_parse(bank_msg_id, make_mock_provider(category="finance"))

    cats = client.get("/api/categories").json()
    finance_id = next(c["id"] for c in cats if c["name"] == "finance")

    response = client.get(f"/api/messages?category_ids={finance_id}&category_ids=0")
    data = response.json()
    assert data["total"] == 2


def test_list_messages_search_unicode(client):
    register_and_login(client)
    token = get_webhook_token(client)
    create_message(client, token, sender="বাবা", content="শুভ জন্মদিন")
    create_message(client, token, sender="Mom", content="Happy birthday")

    response = client.get("/api/messages?search=জন্মদিন")
    data = response.json()
    assert data["total"] == 1
    assert data["messages"][0]["sender"] == "বাবা"


def test_list_messages_search(client):
    register_and_login(client)
    token = get_webhook_token(client)
    create_message(client, token, sender="Bank", content="You paid $50")
    create_message(client, token, sender="Mom", content="Happy birthday")

    response = client.get("/api/messages?search=Bank")
    data = response.json()
    assert data["total"] == 1
    assert data["messages"][0]["sender"] == "Bank"


def test_list_messages_search_content(client):
    register_and_login(client)
    token = get_webhook_token(client)
    create_message(client, token, sender="Bank", content="You paid $50")
    create_message(client, token, sender="Mom", content="Happy birthday")

    response = client.get("/api/messages?search=birthday")
    data = response.json()
    assert data["total"] == 1
    assert data["messages"][0]["content"] == "Happy birthday"


def test_list_messages_search_no_results(client):
    _setup_user_with_messages(client, count=2)
    response = client.get("/api/messages?search=nonexistent")
    data = response.json()
    assert data["total"] == 0
    assert len(data["messages"]) == 0


def test_list_messages_user_isolation(client):
    register_and_login(client, email="user1@example.com")
    token1 = get_webhook_token(client)
    create_message(client, token1, content="User1 message")

    register_and_login(client, email="user2@example.com")
    token2 = get_webhook_token(client)
    create_message(client, token2, content="User2 message")

    response = client.get("/api/messages")
    data = response.json()
    assert data["total"] == 1
    assert data["messages"][0]["content"] == "User2 message"


def test_get_message(client):
    _setup_user_with_messages(client, count=1)
    messages = client.get("/api/messages").json()["messages"]
    msg_id = messages[0]["id"]

    response = client.get(f"/api/messages/{msg_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == msg_id
    assert data["sender"] == "Sender0"
    assert data["content"] == "Message 0"


def test_get_message_not_found(client):
    register_and_login(client)
    response = client.get("/api/messages/9999")
    assert response.status_code == 404


def test_get_other_users_message(client):
    register_and_login(client, email="user1@example.com")
    token1 = get_webhook_token(client)
    create_message(client, token1)
    messages = client.get("/api/messages").json()["messages"]
    msg_id = messages[0]["id"]

    register_and_login(client, email="user2@example.com")
    response = client.get(f"/api/messages/{msg_id}")
    assert response.status_code == 404


def test_get_message_unauthenticated(client):
    response = client.get("/api/messages/1")
    assert response.status_code == 401


def test_delete_message(client):
    _setup_user_with_messages(client, count=1)
    messages = client.get("/api/messages").json()["messages"]
    msg_id = messages[0]["id"]

    response = client.delete(f"/api/messages/{msg_id}")
    assert response.status_code == 200

    remaining = client.get("/api/messages").json()
    assert remaining["total"] == 0


def test_delete_message_not_found(client):
    register_and_login(client)
    response = client.delete("/api/messages/9999")
    assert response.status_code == 404


def test_delete_other_users_message(client):
    register_and_login(client, email="user1@example.com")
    token1 = get_webhook_token(client)
    create_message(client, token1)
    messages = client.get("/api/messages").json()["messages"]
    msg_id = messages[0]["id"]

    register_and_login(client, email="user2@example.com")
    response = client.delete(f"/api/messages/{msg_id}")
    assert response.status_code == 404


def test_list_messages_unauthenticated(client):
    response = client.get("/api/messages")
    assert response.status_code == 401


def test_delete_message_unauthenticated(client):
    response = client.delete("/api/messages/1")
    assert response.status_code == 401


# --- Senders endpoint ---


def test_senders_empty_when_no_messages(client):
    register_and_login(client)
    response = client.get("/api/messages/senders")
    assert response.status_code == 200
    assert response.json() == []


def test_senders_dedups_and_orders_by_recency(client):
    register_and_login(client)
    token = get_webhook_token(client)
    create_message(
        client, token, sender="BRAC", content="m1", timestamp=1_000_000_000_000
    )
    create_message(
        client, token, sender="EBL", content="m2", timestamp=2_000_000_000_000
    )
    create_message(
        client, token, sender="BRAC", content="m3", timestamp=3_000_000_000_000
    )
    create_message(
        client, token, sender="Telco", content="m4", timestamp=500_000_000_000
    )

    response = client.get("/api/messages/senders")
    assert response.status_code == 200
    # BRAC's most recent is 3T, EBL is 2T, Telco is 0.5T
    assert response.json() == ["BRAC", "EBL", "Telco"]


def test_senders_cross_user_isolation(client):
    register_and_login(client, email="user1@example.com")
    token1 = get_webhook_token(client)
    create_message(client, token1, sender="UserOneSender", content="x")

    register_and_login(client, email="user2@example.com")
    token2 = get_webhook_token(client)
    create_message(client, token2, sender="UserTwoSender", content="y")

    response = client.get("/api/messages/senders")
    assert response.json() == ["UserTwoSender"]


def test_senders_unauthenticated(client):
    response = client.get("/api/messages/senders")
    assert response.status_code == 401
