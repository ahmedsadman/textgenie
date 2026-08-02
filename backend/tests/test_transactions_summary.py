from datetime import datetime, timezone

from app.models import User
from tests.conftest import register_and_login
from tests.factories import make_transaction


def _summary(client, **params):
    return client.get("/api/transactions/summary", params=params or None)


def _current_user(db):
    return db.query(User).first()


def _dt(year, month, day=1):
    return datetime(year, month, day, tzinfo=timezone.utc)


def test_summary_multi_month_aggregation(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="100.00", type="income", date=_dt(2025, 1))
    make_transaction(db, user, amount="30.00", type="expense", date=_dt(2025, 2))
    make_transaction(db, user, amount="60.00", type="income", date=_dt(2025, 3))

    body = _summary(client).json()
    series = body["series"]
    assert [b["month_start"] for b in series] == [
        "2025-01-01",
        "2025-02-01",
        "2025-03-01",
    ]
    assert series[0] == {
        "month_start": "2025-01-01",
        "income": "100.00",
        "expense": "0.00",
    }
    assert series[1] == {
        "month_start": "2025-02-01",
        "income": "0.00",
        "expense": "30.00",
    }
    assert series[2] == {
        "month_start": "2025-03-01",
        "income": "60.00",
        "expense": "0.00",
    }


def test_summary_same_month_sums_together(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="100.00", type="income", date=_dt(2025, 1, 5))
    make_transaction(db, user, amount="50.00", type="income", date=_dt(2025, 1, 20))
    make_transaction(db, user, amount="30.00", type="expense", date=_dt(2025, 1, 25))

    series = _summary(client).json()["series"]
    assert len(series) == 1
    assert series[0] == {
        "month_start": "2025-01-01",
        "income": "150.00",
        "expense": "30.00",
    }


def test_summary_excludes_transfers(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="100.00", type="income", date=_dt(2025, 1))
    make_transaction(db, user, amount="200.00", type="transfer", date=_dt(2025, 1))

    series = _summary(client).json()["series"]
    assert len(series) == 1
    assert series[0] == {
        "month_start": "2025-01-01",
        "income": "100.00",
        "expense": "0.00",
    }


def test_summary_gap_fills_empty_months(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="100.00", type="income", date=_dt(2025, 1))
    make_transaction(db, user, amount="40.00", type="expense", date=_dt(2025, 4))

    series = _summary(client).json()["series"]
    # contiguous Jan..Apr
    assert [b["month_start"] for b in series] == [
        "2025-01-01",
        "2025-02-01",
        "2025-03-01",
        "2025-04-01",
    ]
    assert series[1] == {
        "month_start": "2025-02-01",
        "income": "0.00",
        "expense": "0.00",
    }
    assert series[2] == {
        "month_start": "2025-03-01",
        "income": "0.00",
        "expense": "0.00",
    }
    assert series[-1]["expense"] == "40.00"


def test_summary_all_time_bounds_from_min_max(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="10.00", type="income", date=_dt(2024, 11))
    make_transaction(db, user, amount="20.00", type="expense", date=_dt(2025, 2))

    series = _summary(client).json()["series"]
    assert series[0]["month_start"] == "2024-11-01"
    assert series[-1]["month_start"] == "2025-02-01"
    # Nov 2024 .. Feb 2025 inclusive == 4 months
    assert len(series) == 4


def test_summary_no_transactions_returns_empty(client, db):
    register_and_login(client)
    body = _summary(client).json()
    assert body == {"series": []}


def test_summary_date_range_filter(client, db):
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="10.00", type="expense", date=_dt(2024, 9))
    make_transaction(db, user, amount="20.00", type="expense", date=_dt(2025, 1))
    make_transaction(db, user, amount="30.00", type="income", date=_dt(2025, 6))

    body = _summary(
        client,
        from_date="2024-12-01T00:00:00Z",
        to_date="2025-03-31T00:00:00Z",
    ).json()
    series = body["series"]
    # bounds honor request window: Dec 2024 .. Mar 2025
    assert [b["month_start"] for b in series] == [
        "2024-12-01",
        "2025-01-01",
        "2025-02-01",
        "2025-03-01",
    ]
    assert series[0] == {
        "month_start": "2024-12-01",
        "income": "0.00",
        "expense": "0.00",
    }
    assert series[1]["expense"] == "20.00"


def test_summary_bounded_window_with_no_matches_is_empty(client, db):
    """An explicit window matching no income/expense rows returns [], so the
    UI shows an empty state rather than a flat zero line."""
    register_and_login(client)
    user = _current_user(db)
    make_transaction(db, user, amount="10.00", type="expense", date=_dt(2025, 6))

    body = _summary(
        client,
        from_date="2024-01-01T00:00:00Z",
        to_date="2024-12-31T00:00:00Z",
    ).json()
    assert body == {"series": []}


def test_summary_isolated_by_user(client, db):
    register_and_login(client, email="user1@example.com")
    user1 = db.query(User).filter(User.email == "user1@example.com").first()
    make_transaction(db, user1, amount="100.00", type="income", date=_dt(2025, 1))

    register_and_login(client, email="user2@example.com")
    body = _summary(client).json()
    assert body == {"series": []}


def test_summary_unauthenticated(client):
    response = _summary(client)
    assert response.status_code == 401
