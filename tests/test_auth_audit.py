"""Audit events for authentication flows (T-033)."""

import pytest

from app.routers import auth as auth_router
from app.routers import users as users_router


class RecordingLogger:
    """Minimal structured logger that records events and keyword arguments."""

    def __init__(self):
        self.calls = []

    def info(self, event, **kwargs):
        self.calls.append((event, kwargs))

    def warning(self, event, **kwargs):
        self.calls.append((event, kwargs))

    def error(self, event, **kwargs):
        self.calls.append((event, kwargs))

    def events(self):
        return [event for event, _ in self.calls]

    def payloads(self):
        return [kwargs for _, kwargs in self.calls]


@pytest.fixture
def audit_log(monkeypatch):
    recorder = RecordingLogger()
    monkeypatch.setattr(auth_router, "logger", recorder)
    monkeypatch.setattr(users_router, "logger", recorder)
    return recorder


def _register(client, email="audit@example.com", password="password123"):
    return client.post("/api/v1/auth/register", json={"email": email, "password": password})


def _login(client, email, password):
    return client.post("/api/v1/auth/login", data={"username": email, "password": password})


def test_auth_events_include_user_id_without_pii(client, audit_log):
    email = "audit@example.com"
    password = "password123"

    register_response = _register(client, email, password)
    user_id = register_response.json()["id"]

    login_response = _login(client, email, password)
    assert login_response.status_code == 200
    tokens = login_response.json()

    # Five bad passwords lock the account and emit both failure and lockout.
    for _ in range(5):
        assert _login(client, email, "wrong-password").status_code == 401

    refresh_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh_response.status_code == 200
    rotated = refresh_response.json()

    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {rotated['access_token']}"},
        json={"refresh_token": rotated["refresh_token"]},
    )
    assert logout_response.status_code == 204

    events = audit_log.events()
    assert "auth_register_succeeded" in events
    assert "auth_login_succeeded" in events
    assert "auth_login_failed" in events
    assert "auth_account_locked" in events
    assert "auth_refresh_succeeded" in events
    assert "auth_logout_succeeded" in events

    for payload in audit_log.payloads():
        assert "email" not in payload
        assert "password" not in payload
        assert "token" not in payload
        assert payload.get("user_id") in {None, user_id}
        serialized = repr(payload)
        assert email not in serialized
        assert password not in serialized
        assert tokens["refresh_token"] not in serialized
        assert rotated["refresh_token"] not in serialized


def test_password_change_is_audited(client, audit_log):
    email = "change@example.com"
    password = "password123"
    _register(client, email, password)
    tokens = _login(client, email, password).json()

    response = client.put(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={
            "current_password": password,
            "password": "new-password123",
        },
    )
    assert response.status_code == 200

    assert "auth_credentials_updated" in audit_log.events()
    update_payload = audit_log.payloads()[audit_log.events().index("auth_credentials_updated")]
    assert update_payload["user_id"] == response.json()["id"]
    assert update_payload["password_changed"] is True
    assert update_payload["email_changed"] is False
    assert "new-password123" not in repr(update_payload)
