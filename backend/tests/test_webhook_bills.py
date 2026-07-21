from decimal import Decimal

from app.models import Bill, Transaction
from app.services.llm.base import BillMetadataResult
from tests.conftest import create_message, get_webhook_token, register_and_login
from tests.factories import make_mock_provider


def _bill_provider(**kwargs):
    return make_mock_provider(
        category="bill", bill_metadata=BillMetadataResult(**kwargs)
    )


def _create_credit_card(client, name="EBL Credit Card", card="1234|5678"):
    return client.post(
        "/api/banks",
        json={"name": name, "account_type": "credit", "card_digits": card},
    )


def _post_and_parse_bill(
    client,
    run_message_parse,
    provider,
    *,
    sender="EBL",
    content="Monthly bill 4238****3241 JUL2026 Total Due BDT 8020",
    timestamp=None,
):
    token = get_webhook_token(client)
    create_message(client, token, sender=sender, content=content, timestamp=timestamp)
    message_id = client.get("/api/messages").json()["messages"][0]["id"]
    run_message_parse(message_id, provider)
    return message_id


def test_bill_message_creates_bill_row_no_transaction(client, run_message_parse, db):
    register_and_login(client)
    bank_id = _create_credit_card(client).json()["id"]

    _post_and_parse_bill(
        client,
        run_message_parse,
        _bill_provider(
            bank="EBL Credit Card",
            normalized_total_due=Decimal("8020.00"),
            original_amount=Decimal("8020.00"),
            original_currency="BDT",
            statement_month=7,
            statement_year=2026,
        ),
    )

    assert db.query(Transaction).count() == 0
    bills = db.query(Bill).all()
    assert len(bills) == 1
    bill = bills[0]
    assert bill.bank_id == bank_id
    assert bill.normalized_total_due == Decimal("8020.00")
    assert bill.statement_period.year == 2026
    assert bill.statement_period.month == 7
    assert bill.original_currency == "BDT"


def test_bill_missing_normalized_total_due_skipped(client, run_message_parse, db):
    register_and_login(client)
    _create_credit_card(client)
    _post_and_parse_bill(
        client, run_message_parse, _bill_provider(normalized_total_due=None)
    )
    assert db.query(Bill).count() == 0


def test_bill_null_statement_period_still_creates_row(client, run_message_parse, db):
    register_and_login(client)
    _create_credit_card(client)
    _post_and_parse_bill(
        client,
        run_message_parse,
        _bill_provider(
            normalized_total_due=Decimal("500.00"),
            original_amount=Decimal("500.00"),
            original_currency="BDT",
            statement_month=None,
            statement_year=None,
        ),
    )
    bill = db.query(Bill).first()
    assert bill is not None
    assert bill.statement_period is None


def test_bill_foreign_currency_stores_original_and_normalized(
    client, run_message_parse, db
):
    register_and_login(client)
    _create_credit_card(client)
    _post_and_parse_bill(
        client,
        run_message_parse,
        _bill_provider(
            normalized_total_due=Decimal("13255.00"),  # normalized to BDT
            original_amount=Decimal("120.50"),
            original_currency="USD",
            statement_month=7,
            statement_year=2026,
        ),
    )
    bill = db.query(Bill).first()
    assert bill.normalized_total_due == Decimal("13255.00")
    assert bill.original_amount == Decimal("120.50")
    assert bill.original_currency == "USD"
    assert bill.normalized_currency == "BDT"


def test_bill_bank_id_null_when_llm_returns_no_bank(client, run_message_parse, db):
    register_and_login(client)
    _create_credit_card(client, name="AMEX", card="9999|1111")

    _post_and_parse_bill(
        client,
        run_message_parse,
        _bill_provider(
            bank=None,
            normalized_total_due=Decimal("500.00"),
            original_amount=Decimal("500.00"),
            original_currency="BDT",
            statement_month=7,
            statement_year=2026,
        ),
        sender="EBL",
    )
    bill = db.query(Bill).first()
    assert bill is not None
    assert bill.bank_id is None


def test_duplicate_period_bill_skipped(client, run_message_parse, db):
    register_and_login(client)
    _create_credit_card(client)
    provider = _bill_provider(
        bank="EBL Credit Card",
        normalized_total_due=Decimal("8020.00"),
        original_amount=Decimal("8020.00"),
        original_currency="BDT",
        statement_month=7,
        statement_year=2026,
    )
    _post_and_parse_bill(client, run_message_parse, provider, sender="EBL")
    _post_and_parse_bill(
        client,
        run_message_parse,
        provider,
        sender="EBL",
        content="EBL reminder: bill JUL2026 pending",
    )

    assert db.query(Bill).count() == 1


def test_bill_message_reparse_idempotent(client, run_message_parse, db):
    register_and_login(client)
    _create_credit_card(client)
    provider = _bill_provider(
        normalized_total_due=Decimal("500.00"),
        original_amount=Decimal("500.00"),
        original_currency="BDT",
        statement_month=7,
        statement_year=2026,
    )
    token = get_webhook_token(client)
    create_message(client, token, sender="EBL", content="Monthly bill JUL2026")
    message_id = client.get("/api/messages").json()["messages"][0]["id"]

    run_message_parse(message_id, provider)
    run_message_parse(message_id, provider)

    assert db.query(Bill).count() == 1


def test_bill_category_skipped_for_blacklisted_sender(client, run_message_parse, db):
    register_and_login(client)
    _create_credit_card(client)
    client.put("/api/settings/metadata-blacklist", json={"senders": ["EBL"]})
    _post_and_parse_bill(
        client,
        run_message_parse,
        _bill_provider(
            normalized_total_due=Decimal("500.00"),
            original_amount=Decimal("500.00"),
            original_currency="BDT",
            statement_month=7,
            statement_year=2026,
        ),
        sender="EBL",
    )
    assert db.query(Bill).count() == 0
