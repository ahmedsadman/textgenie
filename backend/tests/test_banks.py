from datetime import datetime, timedelta, timezone

from tests.conftest import register_and_login


def create_bank(client, name="BRAC Bank PLC", senders=None, templates=None):
    payload = {"name": name}
    if senders is not None:
        payload["senders"] = senders
    if templates is not None:
        payload["templates"] = templates
    return client.post("/api/banks", json=payload)


# --- Create ---


def test_create_bank(client):
    register_and_login(client)
    response = create_bank(client)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "BRAC Bank PLC"
    assert data["senders"] == []
    assert data["templates"] == []
    assert data["last_balance"] is None
    assert data["last_balance_at"] is None
    assert "id" in data
    assert "created_at" in data


def test_create_bank_with_senders(client):
    register_and_login(client)
    response = create_bank(client, senders=["BRACBANK", "BRAC_SMS"])
    assert response.status_code == 201
    data = response.json()
    assert sorted(data["senders"]) == ["BRACBANK", "BRAC_SMS"]


def test_create_bank_with_templates(client):
    register_and_login(client)
    response = create_bank(client, templates=["Balance: {{balance}} BDT"])
    assert response.status_code == 201
    assert len(response.json()["templates"]) == 1


def test_create_bank_templates_are_normalized(client):
    register_and_login(client)
    response = create_bank(client, templates=["Balance:  {{balance}}\nBDT"])
    assert response.status_code == 201
    assert response.json()["templates"] == ["Balance: {{balance}} BDT"]


def test_create_bank_too_many_senders(client):
    register_and_login(client)
    response = create_bank(client, senders=["A", "B", "C", "D"])
    assert response.status_code == 422


def test_create_bank_duplicate_balance_in_template(client):
    register_and_login(client)
    response = create_bank(client, templates=["{{balance}} and {{balance}}"])
    assert response.status_code == 422


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
    create_bank(client, name="BRAC Bank", senders=["BRACBANK"])
    create_bank(client, name="City Bank")

    response = client.get("/api/banks")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    names = [b["name"] for b in data]
    assert names == ["BRAC Bank", "City Bank", "Eastern Bank"]
    brac = next(b for b in data if b["name"] == "BRAC Bank")
    assert brac["senders"] == ["BRACBANK"]


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

    response = client.put(f"/api/banks/{bank_id}", json={"name": "BRAC Bank PLC"})
    assert response.status_code == 200
    assert response.json()["name"] == "BRAC Bank PLC"


def test_update_bank_senders(client):
    register_and_login(client)
    bank_id = create_bank(client, senders=["BRACBANK"]).json()["id"]

    response = client.put(
        f"/api/banks/{bank_id}", json={"senders": ["BRAC_NEW", "BRAC_SMS"]}
    )
    assert response.status_code == 200
    assert sorted(response.json()["senders"]) == ["BRAC_NEW", "BRAC_SMS"]


def test_update_bank_clear_senders(client):
    register_and_login(client)
    bank_id = create_bank(client, senders=["BRACBANK"]).json()["id"]

    response = client.put(f"/api/banks/{bank_id}", json={"senders": []})
    assert response.status_code == 200
    assert response.json()["senders"] == []


def test_update_bank_senders_none_keeps_existing(client):
    register_and_login(client)
    bank_id = create_bank(client, senders=["BRACBANK"]).json()["id"]

    response = client.put(f"/api/banks/{bank_id}", json={"name": "New Name"})
    assert response.status_code == 200
    assert response.json()["senders"] == ["BRACBANK"]


def test_update_bank_templates(client):
    register_and_login(client)
    bank_id = create_bank(client).json()["id"]

    response = client.put(
        f"/api/banks/{bank_id}",
        json={"templates": ["Balance: {{balance}} BDT"]},
    )
    assert response.status_code == 200
    assert len(response.json()["templates"]) == 1


def test_update_bank_templates_normalized(client):
    register_and_login(client)
    bank_id = create_bank(client).json()["id"]

    response = client.put(
        f"/api/banks/{bank_id}",
        json={"templates": ["Balance:  {{balance}}\nBDT"]},
    )
    assert response.status_code == 200
    assert response.json()["templates"] == ["Balance: {{balance}} BDT"]


def test_update_bank_too_many_senders(client):
    register_and_login(client)
    bank_id = create_bank(client).json()["id"]

    response = client.put(
        f"/api/banks/{bank_id}", json={"senders": ["A", "B", "C", "D"]}
    )
    assert response.status_code == 422


def test_update_bank_duplicate_balance_in_template(client):
    register_and_login(client)
    bank_id = create_bank(client).json()["id"]

    response = client.put(
        f"/api/banks/{bank_id}",
        json={"templates": ["{{balance}} and {{balance}}"]},
    )
    assert response.status_code == 422


def test_update_bank_set_balance_stamps_timestamp(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]

    before = datetime.now(timezone.utc) - timedelta(seconds=1)
    response = client.put(f"/api/banks/{bank_id}", json={"last_balance": "1500.50"})
    after = datetime.now(timezone.utc) + timedelta(seconds=1)

    assert response.status_code == 200
    data = response.json()
    assert data["last_balance"] == "1500.50"
    assert data["last_balance_at"] is not None
    ts = datetime.fromisoformat(data["last_balance_at"])
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    assert before <= ts <= after


def test_update_bank_rename_and_set_balance(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC").json()["id"]

    response = client.put(
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

    response = client.put(f"/api/banks/{bank_id}", json={})
    assert response.status_code == 200
    assert response.json()["name"] == "BRAC Bank"


def test_update_bank_not_found(client):
    register_and_login(client)
    response = client.put("/api/banks/999", json={"name": "Ghost"})
    assert response.status_code == 404


def test_update_bank_duplicate_name(client):
    register_and_login(client)
    create_bank(client, name="BRAC Bank")
    bank_id = create_bank(client, name="EBL").json()["id"]

    response = client.put(f"/api/banks/{bank_id}", json={"name": "BRAC Bank"})
    assert response.status_code == 409


def test_update_bank_duplicate_name_case_insensitive(client):
    register_and_login(client)
    create_bank(client, name="BRAC Bank")
    bank_id = create_bank(client, name="EBL").json()["id"]

    response = client.put(f"/api/banks/{bank_id}", json={"name": "brac bank"})
    assert response.status_code == 409


def test_update_bank_same_name_succeeds(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]

    response = client.put(f"/api/banks/{bank_id}", json={"name": "BRAC Bank"})
    assert response.status_code == 200
    assert response.json()["name"] == "BRAC Bank"


def test_update_bank_negative_balance_rejected(client):
    register_and_login(client)
    bank_id = create_bank(client, name="BRAC Bank").json()["id"]

    response = client.put(f"/api/banks/{bank_id}", json={"last_balance": "-10.00"})
    assert response.status_code == 422


def test_update_other_users_bank(client):
    register_and_login(client, email="user1@example.com")
    bank_id = create_bank(client, name="Private Bank").json()["id"]

    register_and_login(client, email="user2@example.com")
    response = client.put(f"/api/banks/{bank_id}", json={"name": "Stolen"})
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


def test_delete_bank_cascades_senders_and_templates(client):
    register_and_login(client)
    bank_id = create_bank(
        client,
        senders=["BRACBANK"],
        templates=["Balance: {{balance}}"],
    ).json()["id"]

    client.delete(f"/api/banks/{bank_id}")
    assert client.get("/api/banks").json() == []
