"""Pair credit-card 'transfer' transactions with the matching bank debit.

When the LLM marks an SMS as a 'transfer' (typically a credit-card bill
payment-received notification from the issuer), the *other half* of that
money movement is a regular debit from another bank that the LLM cannot
detect on its own — there is no payee hint in the debit SMS.

This module finds and pairs those two halves:

  1. After a transfer transaction is created, ``schedule_transfer_match``
     waits ~10 minutes (so the partner SMS has time to land), then runs
  2. ``find_and_pair_transfer_counterpart``, which searches the same
     user's recent unmatched expenses for one of nearly the same amount
     and closest-in-time-to the transfer. On a unique winner both rows
     are flipped to 'transfer' and linked via ``paired_with_id``.

The two functions are intentionally separated so the matching algorithm
itself stays pure and unit-testable without sleeping.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import timedelta
from decimal import Decimal

from sqlalchemy.orm import Session as DBSession

from app.database import SessionLocal
from app.models import Transaction

logger = logging.getLogger(__name__)

TRANSFER_AMOUNT_TOLERANCE = Decimal("1.00")
TRANSFER_MATCH_WINDOW = timedelta(minutes=15)
TRANSFER_MATCH_DELAY_SECONDS = 600  # 10 minutes


def find_and_pair_transfer_counterpart(
    db: DBSession, transfer_tx: Transaction
) -> Transaction | None:
    if transfer_tx.type != "transfer":
        logger.warning(
            "find_and_pair_transfer_counterpart called on non-transfer tx id=%d",
            transfer_tx.id,
        )
        return None
    if transfer_tx.paired_with_id is not None:
        logger.info(
            "Transfer tx id=%d already paired with id=%d; skipping",
            transfer_tx.id,
            transfer_tx.paired_with_id,
        )
        return None

    lower = transfer_tx.amount - TRANSFER_AMOUNT_TOLERANCE
    upper = transfer_tx.amount + TRANSFER_AMOUNT_TOLERANCE
    window_start = transfer_tx.date - TRANSFER_MATCH_WINDOW
    window_end = transfer_tx.date + TRANSFER_MATCH_WINDOW

    candidates: list[Transaction] = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == transfer_tx.user_id,
            Transaction.id != transfer_tx.id,
            Transaction.type == "expense",
            Transaction.paired_with_id.is_(None),
            Transaction.amount >= lower,
            Transaction.amount <= upper,
            Transaction.date >= window_start,
            Transaction.date <= window_end,
        )
        .all()
    )

    if not candidates:
        logger.info(
            "Transfer tx id=%d: no candidate expense found in window",
            transfer_tx.id,
        )
        return None

    def time_delta(tx: Transaction) -> timedelta:
        diff = tx.date - transfer_tx.date
        return abs(diff)

    candidates.sort(key=time_delta)
    closest_delta = time_delta(candidates[0])
    tied = [c for c in candidates if time_delta(c) == closest_delta]

    if len(tied) > 1:
        logger.info(
            "Transfer tx id=%d: ambiguous match (%d candidates tied at |Δt|=%s); "
            "leaving for manual reconciliation",
            transfer_tx.id,
            len(tied),
            closest_delta,
        )
        return None

    winner = tied[0]
    winner.type = "transfer"
    winner.paired_with_id = transfer_tx.id
    transfer_tx.paired_with_id = winner.id
    db.commit()

    logger.info(
        "Transfer tx id=%d paired with expense tx id=%d (|Δt|=%s, |Δamount|=%s)",
        transfer_tx.id,
        winner.id,
        closest_delta,
        abs(transfer_tx.amount - winner.amount),
    )
    return winner


def schedule_transfer_match(transaction_id: int) -> None:
    thread = threading.Thread(
        target=_deferred_match_worker,
        args=(transaction_id,),
        name=f"transfer-match-{transaction_id}",
        daemon=True,
    )
    thread.start()


def _deferred_match_worker(transaction_id: int) -> None:
    time.sleep(TRANSFER_MATCH_DELAY_SECONDS)

    db = SessionLocal()
    try:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if tx is None:
            logger.info(
                "Deferred match: transaction id=%d no longer exists; skipping",
                transaction_id,
            )
            return
        if tx.type != "transfer" or tx.paired_with_id is not None:
            logger.info(
                "Deferred match: transaction id=%d is no longer an unpaired "
                "transfer (type=%s, paired_with_id=%s); skipping",
                transaction_id,
                tx.type,
                tx.paired_with_id,
            )
            return
        find_and_pair_transfer_counterpart(db, tx)
    except Exception:
        logger.error(
            "Deferred transfer match failed for transaction id=%d",
            transaction_id,
            exc_info=True,
        )
    finally:
        db.close()
