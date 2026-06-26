from app.services.categories import DefaultCategory
from tests.conftest import register_and_login

DEFAULT_CATEGORY_NAMES = {c.value for c in DefaultCategory}


def create_category(client, name="groceries"):
    return client.post("/api/categories", json={"name": name})


# --- Create ---


def test_create_category(client):
    register_and_login(client)
    response = create_category(client)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "groceries"
    assert "id" in data
    assert "created_at" in data


def test_create_category_normalizes_name(client):
    register_and_login(client)
    response = create_category(client, name="  Groceries  ")
    assert response.status_code == 201
    assert response.json()["name"] == "groceries"


def test_create_duplicate_category(client):
    register_and_login(client)
    create_category(client, name="groceries")
    response = create_category(client, name="groceries")
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_duplicate_category_different_case(client):
    register_and_login(client)
    create_category(client, name="groceries")
    response = create_category(client, name="GROCERIES")
    assert response.status_code == 409


def test_create_category_unauthenticated(client):
    response = create_category(client)
    assert response.status_code == 401


def test_create_category_empty_name(client):
    register_and_login(client)
    response = create_category(client, name="")
    assert response.status_code == 422


# --- List ---


def test_list_categories(client):
    register_and_login(client)
    create_category(client, name="travel")
    create_category(client, name="groceries")

    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    names = [c["name"] for c in data]
    for default in DEFAULT_CATEGORY_NAMES:
        assert default in names
    assert "travel" in names
    assert "groceries" in names


def test_list_categories_only_own(client):
    register_and_login(client, email="user1@example.com")
    create_category(client, name="user1-cat")

    register_and_login(client, email="user2@example.com")
    create_category(client, name="user2-cat")

    response = client.get("/api/categories")
    assert response.status_code == 200
    names = [c["name"] for c in response.json()]
    assert "user2-cat" in names
    assert "user1-cat" not in names
    for default in DEFAULT_CATEGORY_NAMES:
        assert default in names


def test_list_categories_unauthenticated(client):
    response = client.get("/api/categories")
    assert response.status_code == 401


# --- Update ---


def test_update_category(client):
    register_and_login(client)
    cat_id = create_category(client, name="groceries").json()["id"]

    response = client.put(f"/api/categories/{cat_id}", json={"name": "food"})
    assert response.status_code == 200
    assert response.json()["name"] == "food"


def test_update_category_normalizes_name(client):
    register_and_login(client)
    cat_id = create_category(client, name="groceries").json()["id"]

    response = client.put(f"/api/categories/{cat_id}", json={"name": "  FOOD  "})
    assert response.status_code == 200
    assert response.json()["name"] == "food"


def test_update_category_not_found(client):
    register_and_login(client)
    response = client.put("/api/categories/999", json={"name": "food"})
    assert response.status_code == 404


def test_update_category_duplicate_name(client):
    register_and_login(client)
    create_category(client, name="groceries")
    cat_id = create_category(client, name="bills").json()["id"]

    response = client.put(f"/api/categories/{cat_id}", json={"name": "groceries"})
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_update_category_same_name(client):
    register_and_login(client)
    cat_id = create_category(client, name="groceries").json()["id"]

    response = client.put(f"/api/categories/{cat_id}", json={"name": "groceries"})
    assert response.status_code == 200
    assert response.json()["name"] == "groceries"


def test_update_other_users_category(client):
    register_and_login(client, email="user1@example.com")
    cat_id = create_category(client, name="private").json()["id"]

    register_and_login(client, email="user2@example.com")
    response = client.put(f"/api/categories/{cat_id}", json={"name": "stolen"})
    assert response.status_code == 404


# --- Delete ---


def test_delete_category(client):
    register_and_login(client)
    cat_id = create_category(client, name="groceries").json()["id"]

    response = client.delete(f"/api/categories/{cat_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Category deleted"

    response = client.get("/api/categories")
    names = [c["name"] for c in response.json()]
    assert "groceries" not in names


def test_delete_category_not_found(client):
    register_and_login(client)
    response = client.delete("/api/categories/999")
    assert response.status_code == 404


def test_delete_other_users_category(client):
    register_and_login(client, email="user1@example.com")
    cat_id = create_category(client, name="private").json()["id"]

    register_and_login(client, email="user2@example.com")
    response = client.delete(f"/api/categories/{cat_id}")
    assert response.status_code == 404


# --- Default categories ---


def test_default_categories_in_listing(client):
    register_and_login(client)
    response = client.get("/api/categories")
    data = response.json()
    defaults = [c for c in data if c["is_default"]]
    assert {c["name"] for c in defaults} == DEFAULT_CATEGORY_NAMES


def test_cannot_update_default_category(client):
    register_and_login(client)
    response = client.get("/api/categories")
    default_cat = next(c for c in response.json() if c["is_default"])

    response = client.put(
        f"/api/categories/{default_cat['id']}", json={"name": "renamed"}
    )
    assert response.status_code == 403


def test_cannot_delete_default_category(client):
    register_and_login(client)
    response = client.get("/api/categories")
    default_cat = next(c for c in response.json() if c["is_default"])

    response = client.delete(f"/api/categories/{default_cat['id']}")
    assert response.status_code == 403


def test_cannot_create_category_with_default_name(client):
    register_and_login(client)
    response = create_category(client, name="transaction")
    assert response.status_code == 409
