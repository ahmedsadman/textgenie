from datetime import datetime, timedelta, timezone

import pytest

from app.services.bill_payment_matcher import (
    BILL_PAYMENT_MATCH_WINDOW,
    find_and_link_bill_for_payment,
    find_and_link_payment_for_bill,
)
from app.services.bills import unlink_transactions
from tests.factories import (
    make_bank,
    make_bill,
    make_transaction,
    make_user,
)


@pytest.fixture()
def at():
    base = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)

    def _at(days: float = 0) -> datetime:
        return base + timedelta(days=days)

    return _at


def _credit_card(db, user, name="EBL Credit Card") -> object:
    return make_bank(db, user, name, account_type="credit", card_digits="1234|5678")


def test_forward_link_bill_created_first(db, at):
    user = make_user(db)
    card = _credit_card(db, user)
    bill = make_bill(
        db,
        user,
        bank=card,
        normalized_total_due="8020.00",
        received_at=at(0),
        sender="EBL",
    )
    transfer_tx = make_transaction(
        db,
        user,
        amount="8020.00",
        type="transfer",
        date=at(10),
        bank=card,
        original_currency="BDT",
    )

    winner = find_and_link_payment_for_bill(db, bill)

    assert winner is not None
    assert winner.id == transfer_tx.id
    db.refresh(bill)
    db.refresh(transfer_tx)
    assert transfer_tx.bill_id == bill.id
    assert bill.paid_at == transfer_tx.date


def test_reverse_link_transfer_arrives_first(db, at):
    user = make_user(db)
    card = _credit_card(db, user)
    transfer_tx = make_transaction(
        db, user, amount="8020.00", type="transfer", date=at(0), bank=card
    )
    bill = make_bill(
        db, user, bank=card, normalized_total_due="8020.00", received_at=at(-5)
    )

    winner = find_and_link_bill_for_payment(db, transfer_tx)

    assert winner is not None
    assert winner.id == bill.id
    db.refresh(transfer_tx)
    db.refresh(bill)
    assert transfer_tx.bill_id == bill.id
    assert bill.paid_at == transfer_tx.date


def test_linking_populates_both_paired_sides(db, at):
    user = make_user(db)
    card = _credit_card(db, user)
    debit_bank = make_bank(db, user, "City Bank")

    debit_tx = make_transaction(
        db, user, amount="8020.00", type="transfer", date=at(10), bank=debit_bank
    )
    transfer_tx = make_transaction(
        db,
        user,
        amount="8020.00",
        type="transfer",
        date=at(10),
        bank=card,
        paired_with_id=debit_tx.id,
    )
    debit_tx.paired_with_id = transfer_tx.id
    db.commit()

    bill = make_bill(
        db, user, bank=card, normalized_total_due="8020.00", received_at=at(0)
    )
    winner = find_and_link_payment_for_bill(db, bill)

    assert winner is not None
    db.refresh(transfer_tx)
    db.refresh(debit_tx)
    db.refresh(bill)
    assert transfer_tx.bill_id == bill.id
    assert debit_tx.bill_id == bill.id
    assert bill.paid_at == transfer_tx.date


def test_amount_mismatch_skipped(db, at):
    user = make_user(db)
    card = _credit_card(db, user)
    bill = make_bill(
        db, user, bank=card, normalized_total_due="8020.00", received_at=at(0)
    )
    make_transaction(db, user, amount="8019.99", type="transfer", date=at(5), bank=card)

    assert find_and_link_payment_for_bill(db, bill) is None
    db.refresh(bill)
    assert bill.paid_at is None


def test_outside_window_skipped(db, at):
    user = make_user(db)
    card = _credit_card(db, user)
    bill = make_bill(
        db, user, bank=card, normalized_total_due="500.00", received_at=at(0)
    )
    out = BILL_PAYMENT_MATCH_WINDOW + timedelta(days=1)
    make_transaction(
        db,
        user,
        amount="500.00",
        type="transfer",
        date=at(0) + out,
        bank=card,
    )
    assert find_and_link_payment_for_bill(db, bill) is None


def test_different_card_skipped(db, at):
    user = make_user(db)
    card_a = _credit_card(db, user, name="EBL Credit Card")
    card_b = make_bank(db, user, "AMEX", account_type="credit", card_digits="9999|1111")
    bill = make_bill(
        db, user, bank=card_a, normalized_total_due="500.00", received_at=at(0)
    )
    make_transaction(
        db, user, amount="500.00", type="transfer", date=at(5), bank=card_b
    )
    assert find_and_link_payment_for_bill(db, bill) is None


def test_different_user_skipped(db, at):
    user_a = make_user(db, email="a@example.com")
    user_b = make_user(db, email="b@example.com")
    card_a = _credit_card(db, user_a)
    card_b = make_bank(
        db,
        user_b,
        "EBL Credit Card",
        account_type="credit",
        card_digits="1234|5678",
    )
    bill = make_bill(
        db, user_a, bank=card_a, normalized_total_due="500.00", received_at=at(0)
    )
    make_transaction(
        db, user_b, amount="500.00", type="transfer", date=at(5), bank=card_b
    )
    assert find_and_link_payment_for_bill(db, bill) is None


def test_already_linked_transfer_skipped(db, at):
    user = make_user(db)
    card = _credit_card(db, user)
    other_bill = make_bill(
        db, user, bank=card, normalized_total_due="500.00", received_at=at(-30)
    )
    transfer_tx = make_transaction(
        db, user, amount="500.00", type="transfer", date=at(5), bank=card
    )
    transfer_tx.bill_id = other_bill.id
    db.commit()

    bill = make_bill(
        db, user, bank=card, normalized_total_due="500.00", received_at=at(0)
    )
    assert find_and_link_payment_for_bill(db, bill) is None


def test_bill_without_bank_returns_none(db, at):
    user = make_user(db)
    bill = make_bill(db, user, normalized_total_due="500.00", received_at=at(0))
    assert find_and_link_payment_for_bill(db, bill) is None


def test_unlink_clears_both_sides_and_paid_at(db, at):
    user = make_user(db)
    card = _credit_card(db, user)
    debit_bank = make_bank(db, user, "City Bank")

    debit_tx = make_transaction(
        db, user, amount="500.00", type="transfer", date=at(5), bank=debit_bank
    )
    transfer_tx = make_transaction(
        db,
        user,
        amount="500.00",
        type="transfer",
        date=at(5),
        bank=card,
        paired_with_id=debit_tx.id,
    )
    debit_tx.paired_with_id = transfer_tx.id
    db.commit()

    bill = make_bill(
        db, user, bank=card, normalized_total_due="500.00", received_at=at(0)
    )
    find_and_link_payment_for_bill(db, bill)

    unlink_transactions(db, user, bill.id, [transfer_tx.id])

    db.refresh(bill)
    db.refresh(transfer_tx)
    db.refresh(debit_tx)
    assert transfer_tx.bill_id is None
    assert debit_tx.bill_id is None
    assert bill.paid_at is None


def test_currency_mismatch_skipped(db, at):
    user = make_user(db)
    card = _credit_card(db, user)
    bill = make_bill(
        db,
        user,
        bank=card,
        normalized_total_due="120.50",
        received_at=at(0),
        normalized_currency="USD",
    )
    # Transfer transaction defaults to normalized_currency = "BDT" via schema default.
    tx = make_transaction(
        db, user, amount="120.50", type="transfer", date=at(5), bank=card
    )
    tx.normalized_currency = "BDT"
    db.commit()

    assert find_and_link_payment_for_bill(db, bill) is None
