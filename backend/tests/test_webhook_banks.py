from decimal import Decimal

from app.models import Bank
from app.services.llm.base import MetadataResult
from tests.conftest import (
    create_message,
    get_webhook_token,
    register_and_login,
)
from tests.factories import make_mock_provider


def _create_bank(client, name="BRAC Bank"):
    return client.post("/api/banks", json={"name": name})


def _get_bank(client, bank_id):
    banks = client.get("/api/banks").json()
    return next(b for b in banks if b["id"] == bank_id)


def _txn_provider(bank=None, balance=None):
    """Provider that always returns category='transaction' + given metadata."""
    md = MetadataResult(bank=bank, balance=balance) if bank else MetadataResult()
    return make_mock_provider(category="transaction", metadata=md)


# --- Happy path: match + newer message updates balance ---


def test_bank_balance_updated_on_match(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRACBANK", content="Balance: 1500 BDT")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("BRAC Bank", Decimal("1500")))

    bank = _get_bank(client, bank_id)
    assert bank["last_balance"] == "1500.00"
    assert bank["last_balance_at"] is not None


def test_newer_message_overwrites_balance(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(
        client,
        token,
        sender="BRAC",
        content="Balance: 100",
        timestamp=1_000_000_000_000,
    )
    msg1_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(msg1_id, _txn_provider("BRAC Bank", Decimal("100")))

    create_message(
        client,
        token,
        sender="BRAC",
        content="Balance: 500",
        timestamp=2_000_000_000_000,
    )
    msg2_id = next(
        m["id"]
        for m in client.get("/api/messages").json()["messages"]
        if m["id"] != msg1_id
    )
    run_message_parse(msg2_id, _txn_provider("BRAC Bank", Decimal("500")))

    assert _get_bank(client, bank_id)["last_balance"] == "500.00"


# --- Staleness guard ---


def test_older_message_does_not_overwrite(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(
        client,
        token,
        sender="BRAC",
        content="Balance: 500",
        timestamp=2_000_000_000_000,
    )
    newer_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(newer_id, _txn_provider("BRAC Bank", Decimal("500")))

    create_message(
        client,
        token,
        sender="BRAC",
        content="Balance: 100",
        timestamp=1_000_000_000_000,
    )
    older_id = next(
        m["id"]
        for m in client.get("/api/messages").json()["messages"]
        if m["id"] != newer_id
    )
    run_message_parse(older_id, _txn_provider("BRAC Bank", Decimal("100")))

    assert _get_bank(client, bank_id)["last_balance"] == "500.00"


def test_equal_timestamp_does_not_overwrite(client, run_message_parse, db):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(
        client,
        token,
        sender="BRAC",
        content="Balance: 500",
        timestamp=1_500_000_000_000,
    )
    msg1_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(msg1_id, _txn_provider("BRAC Bank", Decimal("500")))

    create_message(
        client,
        token,
        sender="BRAC",
        content="Balance: 999",
        timestamp=1_500_000_000_000,
    )
    msg2_id = next(
        m["id"]
        for m in client.get("/api/messages").json()["messages"]
        if m["id"] != msg1_id
    )
    run_message_parse(msg2_id, _txn_provider("BRAC Bank", Decimal("999")))

    assert _get_bank(client, bank_id)["last_balance"] == "500.00"


def test_manual_put_then_older_sms_does_not_overwrite(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    client.patch(f"/api/banks/{bank_id}", json={"last_balance": "999.00"})

    create_message(
        client, token, sender="BRAC", content="Balance: 1", timestamp=1_000_000_000_000
    )
    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(message_id, _txn_provider("BRAC Bank", Decimal("1")))

    assert _get_bank(client, bank_id)["last_balance"] == "999.00"


# --- No-op cases ---


def test_unknown_bank_name_is_noop(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="X", content="something")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("Some Other Bank", Decimal("500")))

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

    run_message_parse(message_id, make_mock_provider(category="finance"))

    msg = client.get("/api/messages").json()["messages"][0]
    assert msg["category"]["name"] == "finance"


def test_non_transaction_category_does_not_touch_bank(client, run_message_parse):
    """Metadata extraction is gated on category == 'transaction'."""
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    client.post("/api/categories", json={"name": "finance"})
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="Balance: 500")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    # Even though we provide metadata, the gate should skip extract_metadata.
    provider = make_mock_provider(
        category="finance",
        metadata=MetadataResult(bank="BRAC Bank", balance=Decimal("500")),
    )
    run_message_parse(message_id, provider)

    assert _get_bank(client, bank_id)["last_balance"] is None


def test_uncategorized_message_does_not_touch_bank(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="Balance: 200")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, make_mock_provider(category=None))

    assert _get_bank(client, bank_id)["last_balance"] is None


def test_category_only_does_not_touch_bank(client, run_message_parse):
    """Transaction category + empty metadata leaves bank unchanged."""
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="msg")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider())

    assert _get_bank(client, bank_id)["last_balance"] is None


