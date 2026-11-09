"""Errors keep the legacy `detail` field and add a stable envelope."""

from fastapi.testclient import TestClient


def test_unauthorized_error_envelope(client: TestClient):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
    body = response.json()
    assert body["detail"]
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == body["detail"]
    assert body["error"]["request_id"]
    assert response.headers["X-Request-ID"] == body["error"]["request_id"]


def test_validation_error_envelope(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "not-an-email", "password": "x"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Validation error"
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)


def test_not_found_error_envelope(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "errors@example.com", "password": "password123"},
    )
    token = client.post(
        "/api/v1/auth/login",
        data={"username": "errors@example.com", "password": "password123"},
    ).json()["access_token"]

    response = client.get(
        "/api/v1/teams/does-not-exist",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
