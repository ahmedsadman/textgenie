from datetime import datetime, timezone
from decimal import Decimal

from app.models import Transaction, User
from app.services.llm.base import MetadataResult
from tests.conftest import (
    create_message,
    get_webhook_token,
    register_and_login,
)
from tests.factories import make_bank, make_bill, make_mock_provider


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
    assert row.normalized_amount == Decimal("50.00")
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
    assert rows[0].normalized_amount == Decimal("25.00")
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
    assert first["bank_account_type"] == "deposit"


def test_get_transactions_exposes_credit_account_type(client, run_message_parse):
    register_and_login(client)
    client.post(
        "/api/banks",
        json={
            "name": "Amex Card",
            "account_type": "credit",
            "card_digits": "1234|5678",
        },
    )
    token = get_webhook_token(client)
    create_message(
        client,
        token,
        sender="AMEX",
        content="Purchase 25 BDT",
        timestamp=1_700_000_000_000,
    )
    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(
        message_id,
        _txn_provider(
            bank="Amex Card",
            amount=Decimal("25"),
            transaction_type="expense",
        ),
    )

    body = client.get("/api/transactions").json()
    assert body["total"] == 1
    tx = body["transactions"][0]
    assert tx["bank_name"] == "Amex Card"
    assert tx["bank_account_type"] == "credit"


def test_get_transactions_bank_account_type_null_when_unmatched(
    client, run_message_parse
):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    token = get_webhook_token(client)
    create_message(
        client,
        token,
        sender="OTHER",
        content="Debit 10 BDT",
        timestamp=1_700_000_000_000,
    )
    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(
        message_id,
        _txn_provider(
            bank="Some Other Bank",
            amount=Decimal("10"),
            transaction_type="expense",
        ),
    )

    body = client.get("/api/transactions").json()
    tx = body["transactions"][0]
    assert tx["bank_id"] is None
    assert tx["bank_name"] is None
    assert tx["bank_account_type"] is None


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
    assert body["transactions"][0]["normalized_amount"] == "20.00"
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


# --- PATCH /api/transactions/{id} ---


def _create_expense(client, run_message_parse, *, amount="50"):
    _create_bank(client, "BRAC Bank")
    _seed_transactions(
        client,
        run_message_parse,
        [("BRAC", "debit", "expense", amount, 1_700_000_000_000)],
    )
    return client.get("/api/transactions").json()["transactions"][0]


def test_patch_transaction_changes_type(client, run_message_parse):
    register_and_login(client)
    tx = _create_expense(client, run_message_parse)

    response = client.patch(f"/api/transactions/{tx['id']}", json={"type": "income"})

    assert response.status_code == 200
    assert response.json()["type"] == "income"
    body = client.get("/api/transactions").json()
    assert body["transactions"][0]["type"] == "income"
    assert body["totals"] == {"income": "50.00", "expense": "0.00"}


def test_patch_transaction_to_transfer_excludes_from_totals(client, run_message_parse):
    register_and_login(client)
    tx = _create_expense(client, run_message_parse, amount="80")

    client.patch(f"/api/transactions/{tx['id']}", json={"type": "transfer"})

    body = client.get("/api/transactions").json()
    assert body["transactions"][0]["type"] == "transfer"
    assert body["totals"] == {"income": "0.00", "expense": "0.00"}


def test_patch_unlinks_pair_when_flipping_away_from_transfer(
    client, run_message_parse, db
):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    _seed_transactions(
        client,
        run_message_parse,
        [
            ("MTB", "cc credit", "transfer", "100", 1_700_000_000_000),
            ("CITY", "debit", "expense", "100", 1_700_000_001_000),
        ],
    )
    txs = db.query(Transaction).order_by(Transaction.id).all()
    transfer_tx, expense_tx = txs[0], txs[1]
    # Manually link as if the matcher had paired them.
    transfer_tx.paired_with_id = expense_tx.id
    expense_tx.paired_with_id = transfer_tx.id
    expense_tx.type = "transfer"
    db.commit()

    client.patch(f"/api/transactions/{expense_tx.id}", json={"type": "expense"})

    db.refresh(transfer_tx)
    db.refresh(expense_tx)
    assert expense_tx.type == "expense"
    assert expense_tx.paired_with_id is None
    # Counterpart's type is untouched — user only spoke for the row they clicked.
    assert transfer_tx.type == "transfer"
    assert transfer_tx.paired_with_id is None