def test_categorize_failure_leaves_bank_unchanged(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="Balance: 1")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(
        message_id,
        make_mock_provider(categorize_raises=RuntimeError("LLM down")),
    )

    assert _get_bank(client, bank_id)["last_balance"] is None


def test_metadata_extraction_failure_leaves_bank_unchanged(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="Balance: 1")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(
        message_id,
        make_mock_provider(
            category="transaction",
            extract_raises=RuntimeError("metadata LLM down"),
        ),
    )

    assert _get_bank(client, bank_id)["last_balance"] is None


def test_bank_match_with_null_balance_does_not_update(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="Some non-balance msg")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("BRAC Bank", None))

    assert _get_bank(client, bank_id)["last_balance"] is None


# --- Cross-user isolation ---


def test_cross_user_bank_isolation(client, run_message_parse, db):
    register_and_login(client, email="user1@example.com")
    user1_bank_id = _create_bank(client, "BRAC Bank").json()["id"]

    register_and_login(client, email="user2@example.com")
    user2_bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="Balance: 700")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("BRAC Bank", Decimal("700")))

    user2_bank = db.query(Bank).filter(Bank.id == user2_bank_id).first()
    user1_bank = db.query(Bank).filter(Bank.id == user1_bank_id).first()
    assert user2_bank.last_balance == Decimal("700.00")
    assert user1_bank.last_balance is None


# --- Case-insensitive bank lookup ---


def test_bank_lookup_is_case_insensitive(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank PLC").json()["id"]
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="Balance: 250")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("brac bank plc", Decimal("250")))

    assert _get_bank(client, bank_id)["last_balance"] == "250.00"


# --- Metadata blacklist ---


def test_blacklisted_sender_skips_metadata_extraction(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    client.put("/api/settings/metadata-blacklist", json={"senders": ["BRAC"]})

    create_message(client, token, sender="BRAC", content="Balance: 500")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    # Even though we'd return metadata, the orchestrator must not call extract_metadata.
    extract_calls = []

    def _extract(self, *a, **k):
        extract_calls.append((a, k))
        return MetadataResult(bank="BRAC Bank", balance=Decimal("500"))

    provider = type(
        "MockProvider",
        (),
        {
            "categorize": lambda self, *a, **k: "transaction",
            "extract_metadata": _extract,
        },
    )()
    run_message_parse(message_id, provider)

    assert extract_calls == []
    assert _get_bank(client, bank_id)["last_balance"] is None
    # The category itself should still be set.
    msg = client.get("/api/messages").json()["messages"][0]
    assert msg["category"]["name"] == "transaction"


def test_blacklist_match_is_case_insensitive(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    client.put("/api/settings/metadata-blacklist", json={"senders": ["bracbank"]})

    create_message(client, token, sender="BRACBANK", content="Balance: 500")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("BRAC Bank", Decimal("500")))

    assert _get_bank(client, bank_id)["last_balance"] is None


def test_non_blacklisted_sender_still_extracts_metadata(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    client.put("/api/settings/metadata-blacklist", json={"senders": ["telco"]})

    create_message(client, token, sender="BRAC", content="Balance: 800")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("BRAC Bank", Decimal("800")))

    assert _get_bank(client, bank_id)["last_balance"] == "800.00"


def test_empty_blacklist_behaves_like_no_blacklist(client, run_message_parse):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    token = get_webhook_token(client)

    # Explicit empty PUT
    client.put("/api/settings/metadata-blacklist", json={"senders": []})

    create_message(client, token, sender="BRAC", content="Balance: 333")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("BRAC Bank", Decimal("333")))

    assert _get_bank(client, bank_id)["last_balance"] == "333.00"


# --- Credit accounts: deterministic card-number routing + balance suppression ---


