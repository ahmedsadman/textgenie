from datetime import datetime, timezone

from app.models import Bank, User
from tests.conftest import register_and_login
from tests.factories import make_bank, make_bill, make_transaction


def _user(db) -> User:
    return db.query(User).first()


def _credit_card(db, user, name="EBL Card") -> Bank:
    return make_bank(db, user, name, account_type="credit", card_digits="1234|5678")


def _make_seed_bill(
    db, user, *, bank=None, normalized_total_due="500.00", sender="EBL"
):
    return make_bill(
        db,
        user,
        bank=bank,
        normalized_total_due=normalized_total_due,
        received_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        sender=sender,
    )


def test_list_bills_empty(client):
    register_and_login(client)
    body = client.get("/api/bills").json()
    assert body == {"bills": [], "total": 0, "page": 1, "page_size": 20}


def test_list_bills_returns_user_scope_only(client, db):
    register_and_login(client, email="a@example.com")
    user_a = db.query(User).filter(User.email == "a@example.com").first()
    _make_seed_bill(db, user_a, bank=_credit_card(db, user_a))

    client.post("/api/auth/logout", json={})
    register_and_login(client, email="b@example.com")

    body = client.get("/api/bills").json()
    assert body["bills"] == []
    assert body["total"] == 0


def test_list_bills_filter_by_bank_id(client, db):
    register_and_login(client)
    user = _user(db)
    card_a = _credit_card(db, user, name="EBL Card")
    card_b = make_bank(db, user, "AMEX", account_type="credit", card_digits="9999|1111")
    _make_seed_bill(db, user, bank=card_a)
    _make_seed_bill(db, user, bank=card_b, sender="AMEX")

    body = client.get(f"/api/bills?bank_id={card_a.id}").json()
    assert body["total"] == 1
    assert body["bills"][0]["bank_id"] == card_a.id


def test_get_single_bill_404_for_other_user(client, db):
    register_and_login(client, email="a@example.com")
    user_a = db.query(User).filter(User.email == "a@example.com").first()
    bill = _make_seed_bill(db, user_a, bank=_credit_card(db, user_a))

    client.post("/api/auth/logout", json={})
    register_and_login(client, email="b@example.com")

    response = client.get(f"/api/bills/{bill.id}")
    assert response.status_code == 404


def test_get_single_bill_returns_linked_transaction_ids(client, db):
    register_and_login(client)
    user = _user(db)
    card = _credit_card(db, user)
    bill = _make_seed_bill(db, user, bank=card)
    tx = make_transaction(
        db,
        user,
        amount="500.00",
        type="transfer",
        date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        bank=card,
    )
    tx.bill_id = bill.id
    db.commit()

    body = client.get(f"/api/bills/{bill.id}").json()
    assert body["linked_transaction_ids"] == [tx.id]


def test_patch_unlink_clears_both_paired_sides(client, db):
    register_and_login(client)
    user = _user(db)
    card = _credit_card(db, user)
    debit_bank = make_bank(db, user, "City Bank")
    bill = _make_seed_bill(db, user, bank=card)

    debit_tx = make_transaction(
        db,
        user,
        amount="500.00",
        type="transfer",
        date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        bank=debit_bank,
    )
    transfer_tx = make_transaction(
        db,
        user,
        amount="500.00",
        type="transfer",
        date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        bank=card,
        paired_with_id=debit_tx.id,
    )
    debit_tx.paired_with_id = transfer_tx.id
    transfer_tx.bill_id = bill.id
    debit_tx.bill_id = bill.id
    bill.paid_at = datetime(2026, 7, 5, tzinfo=timezone.utc)
    db.commit()

    response = client.patch(
        f"/api/bills/{bill.id}",
        json={"unlink_transaction_ids": [transfer_tx.id]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["linked_transaction_ids"] == []
    assert body["paid_at"] is None

    db.refresh(transfer_tx)
    db.refresh(debit_tx)
    assert transfer_tx.bill_id is None
    assert debit_tx.bill_id is None


def test_patch_ignores_foreign_transaction_ids(client, db):
    register_and_login(client, email="a@example.com")
    user_a = db.query(User).filter(User.email == "a@example.com").first()
    card = _credit_card(db, user_a)
    bill = _make_seed_bill(db, user_a, bank=card)
    a_tx = make_transaction(
        db,
        user_a,
        amount="500.00",
        type="transfer",
        date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        bank=card,
    )
    a_tx.bill_id = bill.id
    db.commit()

    # Create a separate user with their own transaction.
    client.post("/api/auth/logout", json={})
    register_and_login(client, email="b@example.com")
    user_b = db.query(User).filter(User.email == "b@example.com").first()
    b_card = make_bank(
        db, user_b, "EBL Card", account_type="credit", card_digits="1234|5678"
    )
    b_tx = make_transaction(
        db,
        user_b,
        amount="500.00",
        type="transfer",
        date=datetime(2026, 7, 5, tzinfo=timezone.utc),
        bank=b_card,
    )

    # Back to user A — try to unlink user B's tx by id. Should be a no-op (not raise).
    client.post("/api/auth/logout", json={})
    register_and_login(client, email="a@example.com")
    response = client.patch(
        f"/api/bills/{bill.id}",
        json={"unlink_transaction_ids": [b_tx.id, a_tx.id]},
    )
    assert response.status_code == 200
    db.refresh(a_tx)
    db.refresh(b_tx)
    # user A's link cleared; user B's untouched.
    assert a_tx.bill_id is None
    assert b_tx.bill_id is None  # b_tx was never linked in the first place


def test_list_bills_order_by_received_at_desc(client, db):
    register_and_login(client)
    user = _user(db)
    card = _credit_card(db, user)
    make_bill(
        db,
        user,
        bank=card,
        normalized_total_due="100",
        received_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        sender="EBL",
    )
    make_bill(
        db,
        user,
        bank=card,
        normalized_total_due="200",
        received_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        sender="EBL",
    )

    bills = client.get("/api/bills").json()["bills"]
    assert [b["normalized_total_due"] for b in bills] == ["200.00", "100.00"]


def test_list_bills_unauthenticated(client):
    response = client.get("/api/bills")
    assert response.status_code == 401