def test_patch_404_for_other_user(client, run_message_parse):
    register_and_login(client, email="a@example.com")
    tx = _create_expense(client, run_message_parse)

    client.post("/api/auth/logout", json={})
    register_and_login(client, email="b@example.com")

    response = client.patch(f"/api/transactions/{tx['id']}", json={"type": "income"})
    assert response.status_code == 404


def test_patch_unauthenticated(client):
    response = client.patch("/api/transactions/1", json={"type": "income"})
    assert response.status_code == 401


def test_get_transactions_exposes_paired_fields(client, run_message_parse, db):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    _seed_transactions(
        client,
        run_message_parse,
        [
            ("MTB", "cc credit", "transfer", "200", 1_700_000_000_000),
            ("CITY", "debit", "transfer", "200", 1_700_000_001_000),
        ],
    )
    txs = db.query(Transaction).order_by(Transaction.id).all()
    txs[0].paired_with_id = txs[1].id
    txs[1].paired_with_id = txs[0].id
    db.commit()

    body = client.get("/api/transactions").json()
    by_id = {t["id"]: t for t in body["transactions"]}
    assert by_id[txs[0].id]["paired_with_id"] == txs[1].id
    assert by_id[txs[0].id]["paired_with_message_id"] == txs[1].message_id
    assert by_id[txs[1].id]["paired_with_id"] == txs[0].id
    assert by_id[txs[1].id]["paired_with_message_id"] == txs[0].message_id


def test_get_transactions_paired_fields_null_when_unpaired(client, run_message_parse):
    register_and_login(client)
    tx = _create_expense(client, run_message_parse)
    assert tx["paired_with_id"] is None
    assert tx["paired_with_message_id"] is None


def test_patch_transfer_to_expense_clears_bill_id_on_both_sides(
    client, run_message_parse, db
):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    _seed_transactions(
        client,
        run_message_parse,
        [
            ("MTB", "cc credit", "transfer", "300", 1_700_000_000_000),
            ("CITY", "debit", "transfer", "300", 1_700_000_001_000),
        ],
    )
    user = db.query(User).first()
    card = make_bank(
        db, user, "EBL Card", account_type="credit", card_digits="1234|5678"
    )
    bill = make_bill(
        db,
        user,
        bank=card,
        normalized_total_due="300.00",
        received_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    txs = db.query(Transaction).order_by(Transaction.id).all()
    transfer_tx, expense_tx = txs[0], txs[1]
    transfer_tx.paired_with_id = expense_tx.id
    expense_tx.paired_with_id = transfer_tx.id
    transfer_tx.bill_id = bill.id
    expense_tx.bill_id = bill.id
    db.commit()

    client.patch(f"/api/transactions/{transfer_tx.id}", json={"type": "expense"})

    db.refresh(transfer_tx)
    db.refresh(expense_tx)
    assert transfer_tx.bill_id is None
    assert expense_tx.bill_id is None
    assert transfer_tx.paired_with_id is None
    assert expense_tx.paired_with_id is None


def test_get_transactions_exposes_bill_id(client, run_message_parse, db):
    register_and_login(client)
    _create_bank(client, "BRAC Bank")
    _seed_transactions(
        client,
        run_message_parse,
        [("MTB", "cc credit", "transfer", "200", 1_700_000_000_000)],
    )
    user = db.query(User).first()
    card = make_bank(
        db, user, "EBL Card", account_type="credit", card_digits="1234|5678"
    )
    bill = make_bill(
        db,
        user,
        bank=card,
        normalized_total_due="200.00",
        received_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    tx = db.query(Transaction).first()
    tx.bill_id = bill.id
    db.commit()

    body = client.get("/api/transactions").json()
    assert body["transactions"][0]["bill_id"] == bill.id