def _create_credit_bank(client, name="BRAC Credit Card", card_digits="4988|3711"):
    return client.post(
        "/api/banks",
        json={"name": name, "account_type": "credit", "card_digits": card_digits},
    )


def _txn_provider_full(bank, amount, txn_type, balance=None):
    md = MetadataResult(
        bank=bank, balance=balance, amount=amount, transaction_type=txn_type
    )
    return make_mock_provider(category="transaction", metadata=md)


def test_credit_bank_balance_is_never_stored(client, run_message_parse):
    """Even when the LLM returns a balance for a credit bank, the guard drops it."""
    register_and_login(client)
    bank_id = _create_credit_bank(client).json()["id"]
    token = get_webhook_token(client)

    create_message(
        client,
        token,
        sender="BRAC",
        content="Purchase on card 4988****3711. Balance: 50000 BDT",
    )
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("BRAC Credit Card", Decimal("50000")))

    bank = _get_bank(client, bank_id)
    assert bank["last_balance"] is None
    assert bank["last_balance_at"] is None


def test_card_sms_routes_to_credit_bank_over_llm_pick(client, run_message_parse):
    """The card-number regex takes precedence over whatever bank the LLM picked."""
    register_and_login(client)
    deposit_id = _create_bank(client, "BRAC Bank").json()["id"]
    _create_credit_bank(client, name="BRAC Credit Card").json()["id"]
    token = get_webhook_token(client)

    create_message(
        client,
        token,
        sender="BRAC",
        content="Purchase on card 4988****3711 for 200 BDT. Balance: 50000",
    )
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    # LLM incorrectly picks the deposit bank and returns a "balance".
    provider = _txn_provider_full(
        "BRAC Bank", Decimal("200"), "expense", balance=Decimal("50000")
    )
    run_message_parse(message_id, provider)

    # Deposit balance untouched — the SMS was rerouted to the credit account.
    assert _get_bank(client, deposit_id)["last_balance"] is None

    # And the transaction was recorded against the credit bank.
    txns = client.get("/api/transactions").json()["transactions"]
    assert len(txns) == 1
    assert txns[0]["bank_name"] == "BRAC Credit Card"
    assert txns[0]["type"] == "expense"
    assert txns[0]["amount"] == "200.00"


def test_card_match_various_masking_formats(client, run_message_parse):
    """Match 4988****3711, 4988xx3711, and 4988 **** 3711 — but not a bare 3711."""
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    credit_id = _create_credit_bank(client, name="BRAC Credit Card").json()["id"]
    token = get_webhook_token(client)

    for content in [
        "Purchase on card 4988****3711 for 10 BDT",
        "Purchase on card 4988xx3711 for 10 BDT",
        "Purchase on card 4988 **** 3711 for 10 BDT",
    ]:
        create_message(client, token, sender="BRAC", content=content)
        message_id = client.get("/api/messages").json()["messages"][0]["id"]
        run_message_parse(
            message_id, _txn_provider_full("BRAC Bank", Decimal("10"), "expense")
        )

    # Bare last4 alone must NOT trigger a match — routes to LLM pick (BRAC Bank).
    create_message(
        client,
        token,
        sender="BRAC",
        content="Your PIN is 3711. Do not share.",
    )
    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(
        message_id, _txn_provider_full("BRAC Bank", Decimal("1"), "expense")
    )

    txns = client.get("/api/transactions").json()["transactions"]
    assert len(txns) == 4
    on_credit = [
        t for t in txns if t["bank_id"] == credit_id and t["amount"] == "10.00"
    ]
    on_deposit = [t for t in txns if t["bank_id"] != credit_id]
    assert len(on_credit) == 3
    assert len(on_deposit) == 1  # the "PIN 3711" one — bare last4 did not match


def test_deposit_bank_still_stores_balance(client, run_message_parse):
    """Regression: adding credit routing does not break the deposit path."""
    register_and_login(client)
    deposit_id = _create_bank(client, "BRAC Bank").json()["id"]
    _create_credit_bank(client, name="BRAC Credit Card")
    token = get_webhook_token(client)

    create_message(client, token, sender="BRAC", content="Balance: 1234 BDT")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, _txn_provider("BRAC Bank", Decimal("1234")))

    assert _get_bank(client, deposit_id)["last_balance"] == "1234.00"
