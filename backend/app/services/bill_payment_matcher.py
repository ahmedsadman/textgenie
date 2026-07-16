"""Link credit-card Bill rows to their paying Transaction(s).

A bill message ("EBL Monthly bill 4238****3241 JUL2026; Total Due 8020")
describes what the user owes; separately, two Transaction rows record the
actual movement of money (a bank debit + a card-side credit, already paired
via ``paired_with_id`` by ``transfer_matcher``). This module links a bill
to the transfer transaction whose card + amount + timing match, and
symmetrically populates ``bill_id`` on the paired counterpart so both
sides of the payment carry the same bill reference (1 bill : up to 2 tx).

Two entry points, one algorithm:

* ``find_and_link_payment_for_bill`` — called after a new Bill row is
  created; searches recent unpaired transfer transactions on the same card.
* ``find_and_link_bill_for_payment`` — called by ``transfer_matcher`` after
  it pairs a credit-card transfer; searches recent unpaired Bills on
  that card.

Constants are exact-amount and a 45-day window to cover a full statement
cycle plus late-payer slack. Ties are resolved by closest-in-time-after
the bill message; genuine ties are logged and skipped.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.orm import Session as DBSession

from app.constants import CREDIT, TRANSFER
from app.database import SessionLocal
from app.models import Bill, Message, Transaction

logger = logging.getLogger(__name__)

BILL_PAYMENT_AMOUNT_TOLERANCE = Decimal("0.00")
BILL_PAYMENT_MATCH_WINDOW = timedelta(days=45)
BILL_PAYMENT_MATCH_DELAY_SECONDS = 600  # mirrors transfer_matcher


def find_and_link_payment_for_bill(db: DBSession, bill: Bill) -> Transaction | None:
    """Look for an unlinked transfer on this card that matches the bill."""
    if bill.bank_id is None:
        logger.info("Bill id=%d has no bank_id; cannot match a payment", bill.id)
        return None

    bill_received_at = bill.message.received_at
    lower = bill.normalized_total_due - BILL_PAYMENT_AMOUNT_TOLERANCE
    upper = bill.normalized_total_due + BILL_PAYMENT_AMOUNT_TOLERANCE
    window_start = bill_received_at - BILL_PAYMENT_MATCH_WINDOW
    window_end = bill_received_at + BILL_PAYMENT_MATCH_WINDOW

    candidates: list[Transaction] = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == bill.user_id,
            Transaction.bank_id == bill.bank_id,
            Transaction.type == TRANSFER,
            Transaction.bill_id.is_(None),
            Transaction.normalized_currency == bill.normalized_currency,
            Transaction.normalized_amount >= lower,
            Transaction.normalized_amount <= upper,
            Transaction.date >= window_start,
            Transaction.date <= window_end,
        )
        .all()
    )

    winner = _pick_winner(candidates, bill_received_at)
    if winner is None:
        logger.info("Bill id=%d: no unique payment match", bill.id)
        return None

    _link(db, bill, winner)
    return winner


def find_and_link_bill_for_payment(
    db: DBSession, transfer_tx: Transaction
) -> Bill | None:
    """Look for an unlinked Bill on this credit card that matches the transfer."""
    if transfer_tx.type != TRANSFER:
        return None
    if transfer_tx.bill_id is not None:
        return None
    if transfer_tx.bank_id is None or transfer_tx.bank is None:
        return None
    if transfer_tx.bank.account_type != CREDIT:
        return None

    lower = transfer_tx.normalized_amount - BILL_PAYMENT_AMOUNT_TOLERANCE
    upper = transfer_tx.normalized_amount + BILL_PAYMENT_AMOUNT_TOLERANCE
    window_start = transfer_tx.date - BILL_PAYMENT_MATCH_WINDOW
    window_end = transfer_tx.date + BILL_PAYMENT_MATCH_WINDOW

    candidates: list[tuple[Bill, Message]] = (
        db.query(Bill, Message)
        .join(Message, Message.id == Bill.message_id)
        .filter(
            Bill.user_id == transfer_tx.user_id,
            Bill.bank_id == transfer_tx.bank_id,
            Bill.normalized_currency == transfer_tx.normalized_currency,
            Bill.normalized_total_due >= lower,
            Bill.normalized_total_due <= upper,
            Message.received_at >= window_start,
            Message.received_at <= window_end,
            ~Bill.linked_transactions.any(),
        )
        .all()
    )

    if not candidates:
        logger.info(
            "Transfer tx id=%d: no matching bill on card id=%d",
            transfer_tx.id,
            transfer_tx.bank_id,
        )
        return None

    # Prefer bills whose message arrived BEFORE the payment (typical flow),
    # closest first; fall back to closest overall.
    def sort_key(item: tuple[Bill, Message]):
        _, msg = item
        diff = transfer_tx.date - msg.received_at
        before = diff.total_seconds() >= 0
        return (not before, abs(diff))

    candidates.sort(key=sort_key)
    top_key = sort_key(candidates[0])
    tied = [c for c in candidates if sort_key(c) == top_key]
    if len(tied) > 1:
        logger.info(
            "Transfer tx id=%d: ambiguous bill match (%d tied); skipping",
            transfer_tx.id,
            len(tied),
        )
        return None

    winner_bill = tied[0][0]
    _link(db, winner_bill, transfer_tx)
    return winner_bill


def _pick_winner(candidates: list[Transaction], bill_received_at) -> Transaction | None:
    if not candidates:
        return None

    def sort_key(tx: Transaction):
        diff = tx.date - bill_received_at
        before = diff.total_seconds() < 0
        return (before, abs(diff))

    candidates.sort(key=sort_key)
    top_key = sort_key(candidates[0])
    tied = [c for c in candidates if sort_key(c) == top_key]
    if len(tied) > 1:
        logger.info(
            "Ambiguous bill payment match (%d candidates tied); skipping",
            len(tied),
        )
        return None
    return tied[0]


def _link(db: DBSession, bill: Bill, transfer_tx: Transaction) -> None:
    transfer_tx.bill_id = bill.id
    if transfer_tx.paired_with_id is not None:
        counterpart = (
            db.query(Transaction)
            .filter(Transaction.id == transfer_tx.paired_with_id)
            .first()
        )
        if counterpart is not None:
            counterpart.bill_id = bill.id
    bill.paid_at = transfer_tx.date
    db.commit()
    logger.info(
        "Bill id=%d linked to transfer tx id=%d (paid_at=%s)",
        bill.id,
        transfer_tx.id,
        transfer_tx.date,
    )


def schedule_bill_payment_match(bill_id: int) -> None:
    thread = threading.Thread(
        target=_deferred_bill_match_worker,
        args=(bill_id,),
        name=f"bill-payment-match-{bill_id}",
        daemon=True,
    )
    thread.start()


def _deferred_bill_match_worker(bill_id: int) -> None:
    time.sleep(BILL_PAYMENT_MATCH_DELAY_SECONDS)

    db = SessionLocal()
    try:
        bill = db.query(Bill).filter(Bill.id == bill_id).first()
        if bill is None:
            logger.info(
                "Deferred bill match: bill id=%d no longer exists; skipping",
                bill_id,
            )
            return
        if bill.bank_id is None:
            logger.info(
                "Deferred bill match: bill id=%d has no bank; skipping",
                bill_id,
            )
            return
        find_and_link_payment_for_bill(db, bill)
    except Exception:
        logger.error(
            "Deferred bill match failed for bill id=%d",
            bill_id,
            exc_info=True,
        )
    finally:
        db.close()
