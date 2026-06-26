from app.services import metadata_blacklist
from tests.conftest import register_and_login

# --- Helper module ---


def test_parse_none_returns_empty():
    assert metadata_blacklist.parse(None) == []
    assert metadata_blacklist.parse("") == []


def test_parse_splits_and_normalizes():
    assert metadata_blacklist.parse("BRAC, EBL ,gp ") == ["brac", "ebl", "gp"]


def test_parse_drops_empty_segments():
    assert metadata_blacklist.parse(",,brac,,") == ["brac"]


def test_serialize_dedupes_and_lowercases():
    assert metadata_blacklist.serialize(["BRAC", "brac", "EBL"]) == "brac,ebl"


def test_serialize_trims_and_drops_empties():
    assert metadata_blacklist.serialize(["  BRAC  ", "", " "]) == "brac"


def test_serialize_empty_returns_empty_string():
    assert metadata_blacklist.serialize([]) == ""


def test_contains_is_case_insensitive():
    raw = "brac,ebl"
    assert metadata_blacklist.contains("BRAC", raw) is True
    assert metadata_blacklist.contains("brac", raw) is True
    assert metadata_blacklist.contains("Ebl", raw) is True
    assert metadata_blacklist.contains("citybank", raw) is False


def test_contains_handles_none_and_empty():
    assert metadata_blacklist.contains("BRAC", None) is False
    assert metadata_blacklist.contains("BRAC", "") is False
    assert metadata_blacklist.contains("", "brac") is False


def test_contains_trims_sender():
    assert metadata_blacklist.contains("  BRAC  ", "brac") is True


# --- Settings API ---


def test_get_blacklist_default_is_empty(client):
    register_and_login(client)
    response = client.get("/api/settings/metadata-blacklist")
    assert response.status_code == 200
    assert response.json() == {"senders": []}


def test_get_blacklist_unauthenticated(client):
    response = client.get("/api/settings/metadata-blacklist")
    assert response.status_code == 401


def test_put_blacklist_round_trip(client):
    register_and_login(client)
    response = client.put(
        "/api/settings/metadata-blacklist",
        json={"senders": ["BRAC", "EBL"]},
    )
    assert response.status_code == 200
    assert response.json() == {"senders": ["brac", "ebl"]}

    response = client.get("/api/settings/metadata-blacklist")
    assert response.json() == {"senders": ["brac", "ebl"]}


def test_put_blacklist_normalizes_and_dedupes(client):
    register_and_login(client)
    response = client.put(
        "/api/settings/metadata-blacklist",
        json={"senders": ["  BRAC  ", "brac", "EBL", "", " "]},
    )
    assert response.status_code == 200
    assert response.json() == {"senders": ["brac", "ebl"]}


def test_put_blacklist_rejects_commas(client):
    register_and_login(client)
    response = client.put(
        "/api/settings/metadata-blacklist",
        json={"senders": ["BRAC,EBL"]},
    )
    assert response.status_code == 400


def test_put_blacklist_empty_clears_all(client):
    register_and_login(client)
    client.put(
        "/api/settings/metadata-blacklist",
        json={"senders": ["BRAC", "EBL"]},
    )

    response = client.put("/api/settings/metadata-blacklist", json={"senders": []})
    assert response.status_code == 200
    assert response.json() == {"senders": []}

    response = client.get("/api/settings/metadata-blacklist")
    assert response.json() == {"senders": []}


def test_put_blacklist_unauthenticated(client):
    response = client.put("/api/settings/metadata-blacklist", json={"senders": []})
    assert response.status_code == 401


def test_blacklist_cross_user_isolation(client):
    register_and_login(client, email="user1@example.com")
    client.put("/api/settings/metadata-blacklist", json={"senders": ["BRAC"]})

    register_and_login(client, email="user2@example.com")
    response = client.get("/api/settings/metadata-blacklist")
    assert response.json() == {"senders": []}

    client.put("/api/settings/metadata-blacklist", json={"senders": ["EBL"]})

    register_and_login(client, email="user1@example.com")
    response = client.get("/api/settings/metadata-blacklist")
    assert response.json() == {"senders": ["brac"]}
