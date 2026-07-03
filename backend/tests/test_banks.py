from datetime import datetime, timedelta, timezone

from tests.conftest import register_and_login


def create_bank(client, name="BRAC Bank PLC"):
    return client.post("/api/banks", json={"name": name})


# --- Create ---


def test_create_bank(client):
    register_and_login(client)
    response = create_bank(client)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "BRAC Bank PLC"
    assert data["last_balance"] is None
    assert data["last_balance_at"] is None
    assert "id" in data
    assert "created_at" in data


def test_create_bank_trims_whitespace(client):
    register_and_login(client)
    response = create_bank(client, name="  EBL  ")
    assert response.status_code == 201
    assert response.json()["name"] == "EBL"


def test_create_bank_preserves_case(client):
    register_and_login(client)
    response = create_bank(client, name="BRAC Bank PLC")
    assert response.status_code == 201
    assert response.json()["name"] == "BRAC Bank PLC"


def test_create_duplicate_bank(client):
    register_and_login(client)
    create_bank(client, name="BRAC Bank")
    response = create_bank(client, name="BRAC Bank")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_duplicate_bank_case_insensitive(client):
    register_and_login(client)
    create_bank(client, name="BRAC Bank")
    response = create_bank(client, name="brac bank")
    assert response.status_code == 409


def test_create_bank_unauthenticated(client):
    response = create_bank(client)
    assert response.status_code == 401


def test_create_bank_empty_name(client):
    register_and_login(client)
    response = create_bank(client, name="")
    assert response.status_code == 422


# --- List ---


