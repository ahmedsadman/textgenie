from tests.conftest import (
    create_message,
    get_webhook_token,
    register_and_login,
)


def test_get_webhook_settings(client):
    register_and_login(client)
    response = client.get("/api/settings/webhook")
    assert response.status_code == 200
    data = response.json()
    assert "webhook_url" in data
    assert "webhook_token" in data
    assert data["webhook_token"] in data["webhook_url"]


def test_get_webhook_unauthenticated(client):
    response = client.get("/api/settings/webhook")
    assert response.status_code == 401


def test_regenerate_token(client):
    register_and_login(client)
    old_token = get_webhook_token(client)
    response = client.post("/api/settings/webhook/regenerate")
    assert response.status_code == 200
    new_token = response.json()["webhook_token"]
    assert new_token != old_token


def test_regenerate_invalidates_old_token(client):
    register_and_login(client)
    old_token = get_webhook_token(client)

    client.post("/api/settings/webhook/regenerate")

    response = create_message(client, old_token)
    assert response.status_code == 404


def test_regenerate_new_token_works(client):
    register_and_login(client)
    client.post("/api/settings/webhook/regenerate")
    new_token = get_webhook_token(client)

    response = create_message(client, new_token)
    assert response.status_code == 202


def test_regenerate_unauthenticated(client):
    response = client.post("/api/settings/webhook/regenerate")
    assert response.status_code == 401
