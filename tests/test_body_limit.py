"""Request body size limits (SEC-2.2)."""

from fastapi.testclient import TestClient


def test_rejects_oversized_json_bodies(client: TestClient):
    payload = '{"email":"' + "a" * 1_100_000 + '","password":"password123"}'

    response = client.post(
        "/api/v1/auth/register",
        content=payload,
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_rejects_oversized_form_bodies(client: TestClient):
    payload = "username=" + "a" * 70_000 + "&password=password123"

    response = client.post(
        "/api/v1/auth/login",
        content=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 413


def test_rejects_oversized_chunked_bodies(client: TestClient):
    def chunks():
        yield b'{"email":"'
        yield b"a" * 1_100_000
        yield b'","password":"password123"}'

    response = client.post(
        "/api/v1/auth/register",
        content=chunks(),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


def test_normal_json_bodies_still_work(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "body-limit@example.com", "password": "password123"},
    )

    assert response.status_code == 201
