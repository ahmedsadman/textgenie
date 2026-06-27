from decimal import Decimal

from app.models import Transaction
from app.services.llm.base import MetadataResult
from tests.conftest import (
    create_message,
    get_webhook_token,
    make_mock_provider,
    register_and_login,
)


def _create_bank(client, name="BRAC Bank"):
    return client.post("/api/banks", json={"name": name})


def _txn_provider(bank=None, balance=None, amount=None, transaction_type=None):
    md = MetadataResult(
        bank=bank,
        balance=balance,
        amount=amount,
        transaction_type=transaction_type,
    )
    return make_mock_provider(category="transaction", metadata=md)


def _post_and_parse(
    client,
    run_message_parse,
    provider,
    *,
    sender="BRAC",
    content="msg",
    timestamp=None,
):
    token = get_webhook_token(client)
    create_message(client, token, sender=sender, content=content, timestamp=timestamp)
    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(message_id, provider)
    return message_id


# --- Webhook persistence ---


def test_webhook_creates_transaction_row(client, run_message_parse, db):
    register_and_login(client)
    bank_id = _create_bank(client, "BRAC Bank").json()["id"]
    _post_and_parse(
        client,
        run_message_parse,
        _txn_provider(
            bank="BRAC Bank",
            balance=Decimal("1500"),
            amount=Decimal("50"),
            transaction_type="expense",
        ),
        content="Debit 50 BDT. Bal 1500 BDT",
    )

    rows = db.query(Transaction).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.bank_id == bank_id
    assert row.amount == Decimal("50.00")
    assert row.type == "expense"
    assert row.date is not None


def test_webhook_skips_when_amount_missing(client, run_message_parse, db):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    _post_and_parse(
        client,
        run_message_parse,
        _txn_provider(
            bank="BRAC Bank",
            balance=Decimal("1500"),
            amount=None,
            transaction_type="expense",
        ),
    )

    assert db.query(Transaction).count() == 0


def test_webhook_skips_when_type_missing(client, run_message_parse, db):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    _post_and_parse(
        client,
        run_message_parse,
        _txn_provider(
            bank="BRAC Bank",
            balance=Decimal("1500"),
            amount=Decimal("50"),
            transaction_type=None,
        ),
    )

    assert db.query(Transaction).count() == 0


def test_webhook_records_transaction_when_bank_unmatched(client, run_message_parse, db):
    """LLM finds an amount + type but bank name doesn't match any user bank.
    Transaction is still recorded with bank_id=None."""
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    _post_and_parse(
        client,
        run_message_parse,
        _txn_provider(
            bank="Some Other Bank",
            balance=Decimal("100"),
            amount=Decimal("25"),
            transaction_type="income",
        ),
    )

    rows = db.query(Transaction).all()
    assert len(rows) == 1
    assert rows[0].bank_id is None
    assert rows[0].amount == Decimal("25.00")
    assert rows[0].type == "income"


def test_webhook_idempotent_on_reparse(client, run_message_parse, db):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    provider = _txn_provider(
        bank="BRAC Bank",
        balance=Decimal("1500"),
        amount=Decimal("50"),
        transaction_type="expense",
    )
    token = get_webhook_token(client)
    create_message(client, token, sender="BRAC", content="Debit 50")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, provider)
    run_message_parse(message_id, provider)

    assert db.query(Transaction).count() == 1


def test_webhook_skips_transaction_when_no_banks_configured(
    client, run_message_parse, db
):
    """Bank gate keeps metadata extraction off entirely when user has no banks."""
    register_and_login(client)
    _post_and_parse(
        client,
        run_message_parse,
        _txn_provider(
            bank="BRAC Bank",
            balance=Decimal("1500"),
            amount=Decimal("50"),
            transaction_type="expense",
        ),
    )

    assert db.query(Transaction).count() == 0


def test_webhook_skips_transaction_for_blacklisted_sender(
    client, run_message_parse, db
):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    client.put("/api/settings/metadata-blacklist", json={"senders": ["BRAC"]})

    _post_and_parse(
        client,
        run_message_parse,
        _txn_provider(
            bank="BRAC Bank",
            balance=Decimal("1500"),
            amount=Decimal("50"),
            transaction_type="expense",
        ),
    )

    assert db.query(Transaction).count() == 0


