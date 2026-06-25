from decimal import Decimal

from app.models import Bank
from app.services.llm.base import MessageParseResult
from tests.conftest import create_message, get_webhook_token, register_and_login


def _mock_provider(result: MessageParseResult):
    return type("MockProvider", (), {"parse_message": lambda self, *a, **k: result})()


def _create_bank(client, name="BRAC Bank", senders=None, templates=None):
    payload = {"name": name}
    if senders is not None:
        payload["senders"] = senders
    if templates is not None:
        payload["templates"] = templates
    return client.post("/api/banks", json=payload)


def _get_bank(client, bank_id):
    banks = client.get("/api/banks").json()
    return next(b for b in banks if b["id"] == bank_id)


# --- Happy path: template match updates balance ---


def test_bank_balance_updated_on_template_match(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(
        client,
        "BRAC Bank",
        senders=["BRACBANK"],
        templates=["Balance: {{balance}} BDT"],
    ).json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRACBANK", content="Balance: 1,500.00 BDT")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _mock_provider(MessageParseResult()))

    bank = _get_bank(client, bank_id)
    assert bank["last_balance"] == "1500.00"
    assert bank["last_balance_at"] is not None


def test_newer_message_overwrites_balance(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(
        client,
        "BRAC Bank",
        senders=["BRACBANK"],
        templates=["Balance: {{balance}} BDT"],
    ).json()["id"]
    token = get_webhook_token(client)

    create_message(
        client,
        token,
        sender="BRACBANK",
        content="Balance: 100 BDT",
        timestamp=1_000_000_000_000,
    )
    msg1_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(msg1_id, _mock_provider(MessageParseResult()))

    create_message(
        client,
        token,
        sender="BRACBANK",
        content="Balance: 500 BDT",
        timestamp=2_000_000_000_000,
    )
    msg2_id = next(
        m["id"]
        for m in client.get("/api/messages").json()["messages"]
        if m["id"] != msg1_id
    )
    run_message_parse(msg2_id, _mock_provider(MessageParseResult()))

    assert _get_bank(client, bank_id)["last_balance"] == "500.00"


# --- Staleness guard ---


def test_older_message_does_not_overwrite(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(
        client,
        "BRAC Bank",
        senders=["BRACBANK"],
        templates=["Balance: {{balance}} BDT"],
    ).json()["id"]
    token = get_webhook_token(client)

    create_message(
        client,
        token,
        sender="BRACBANK",
        content="Balance: 500 BDT",
        timestamp=2_000_000_000_000,
    )
    newer_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(newer_id, _mock_provider(MessageParseResult()))

    create_message(
        client,
        token,
        sender="BRACBANK",
        content="Balance: 100 BDT",
        timestamp=1_000_000_000_000,
    )
    older_id = next(
        m["id"]
        for m in client.get("/api/messages").json()["messages"]
        if m["id"] != newer_id
    )
    run_message_parse(older_id, _mock_provider(MessageParseResult()))

    assert _get_bank(client, bank_id)["last_balance"] == "500.00"


def test_equal_timestamp_does_not_overwrite(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(
        client,
        "BRAC Bank",
        senders=["BRACBANK"],
        templates=["Balance: {{balance}} BDT"],
    ).json()["id"]
    token = get_webhook_token(client)

    create_message(
        client,
        token,
        sender="BRACBANK",
        content="Balance: 500 BDT",
        timestamp=1_500_000_000_000,
    )
    msg1_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(msg1_id, _mock_provider(MessageParseResult()))

    create_message(
        client,
        token,
        sender="BRACBANK",
        content="Balance: 999 BDT",
        timestamp=1_500_000_000_000,
    )
    msg2_id = next(
        m["id"]
        for m in client.get("/api/messages").json()["messages"]
        if m["id"] != msg1_id
    )
    run_message_parse(msg2_id, _mock_provider(MessageParseResult()))

    assert _get_bank(client, bank_id)["last_balance"] == "500.00"


def test_manual_put_then_older_sms_does_not_overwrite(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(
        client,
        "BRAC Bank",
        senders=["BRACBANK"],
        templates=["Balance: {{balance}} BDT"],
    ).json()["id"]
    token = get_webhook_token(client)

    client.put(f"/api/banks/{bank_id}", json={"last_balance": "999.00"})

    create_message(
        client,
        token,
        sender="BRACBANK",
        content="Balance: 1 BDT",
        timestamp=1_000_000_000_000,
    )
    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(message_id, _mock_provider(MessageParseResult()))

    assert _get_bank(client, bank_id)["last_balance"] == "999.00"


# --- No-op cases ---


def test_unknown_sender_is_noop(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(
        client,
        "BRAC Bank",
        senders=["BRACBANK"],
        templates=["Balance: {{balance}} BDT"],
    ).json()["id"]
    client.post("/api/categories", json={"name": "transaction"})
    token = get_webhook_token(client)

    create_message(client, token, sender="UNKNOWN", content="Balance: 500 BDT")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(
        message_id, _mock_provider(MessageParseResult(category="transaction"))
    )

    bank = _get_bank(client, bank_id)
    assert bank["last_balance"] is None
    msg = client.get("/api/messages").json()["messages"][0]
    assert msg["category"]["name"] == "transaction"


def test_user_with_no_banks_categorization_still_works(client, run_message_parse):
    register_and_login(client)
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token, sender="X", content="msg")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(
        message_id, _mock_provider(MessageParseResult(category="finance"))
    )

    msg = client.get("/api/messages").json()["messages"][0]
    assert msg["category"]["name"] == "finance"


def test_no_template_match_does_not_touch_bank(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(
        client,
        "BRAC Bank",
        senders=["BRACBANK"],
        templates=["Balance: {{balance}} BDT"],
    ).json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRACBANK", content="Your ticket is confirmed")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _mock_provider(MessageParseResult()))

    assert _get_bank(client, bank_id)["last_balance"] is None


def test_template_match_and_categorization_together(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(
        client,
        "BRAC Bank",
        senders=["BRACBANK"],
        templates=["Balance: {{balance}} BDT"],
    ).json()["id"]
    client.post("/api/categories", json={"name": "transaction"})
    token = get_webhook_token(client)

    create_message(client, token, sender="BRACBANK", content="Balance: 200 BDT")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(
        message_id, _mock_provider(MessageParseResult(category="transaction"))
    )

    assert _get_bank(client, bank_id)["last_balance"] == "200.00"
    msg = client.get("/api/messages").json()["messages"][0]
    assert msg["category"]["name"] == "transaction"


def test_llm_failure_does_not_affect_template_extraction(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(
        client,
        "BRAC Bank",
        senders=["BRACBANK"],
        templates=["Balance: {{balance}} BDT"],
    ).json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRACBANK", content="Balance: 1000 BDT")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    def _raise(*a, **k):
        raise RuntimeError("LLM down")

    run_message_parse(message_id, type("MockProvider", (), {"parse_message": _raise})())

    assert _get_bank(client, bank_id)["last_balance"] == "1000.00"
    assert client.get("/api/messages").json()["messages"][0]["category"] is None


# --- Cross-user isolation ---


def test_cross_user_bank_isolation(client, run_message_parse, db):
    register_and_login(client, email="user1@example.com")
    user1_bank_id = _create_bank(
        client, "BRAC Bank", senders=["BRACBANK"], templates=["Balance: {{balance}}"]
    ).json()["id"]

    register_and_login(client, email="user2@example.com")
    user2_bank_id = _create_bank(
        client, "BRAC Bank", senders=["BRACBANK"], templates=["Balance: {{balance}}"]
    ).json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRACBANK", content="Balance: 700")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _mock_provider(MessageParseResult()))

    user2_bank = db.query(Bank).filter(Bank.id == user2_bank_id).first()
    user1_bank = db.query(Bank).filter(Bank.id == user1_bank_id).first()
    assert user2_bank.last_balance == Decimal("700")
    assert user1_bank.last_balance is None
