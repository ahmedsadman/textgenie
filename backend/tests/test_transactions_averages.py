from datetime import datetime, timezone

from app.models import User
from tests.conftest import register_and_login
from tests.factories import make_transaction


def _averages(client):
    return client.get("/api/transactions/averages")


def _current_user(db):
    return db.query(User).first()


def _dt(year, month, day=1):
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_averages_no_transactions_returns_zeros(client, db):
    register_and_login(client)
    body = _averages(client).json()
    assert body == {"avg_spend": "0.00", "avg_saving": "0.00"}


def test_averages_single_month(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="100.00", type="income", date=_dt(2025, 1))
    make_transaction(db, user, amount="30.00", type="expense", date=_dt(2025, 1))

    # span == 1 month
    body = _averages(client).json()
    assert body == {"avg_spend": "30.00", "avg_saving": "70.00"}


def test_averages_divides_by_full_span_including_gaps(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="30.00", type="expense", date=_dt(2025, 1))
    make_transaction(db, user, amount="60.00", type="expense", date=_dt(2025, 3))

    # Jan..Mar inclusive == 3 months, empty Feb counts. Net saving is negative.
    body = _averages(client).json()
    assert body == {"avg_spend": "30.00", "avg_saving": "-30.00"}


def test_averages_net_saving_across_months(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="900.00", type="income", date=_dt(2025, 1))
    make_transaction(db, user, amount="300.00", type="expense", date=_dt(2025, 2))

    # span == 2 months; saving == (900 - 300) / 2
    body = _averages(client).json()
    assert body == {"avg_spend": "150.00", "avg_saving": "300.00"}


def test_averages_excludes_transfers_from_sums_and_span(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="100.00", type="income", date=_dt(2025, 1))
    make_transaction(db, user, amount="40.00", type="expense", date=_dt(2025, 1))
    make_transaction(db, user, amount="5000.00", type="transfer", date=_dt(2025, 1))
    # A later transfer must not stretch the span beyond the income/expense rows.
    make_transaction(db, user, amount="999.00", type="transfer", date=_dt(2025, 5))

    body = _averages(client).json()
    assert body == {"avg_spend": "40.00", "avg_saving": "60.00"}


def test_averages_isolated_by_user(client, db):
    register_and_login(client, email="user1@example.com")
    user1 = db.query(User).filter(User.email == "user1@example.com").first()
    make_transaction(db, user1, amount="100.00", type="expense", date=_dt(2025, 1))

    register_and_login(client, email="user2@example.com")
    body = _averages(client).json()
    assert body == {"avg_spend": "0.00", "avg_saving": "0.00"}


def test_averages_unauthenticated(client):
    response = _averages(client)
    assert response.status_code == 401
