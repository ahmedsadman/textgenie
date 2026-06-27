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