def test_list_banks(client):
    register_and_login(client)
    create_bank(client, name="Eastern Bank")
    create_bank(client, name="BRAC Bank")
    create_bank(client, name="City Bank")

    response = client.get("/api/banks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = [b["name"] for b in data]
    assert names == ["BRAC Bank", "City Bank", "Eastern Bank"]


def test_list_banks_only_own(client):
    register_and_login(client, email="user1@example.com")
    create_bank(client, name="User1 Bank")

    register_and_login(client, email="user2@example.com")
    create_bank(client, name="User2 Bank")

    response = client.get("/api/banks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "User2 Bank"


def test_list_banks_empty(client):
    register_and_login(client)
    response = client.get("/api/banks")
    assert response.status_code == 200
    assert response.json() == []


def test_list_banks_unauthenticated(client):
    response = client.get("/api/banks")
    assert response.status_code == 401


# --- Update ---


def test_update_bank_rename(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]

    response = client.patch(f"/api/banks/{bank_id}", json={"name": "BRAC Bank PLC"})
    assert response.status_code == 200
    assert response.json()["name"] == "BRAC Bank PLC"


def test_update_bank_set_balance_stamps_timestamp(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]

    before = datetime.now(timezone.utc) - timedelta(seconds=1)
    response = client.patch(f"/api/banks/{bank_id}", json={"last_balance": "1500.50"})
    after = datetime.now(timezone.utc) + timedelta(seconds=1)

    assert response.status_code == 200
    data = response.json()
    assert data["last_balance"] == "1500.50"
    assert data["last_balance_at"] is not None
    ts = datetime.fromisoformat(data["last_balance_at"])
    # SQLite (test DB) drops tzinfo; normalize to UTC for comparison.
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    assert before <= ts <= after


def test_update_bank_rename_and_set_balance(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC").json()["id"]

    response = client.patch(
        f"/api/banks/{bank_id}",
        json={"name": "BRAC Bank PLC", "last_balance": "500.00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "BRAC Bank PLC"
    assert data["last_balance"] == "500.00"
    assert data["last_balance_at"] is not None


def test_update_bank_no_fields_noop(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]

    response = client.patch(f"/api/banks/{bank_id}", json={})
    assert response.status_code == 200
    assert response.json()["name"] == "BRAC Bank"


def test_update_bank_not_found(client):
    register_and_login(client)
    response = client.patch("/api/banks/999", json={"name": "Ghost"})
    assert response.status_code == 404


def test_update_bank_duplicate_name(client):
    register_and_login(client)
    create_bank(client, name="BRAC Bank")
    bank_id = create_bank(client, name="EBL").json()["id"]

    response = client.patch(f"/api/banks/{bank_id}", json={"name": "BRAC Bank"})
    assert response.status_code == 409


def test_update_bank_duplicate_name_case_insensitive(client):
    register_and_login(client)
    create_bank(client, name="BRAC Bank")
    bank_id = create_bank(client, name="EBL").json()["id"]

    response = client.patch(f"/api/banks/{bank_id}", json={"name": "brac bank"})
    assert response.status_code == 409


def test_update_bank_same_name_succeeds(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]

    response = client.patch(f"/api/banks/{bank_id}", json={"name": "BRAC Bank"})
    assert response.status_code == 200
    assert response.json()["name"] == "BRAC Bank"


def test_update_bank_negative_balance_rejected(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]

    response = client.patch(f"/api/banks/{bank_id}", json={"last_balance": "-10.00"})
    assert response.status_code == 422


def test_update_other_users_bank(client):
    register_and_login(client, email="user1@example.com")
    bank_id = create_bank(client, name="Private Bank").json()["id"]

    register_and_login(client, email="user2@example.com")
    response = client.patch(f"/api/banks/{bank_id}", json={"name": "Stolen"})
    assert response.status_code == 404


# --- Delete ---


def test_delete_bank(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]

    response = client.delete(f"/api/banks/{bank_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Bank deleted"

    response = client.get("/api/banks")
    assert response.json() == []


def test_delete_bank_not_found(client):
    register_and_login(client)
    response = client.delete("/api/banks/999")
    assert response.status_code == 404


def test_delete_other_users_bank(client):
    register_and_login(client, email="user1@example.com")
    bank_id = create_bank(client, name="Private Bank").json()["id"]

    register_and_login(client, email="user2@example.com")
    response = client.delete(f"/api/banks/{bank_id}")
    assert response.status_code == 404


# --- Credit accounts ---


def _create_credit(client, name="BRAC Credit Card", card_digits="4988|3711"):
    return client.post(
        "/api/banks",
        json={"name": name, "account_type": "credit", "card_digits": card_digits},
    )


def test_create_bank_defaults_to_deposit(client):
    register_and_login(client)
    data = create_bank(client).json()
    assert data["account_type"] == "deposit"
    assert data["card_digits"] is None


def test_create_credit_bank_requires_card_digits(client):
    register_and_login(client)
    response = client.post(
        "/api/banks", json={"name": "Credit Card", "account_type": "credit"}
    )
    assert response.status_code == 422


def test_create_credit_bank_stores_card_digits(client):
    register_and_login(client)
    data = _create_credit(client).json()
    assert data["account_type"] == "credit"
    assert data["card_digits"] == "4988|3711"
    assert data["last_balance"] is None


def test_create_bank_invalid_account_type(client):
    register_and_login(client)
    response = client.post(
        "/api/banks",
        json={"name": "X", "account_type": "checking", "card_digits": "4988|3711"},
    )
    assert response.status_code == 422


def test_create_credit_bank_rejects_malformed_card_digits(client):
    register_and_login(client)
    for bad in ["4988-3711", "49883711", "abcd|3711", "988|3711", "4988|37110"]:
        response = client.post(
            "/api/banks",
            json={"name": f"X-{bad}", "account_type": "credit", "card_digits": bad},
        )
        assert response.status_code == 422, f"expected 422 for card_digits={bad!r}"


def test_list_bank_response_includes_credit_fields(client):
    register_and_login(client)
    create_bank(client, name="BRAC Bank")
    _create_credit(client, name="BRAC Credit Card")
    data = client.get("/api/banks").json()
    by_name = {b["name"]: b for b in data}
    assert by_name["BRAC Bank"]["account_type"] == "deposit"
    assert by_name["BRAC Bank"]["card_digits"] is None
    assert by_name["BRAC Credit Card"]["account_type"] == "credit"
    assert by_name["BRAC Credit Card"]["card_digits"] == "4988|3711"


def test_deposit_and_credit_same_institution_coexist(client):
    register_and_login(client)
    assert create_bank(client, name="BRAC Bank").status_code == 201
    assert _create_credit(client, name="BRAC Credit Card").status_code == 201


def test_update_flip_deposit_to_credit_clears_balance(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]
    client.patch(f"/api/banks/{bank_id}", json={"last_balance": "500.00"})

    response = client.patch(
        f"/api/banks/{bank_id}",
        json={"account_type": "credit", "card_digits": "4988|3711"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["account_type"] == "credit"
    assert data["card_digits"] == "4988|3711"
    assert data["last_balance"] is None
    assert data["last_balance_at"] is None


def test_update_flip_to_credit_without_card_digits_rejected(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]
    response = client.patch(f"/api/banks/{bank_id}", json={"account_type": "credit"})
    assert response.status_code == 400


def test_update_credit_bank_rejects_last_balance(client):
    register_and_login(client)
    bank_id = _create_credit(client).json()["id"]
    response = client.patch(f"/api/banks/{bank_id}", json={"last_balance": "500.00"})
    assert response.status_code == 400


def test_update_flip_credit_to_deposit_clears_card_and_allows_balance(client):
    register_and_login(client)
    bank_id = _create_credit(client).json()["id"]

    response = client.patch(
        f"/api/banks/{bank_id}",
        json={"account_type": "deposit", "last_balance": "1000.00"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["account_type"] == "deposit"
    assert data["card_digits"] is None
    assert data["last_balance"] == "1000.00"


def test_update_set_credit_and_balance_same_request_rejected(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]
    response = client.patch(
        f"/api/banks/{bank_id}",
        json={
            "account_type": "credit",
            "card_digits": "4988|3711",
            "last_balance": "500.00",
        },
    )
    assert response.status_code == 422


def test_update_set_deposit_and_card_digits_same_request_rejected(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]
    response = client.patch(
        f"/api/banks/{bank_id}",
        json={"account_type": "deposit", "card_digits": "4988|3711"},
    )
    assert response.status_code == 422


def test_update_credit_bank_card_digits(client):
    register_and_login(client)
    bank_id = _create_credit(client).json()["id"]
    response = client.patch(f"/api/banks/{bank_id}", json={"card_digits": "1234|5678"})
    assert response.status_code == 200
    assert response.json()["card_digits"] == "1234|5678"
