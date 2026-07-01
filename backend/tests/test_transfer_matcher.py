from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.services.transfer_matcher import (
    TRANSFER_AMOUNT_TOLERANCE,
    TRANSFER_MATCH_WINDOW,
    find_and_pair_transfer_counterpart,
)
from tests.factories import make_bank, make_transaction, make_user


@pytest.fixture()
def at():
    """Anchor timestamp factory: returns a base UTC dt plus N minutes."""
    base = datetime(2026, 6, 28, 12, 0, 0, tzinfo=timezone.utc)

    def _at(minutes: float = 0) -> datetime:
        return base + timedelta(minutes=minutes)

    return _at


def test_unique_candidate_in_window_is_paired(db, at):
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    city = make_bank(db, user, "City")

    transfer_tx = make_transaction(
        db, user, amount="2951.00", type="transfer", date=at(0), bank=mtb
    )
    debit_tx = make_transaction(
        db, user, amount="2951.00", type="expense", date=at(-2), bank=city
    )

    winner = find_and_pair_transfer_counterpart(db, transfer_tx)

    assert winner is not None
    assert winner.id == debit_tx.id

    db.refresh(transfer_tx)
    db.refresh(debit_tx)
    assert debit_tx.type == "transfer"
    assert transfer_tx.paired_with_id == debit_tx.id
    assert debit_tx.paired_with_id == transfer_tx.id


def test_no_candidate_is_noop(db, at):
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    transfer_tx = make_transaction(
        db, user, amount="100.00", type="transfer", date=at(0), bank=mtb
    )

    winner = find_and_pair_transfer_counterpart(db, transfer_tx)

    assert winner is None
    db.refresh(transfer_tx)
    assert transfer_tx.paired_with_id is None


def test_ambiguous_tie_is_noop(db, at):
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    city = make_bank(db, user, "City")

    transfer_tx = make_transaction(
        db, user, amount="500.00", type="transfer", date=at(0), bank=mtb
    )
    # Two debits equidistant from the transfer (both 3 minutes away).
    debit_a = make_transaction(
        db, user, amount="500.00", type="expense", date=at(-3), bank=city
    )
    debit_b = make_transaction(
        db, user, amount="500.00", type="expense", date=at(3), bank=city
    )

    winner = find_and_pair_transfer_counterpart(db, transfer_tx)

    assert winner is None
    db.refresh(transfer_tx)
    db.refresh(debit_a)
    db.refresh(debit_b)
    assert transfer_tx.paired_with_id is None
    assert debit_a.type == "expense"
    assert debit_b.type == "expense"


def test_candidate_outside_time_window_ignored(db, at):
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    city = make_bank(db, user, "City")

    transfer_tx = make_transaction(
        db, user, amount="100.00", type="transfer", date=at(0), bank=mtb
    )
    # Just outside the 15-min window.
    over_window = TRANSFER_MATCH_WINDOW + timedelta(seconds=1)
    make_transaction(
        db,
        user,
        amount="100.00",
        type="expense",
        date=at(0) - over_window,
        bank=city,
    )

    assert find_and_pair_transfer_counterpart(db, transfer_tx) is None


def test_candidate_outside_amount_tolerance_ignored(db, at):
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    city = make_bank(db, user, "City")

    transfer_tx = make_transaction(
        db, user, amount="100.00", type="transfer", date=at(0), bank=mtb
    )
    # 1.01 BDT off — outside the 1.00 tolerance.
    make_transaction(
        db,
        user,
        amount="101.01",
        type="expense",
        date=at(-1),
        bank=city,
    )

    assert find_and_pair_transfer_counterpart(db, transfer_tx) is None


def test_candidate_already_paired_ignored(db, at):
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    city = make_bank(db, user, "City")

    transfer_tx = make_transaction(
        db, user, amount="100.00", type="transfer", date=at(0), bank=mtb
    )
    other_transfer = make_transaction(
        db, user, amount="100.00", type="transfer", date=at(-5), bank=mtb
    )
    make_transaction(
        db,
        user,
        amount="100.00",
        type="expense",
        date=at(-1),
        bank=city,
        paired_with_id=other_transfer.id,
    )

    assert find_and_pair_transfer_counterpart(db, transfer_tx) is None


def test_other_user_candidate_ignored(db, at):
    user_a = make_user(db, email="a@example.com")
    user_b = make_user(db, email="b@example.com")
    mtb = make_bank(db, user_a, "MTB")
    city_b = make_bank(db, user_b, "City")

    transfer_tx = make_transaction(
        db, user_a, amount="100.00", type="transfer", date=at(0), bank=mtb
    )
    make_transaction(
        db,
        user_b,
        amount="100.00",
        type="expense",
        date=at(-1),
        bank=city_b,
    )

    assert find_and_pair_transfer_counterpart(db, transfer_tx) is None


def test_amount_tolerance_edge_inclusive(db, at):
    """Exactly +1.00 BDT diff matches; +1.01 doesn't."""
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    city = make_bank(db, user, "City")

    transfer_tx = make_transaction(
        db, user, amount="100.00", type="transfer", date=at(0), bank=mtb
    )
    edge_match = make_transaction(
        db,
        user,
        amount=str(Decimal("100.00") + TRANSFER_AMOUNT_TOLERANCE),
        type="expense",
        date=at(-1),
        bank=city,
    )

    winner = find_and_pair_transfer_counterpart(db, transfer_tx)
    assert winner is not None
    assert winner.id == edge_match.id


def test_already_paired_transfer_skipped(db, at):
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    city = make_bank(db, user, "City")

    debit = make_transaction(
        db, user, amount="100.00", type="expense", date=at(-1), bank=city
    )
    transfer_tx = make_transaction(
        db,
        user,
        amount="100.00",
        type="transfer",
        date=at(0),
        bank=mtb,
        paired_with_id=debit.id,
    )

    assert find_and_pair_transfer_counterpart(db, transfer_tx) is None


def test_non_transfer_input_skipped(db, at):
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    expense_tx = make_transaction(
        db, user, amount="100.00", type="expense", date=at(0), bank=mtb
    )
    assert find_and_pair_transfer_counterpart(db, expense_tx) is None


def test_closest_in_time_wins(db, at):
    user = make_user(db)
    mtb = make_bank(db, user, "MTB")
    city = make_bank(db, user, "City")

    transfer_tx = make_transaction(
        db, user, amount="500.00", type="transfer", date=at(0), bank=mtb
    )
    far = make_transaction(
        db, user, amount="500.00", type="expense", date=at(-10), bank=city
    )
    near = make_transaction(
        db, user, amount="500.00", type="expense", date=at(-2), bank=city
    )

    winner = find_and_pair_transfer_counterpart(db, transfer_tx)

    assert winner is not None
    assert winner.id == near.id
    db.refresh(far)
    assert far.type == "expense"
    assert far.paired_with_id is None
