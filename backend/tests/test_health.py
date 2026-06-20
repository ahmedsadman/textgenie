def test_health_check_returns_ok(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["message"] == "TextGenie API is running"


def test_health_check_response_schema(client):
    response = client.get("/api/health")
    data = response.json()
    assert set(data.keys()) == {"status", "message"}