# --- API ---


def _seed_transactions(client, run_message_parse, items):
    """Seed transactions by calling the webhook with stub providers.

    items: list of (sender, content, type, amount, timestamp_ms)
    """
    token = get_webhook_token(client)
    for sender, content, t_type, amount, ts in items:
        create_message(client, token, sender=sender, content=content, timestamp=ts)
        message_id = client.get("/api/messages").json()["messages"][0]["id"]
        provider = _txn_provider(
            bank="BRAC Bank",
            balance=Decimal("0"),
            amount=Decimal(str(amount)),
            transaction_type=t_type,
        )
        run_message_parse(message_id, provider)


def test_get_transactions_empty(client):
    register_and_login(client)
    response = client.get("/api/transactions")
    assert response.status_code == 200
    body = response.json()
    assert body["transactions"] == []
    assert body["total"] == 0
    assert body["totals"] == {"income": "0.00", "expense": "0.00"}


def test_get_transactions_returns_list_with_totals(client, run_message_parse):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    _seed_transactions(
        client,
        run_message_parse,
        [
            ("BRAC", "credit", "income", 100, 1_700_000_000_000),
            ("BRAC", "debit", "expense", 30, 1_700_000_001_000),
            ("BRAC", "credit", "income", 50, 1_700_000_002_000),
        ],
    )

    body = client.get("/api/transactions").json()
    assert body["total"] == 3
    assert len(body["transactions"]) == 3
    assert body["totals"] == {"income": "150.00", "expense": "30.00"}
    # ordered date desc
    dates = [t["date"] for t in body["transactions"]]
    assert dates == sorted(dates, reverse=True)
    # joined fields populated
    first = body["transactions"][0]
    assert first["sender"] == "BRAC"
    assert first["bank_name"] == "BRAC Bank"


def test_get_transactions_pagination(client, run_message_parse):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    items = [
        ("BRAC", f"msg{i}", "expense", 10, 1_700_000_000_000 + i * 1000)
        for i in range(5)
    ]
    _seed_transactions(client, run_message_parse, items)

    page1 = client.get("/api/transactions?page=1&page_size=2").json()
    page2 = client.get("/api/transactions?page=2&page_size=2").json()
    page3 = client.get("/api/transactions?page=3&page_size=2").json()

    assert page1["total"] == 5
    assert len(page1["transactions"]) == 2
    assert len(page2["transactions"]) == 2
    assert len(page3["transactions"]) == 1
    # totals are over full range, not per page
    assert page1["totals"] == {"income": "0.00", "expense": "50.00"}
    assert page2["totals"] == page1["totals"]


def test_get_transactions_date_filter(client, run_message_parse):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    _seed_transactions(
        client,
        run_message_parse,
        [
            ("BRAC", "old", "expense", 10, 1_600_000_000_000),  # 2020-09
            ("BRAC", "mid", "expense", 20, 1_700_000_000_000),  # 2023-11
            ("BRAC", "new", "income", 30, 1_750_000_000_000),  # 2025-06
        ],
    )

    # Filter to the middle window only
    body = client.get(
        "/api/transactions",
        params={
            "from_date": "2023-01-01T00:00:00Z",
            "to_date": "2024-01-01T00:00:00Z",
        },
    ).json()
    assert body["total"] == 1
    assert body["transactions"][0]["amount"] == "20.00"
    assert body["totals"] == {"income": "0.00", "expense": "20.00"}


def test_get_transactions_isolated_by_user(client, run_message_parse):
    register_and_login(client, email="user1@example.com")
    _create_bank(client, "BRAC Bank")
    _seed_transactions(
        client,
        run_message_parse,
        [("BRAC", "u1", "income", 100, 1_700_000_000_000)],
    )

    register_and_login(client, email="user2@example.com")
    body = client.get("/api/transactions").json()
    assert body["total"] == 0
    assert body["transactions"] == []


def test_get_transactions_unauthenticated(client):
    response = client.get("/api/transactions")
    assert response.status_code == 401
