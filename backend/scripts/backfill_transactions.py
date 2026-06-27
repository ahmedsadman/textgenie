"""Backfill Transaction records from previously-categorized 'transaction' messages.

Walks transaction-category messages newest-first, runs metadata extraction on any
that don't yet have a Transaction record, and inserts records using the same
helpers the live webhook uses (so behavior matches).

Run inside the backend container:

    docker compose -f docker-compose.yml -f docker-compose.dev.yml \\
        exec backend uv run python scripts/backfill_transactions.py --count 50

Idempotency: re-runs skip messages that already have a Transaction (unique on
message_id). Bank balances only advance forward in time, so re-processing older
messages cannot roll back a newer balance.
"""

import argparse
import logging
import sys

from sqlalchemy import exists
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

from app.database import SessionLocal
from app.models import Bank, Category, Message, Transaction, User
from app.services import metadata_blacklist
from app.services.categories import DefaultCategory
from app.services.webhook import (
    _extract_metadata,
    _match_bank,
    _record_transaction,
    _update_bank_balance,
)

logger = logging.getLogger("backfill_transactions")


# Outcomes per message — drives the counter and the run summary.
CREATED = "created"
NO_EXTRACTION = "no_extraction"
SKIPPED_NO_BANKS = "skipped_no_banks"
SKIPPED_BLACKLIST = "skipped_blacklist"
ERROR = "error"

# Outcomes that count toward the user's --count target: the LLM was called and
# we either inserted a row or learned the message has no extractable data.
COUNTABLE = {CREATED, NO_EXTRACTION}


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--count",
        type=int,
        default=10,
        help="Number of messages to fully process before stopping (default: 10). "
        "Messages skipped because they already have a Transaction, the sender is "
        "blacklisted, or the user has no banks DO NOT count.",
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="DB fetch + commit batch size (default: 25). One commit per batch "
        "bounds rework-on-crash; LLM calls within a batch are sequential.",
    )
    p.add_argument(
        "--user-id",
        type=int,
        default=None,
        help="Restrict to a single user_id. Defaults to all users.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Run LLM extraction and log results, but do not write to the DB.",
    )
    return p.parse_args()


def _fetch_candidates(
    db: DBSession,
    *,
    user_id: int | None,
    excluded_ids: set[int],
    limit: int,
) -> list[Message]:
    """Transaction-category messages with no Transaction row yet, newest-first."""
    query = (
        db.query(Message)
        .join(Category, Message.category_id == Category.id)
        .filter(Category.name == DefaultCategory.TRANSACTION.value)
        .filter(~exists().where(Transaction.message_id == Message.id))
        .order_by(Message.received_at.desc(), Message.id.desc())
    )
    if user_id is not None:
        query = query.filter(Message.user_id == user_id)
    if excluded_ids:
        query = query.filter(Message.id.notin_(excluded_ids))
    return query.limit(limit).all()


def _process_message(db: DBSession, msg: Message, user: User, *, dry_run: bool) -> str:
    if metadata_blacklist.contains(msg.sender, user.metadata_blacklist):
        return SKIPPED_BLACKLIST

    banks = db.query(Bank).filter(Bank.user_id == user.id).all()
    if not banks:
        return SKIPPED_NO_BANKS

    metadata = _extract_metadata(msg.content, msg.sender, [b.name for b in banks])
    bank = _match_bank(banks, metadata.bank)

    if dry_run:
        logger.info(
            "[dry-run] msg=%d sender=%s -> bank=%s amount=%s type=%s",
            msg.id,
            msg.sender,
            metadata.bank,
            metadata.amount,
            metadata.transaction_type,
        )
        return (
            CREATED
            if (metadata.amount and metadata.transaction_type)
            else NO_EXTRACTION
        )

    _update_bank_balance(bank, metadata, msg)
    _record_transaction(db, user, bank, metadata, msg)

    return CREATED if (metadata.amount and metadata.transaction_type) else NO_EXTRACTION


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.dry_run:
        logger.info("DRY RUN — no DB writes will be performed.")

    counts = {
        CREATED: 0,
        NO_EXTRACTION: 0,
        SKIPPED_NO_BANKS: 0,
        SKIPPED_BLACKLIST: 0,
        ERROR: 0,
    }
    countable_done = 0
    scanned_ids: set[int] = set()

    db = SessionLocal()
    try:
        while countable_done < args.count:
            remaining = args.count - countable_done
            batch = _fetch_candidates(
                db,
                user_id=args.user_id,
                excluded_ids=scanned_ids,
                # Fetch one batch at a time, but never more than we still need
                # (assuming worst case where every message counts).
                limit=min(
                    args.batch_size, remaining + len(scanned_ids) + args.batch_size
                ),
            )
            if not batch:
                logger.info("No more candidate messages.")
                break

            for msg in batch:
                if countable_done >= args.count:
                    break

                user = db.query(User).filter(User.id == msg.user_id).first()
                if user is None:
                    logger.warning("Message %d has no user; skipping", msg.id)
                    counts[ERROR] += 1
                    scanned_ids.add(msg.id)
                    continue

                try:
                    outcome = _process_message(db, msg, user, dry_run=args.dry_run)
                except Exception:
                    logger.exception("Failed to process message %d", msg.id)
                    counts[ERROR] += 1
                    scanned_ids.add(msg.id)
                    db.rollback()
                    continue

                counts[outcome] += 1
                scanned_ids.add(msg.id)
                if outcome in COUNTABLE:
                    countable_done += 1

            if not args.dry_run:
                try:
                    db.commit()
                except IntegrityError:
                    # A concurrent backfill (or webhook) inserted the same
                    # transaction first. Roll back and continue — the row exists.
                    logger.warning(
                        "Commit hit IntegrityError (concurrent insert?); "
                        "rolling back batch"
                    )
                    db.rollback()

            logger.info(
                "Batch done. countable=%d/%d  created=%d  no_extraction=%d  "
                "skipped_no_banks=%d  skipped_blacklist=%d  errors=%d",
                countable_done,
                args.count,
                counts[CREATED],
                counts[NO_EXTRACTION],
                counts[SKIPPED_NO_BANKS],
                counts[SKIPPED_BLACKLIST],
                counts[ERROR],
            )

        logger.info(
            "Finished. created=%d  no_extraction=%d  skipped_no_banks=%d  "
            "skipped_blacklist=%d  errors=%d  scanned=%d",
            counts[CREATED],
            counts[NO_EXTRACTION],
            counts[SKIPPED_NO_BANKS],
            counts[SKIPPED_BLACKLIST],
            counts[ERROR],
            len(scanned_ids),
        )
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
