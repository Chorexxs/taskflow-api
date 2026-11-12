"""Password policy, lockout and global session revocation tests."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import models
from app.config import settings


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


def _fail_login(client: TestClient, email: str, times: int) -> None:
    for _ in range(times):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": email, "password": "wrong-password"},
        )
        assert response.status_code == 401, response.text


def test_lockout_revokes_every_existing_session(client: TestClient):
    """SEC-ASVS-10: a locked account must not keep usable tokens (T-116)."""
    email = "lockout@example.com"
    tokens = _register_and_login(client, email)

    # One failure below the threshold keeps the session alive.
    _fail_login(client, email, settings.MAX_LOGIN_ATTEMPTS - 1)
    assert (
        client.get("/api/v1/users/me", headers=_headers(tokens["access_token"])).status_code == 200
    )

    # The failure that triggers the lock revokes access and refresh tokens.
    _fail_login(client, email, 1)
    assert (
        client.get("/api/v1/users/me", headers=_headers(tokens["access_token"])).status_code == 401
    )
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        ).status_code
        == 401
    )

    # Even the right password is rejected while the lockout is active.
    locked = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert locked.status_code == 423


def test_login_after_lockout_expiry_issues_a_working_session(client: TestClient, db_session):
    """Unlocking must not leave the account with a stale ``token_version``."""
    email = "expired-lock@example.com"
    _register_and_login(client, email)
    _fail_login(client, email, settings.MAX_LOGIN_ATTEMPTS)

    db_session.expire_all()
    user = db_session.query(models.User).filter(models.User.email == email).one()
    assert user.token_version == 1
    user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert login.status_code == 200, login.text
    fresh = login.json()
    assert (
        client.get("/api/v1/users/me", headers=_headers(fresh["access_token"])).status_code == 200
    )
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": fresh["refresh_token"]},
        ).status_code
        == 200
    )

    db_session.expire_all()
    unlocked = db_session.query(models.User).filter(models.User.email == email).one()
    assert unlocked.token_version == 1
    assert unlocked.is_blocked is False
