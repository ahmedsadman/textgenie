from datetime import date

from app.models import LLMUsage, User
from app.services.llm.usage import LLMUsageEvent
from app.services.llm.usage.prices import compute_cost_micros
from app.services.llm.usage.recorder import record
from tests.conftest import register_and_login


def _make_admin(db, email="admin@example.com"):
    user = User(
        name="Admin",
        email=email,
        password_hash="x",
        webhook_token=f"tok-{email}",
        is_admin=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _promote_current_user(db, email):
    user = db.query(User).filter(User.email == email).first()
    user.is_admin = True
    db.commit()
    return user


def test_compute_cost_known_model():
    cost = compute_cost_micros("gemini", "gemini-2.5-flash-lite", 1_000_000, 0, 500_000)
    # input: 1M * 100_000 / 1M = 100_000; output: 500_000 * 400_000 / 1M = 200_000
    assert cost == 300_000


def test_compute_cost_with_cached_input():
    cost = compute_cost_micros("gemini", "gemini-2.5-flash-lite", 1_000_000, 400_000, 0)
    # uncached: 600_000 * 100_000 / 1M = 60_000; cached: 400_000 * 10_000 / 1M = 4_000
    assert cost == 64_000


def test_compute_cost_unknown_model():
    assert compute_cost_micros("openai", "gpt-99", 1_000, 0, 100) == 0


def test_record_creates_row_on_first_call(db):
    user = _make_admin(db)
    event = LLMUsageEvent(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        input_tokens=100,
        cached_input_tokens=0,
        output_tokens=50,
    )
    record(db, user.id, event)

    row = db.query(LLMUsage).filter(LLMUsage.user_id == user.id).one()
    assert row.input_tokens == 100
    assert row.output_tokens == 50
    assert row.request_count == 1
    assert row.cost_micros == compute_cost_micros(
        "gemini", "gemini-2.5-flash-lite", 100, 0, 50
    )


def test_record_aggregates_on_same_day(db):
    user = _make_admin(db)
    event = LLMUsageEvent(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        input_tokens=100,
        cached_input_tokens=0,
        output_tokens=50,
    )
    record(db, user.id, event)
    record(db, user.id, event)
    record(db, user.id, event)

    row = db.query(LLMUsage).filter(LLMUsage.user_id == user.id).one()
    assert row.input_tokens == 300
    assert row.output_tokens == 150
    assert row.request_count == 3


def test_admin_endpoints_require_admin(client):
    register_and_login(client)  # regular user
    for path in [
        "/api/admin/users",
        "/api/admin/usage/summary",
    ]:
        response = client.get(path)
        assert response.status_code == 403


def test_admin_endpoints_require_auth(client):
    response = client.get("/api/admin/users")
    assert response.status_code == 401


def test_list_users_returns_all(client, db):
    register_and_login(client)
    _promote_current_user(db, "test@example.com")
    # add second user
    other = User(
        name="Other",
        email="other@example.com",
        password_hash="x",
        webhook_token="tok-other",
    )
    db.add(other)
    db.commit()

    response = client.get("/api/admin/users")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    emails = {u["email"] for u in body["users"]}
    assert emails == {"test@example.com", "other@example.com"}


def test_usage_summary_zero_when_no_data(client, db):
    register_and_login(client)
    admin = _promote_current_user(db, "test@example.com")

    response = client.get(f"/api/admin/usage/summary?user_ids={admin.id}")
    assert response.status_code == 200
    body = response.json()
    assert body[str(admin.id)]["lifetime_cost_micros"] == 0
    assert body[str(admin.id)]["lifetime_tokens"] == 0


def test_usage_summary_aggregates(client, db):
    register_and_login(client)
    admin = _promote_current_user(db, "test@example.com")

    event = LLMUsageEvent(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        input_tokens=1_000_000,
        cached_input_tokens=0,
        output_tokens=500_000,
    )
    record(db, admin.id, event)

    response = client.get(f"/api/admin/usage/summary?user_ids={admin.id}")
    body = response.json()
    entry = body[str(admin.id)]
    assert entry["lifetime_tokens"] == 1_500_000
    assert entry["lifetime_cost_micros"] == 300_000
    assert entry["last30d_tokens"] == 1_500_000


def test_user_usage_detail(client, db):
    register_and_login(client)
    admin = _promote_current_user(db, "test@example.com")

    event = LLMUsageEvent(
        provider="gemini",
        model="gemini-2.5-flash-lite",
        input_tokens=100,
        cached_input_tokens=0,
        output_tokens=50,
    )
    record(db, admin.id, event)

    today = date.today().isoformat()
    response = client.get(f"/api/admin/users/{admin.id}/usage?from={today}&to={today}")
    assert response.status_code == 200
    body = response.json()
    assert body["bucket"] == "day"
    assert len(body["series"]) == 1
    assert body["series"][0]["tokens"] == 150


def test_user_usage_detail_unknown_user(client, db):
    register_and_login(client)
    _promote_current_user(db, "test@example.com")

    response = client.get("/api/admin/users/9999/usage")
    assert response.status_code == 404


def test_delete_user_success(client, db):
    register_and_login(client)
    _promote_current_user(db, "test@example.com")
    victim = User(
        name="Victim",
        email="victim@example.com",
        password_hash="x",
        webhook_token="tok-victim",
    )
    db.add(victim)
    db.commit()
    db.refresh(victim)
    victim_id = victim.id

    response = client.delete(f"/api/admin/users/{victim_id}")
    assert response.status_code == 204
    db.expire_all()
    assert db.get(User, victim_id) is None


def test_delete_self_forbidden(client, db):
    register_and_login(client)
    admin = _promote_current_user(db, "test@example.com")

    response = client.delete(f"/api/admin/users/{admin.id}")
    assert response.status_code == 400


def test_delete_unknown_user(client, db):
    register_and_login(client)
    _promote_current_user(db, "test@example.com")

    response = client.delete("/api/admin/users/9999")
    assert response.status_code == 404


def test_me_includes_is_admin(client, db):
    register_and_login(client)
    _promote_current_user(db, "test@example.com")

    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["is_admin"] is True
