"""Password policy and global session revocation tests."""

from fastapi.testclient import TestClient


def _register_and_login(client: TestClient, email: str, password: str = "password123") -> dict:
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register.status_code == 201, register.text
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_registration_rejects_short_passwords(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "short@example.com", "password": "short"},
    )
    assert response.status_code == 422


def test_password_change_requires_current_password(client: TestClient):
    tokens = _register_and_login(client, "nocurrent@example.com")

    response = client.put(
        "/api/v1/users/me",
        json={"password": "newpassword123"},
        headers=_headers(tokens["access_token"]),
    )
    assert response.status_code == 400
    assert "current_password" in response.json()["detail"]


def test_password_change_rejects_wrong_current_password(client: TestClient):
    tokens = _register_and_login(client, "wrongcurrent@example.com")

    response = client.put(
        "/api/v1/users/me",
        json={"current_password": "not-the-password", "password": "newpassword123"},
        headers=_headers(tokens["access_token"]),
    )
    assert response.status_code == 400


def test_password_change_revokes_every_existing_session(client: TestClient):
    tokens = _register_and_login(client, "rotate@example.com")

    response = client.put(
        "/api/v1/users/me",
        json={"current_password": "password123", "password": "newpassword123"},
        headers=_headers(tokens["access_token"]),
    )
    assert response.status_code == 200, response.text

    # The access token used for the change is now invalid.
    old_access = client.get(
        "/api/v1/users/me",
        headers=_headers(tokens["access_token"]),
    )
    assert old_access.status_code == 401

    # The old refresh token is invalid too.
    old_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert old_refresh.status_code == 401

    # The old password no longer works; the new one does.
    old_login = client.post(
        "/api/v1/auth/login",
        data={"username": "rotate@example.com", "password": "password123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        data={"username": "rotate@example.com", "password": "newpassword123"},
    )
    assert new_login.status_code == 200
    assert new_login.json()["access_token"]
