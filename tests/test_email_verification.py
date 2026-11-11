"""Email verification flow (T-113)."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import models
from app.auth import get_password_hash
from app.config import settings
from app.email_verification import consume_token, issue_token

GENERIC_MESSAGE = "If the email is available"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register(client: TestClient, email: str, password: str = "password123"):
    return client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )


def _login(client: TestClient, email: str, password: str = "password123"):
    return client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )


def test_verification_disabled_keeps_current_registration(client: TestClient):
    response = _register(client, "no-verification@example.com")

    assert response.status_code == 201
    payload = response.json()
    assert payload["id"] == 1
    assert payload["email_verified"] is True
    assert _login(client, "no-verification@example.com").status_code == 200


def test_verification_flow_requires_email_and_token(client: TestClient, db_session, monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(settings, "EMAIL_VERIFICATION_REQUIRED", True)
    monkeypatch.setattr(
        "app.routers.auth.send_verification_email",
        lambda to, token: sent.append((to, token)),
    )

    registered = _register(client, "verify-me@example.com")

    assert registered.status_code == 201
    assert GENERIC_MESSAGE in registered.json()["message"]
    assert registered.json()["id"] is None
    assert len(sent) == 1
    assert sent[0][0] == "verify-me@example.com"

    user = db_session.query(models.User).filter_by(email="verify-me@example.com").one()
    assert user.email_verified is False
    stored = db_session.query(models.EmailVerificationToken).one()
    assert stored.token_hash != sent[0][1]
    assert len(stored.token_hash) == 64

    assert _login(client, "verify-me@example.com").status_code == 403

    verified = client.post("/api/v1/auth/verify-email", json={"token": sent[0][1]})
    assert verified.status_code == 200, verified.text
    db_session.refresh(user)
    assert user.email_verified is True
    assert _login(client, "verify-me@example.com").status_code == 200

    replay = client.post("/api/v1/auth/verify-email", json={"token": sent[0][1]})
    assert replay.status_code == 400


def test_duplicate_registration_does_not_reveal_existence(client: TestClient, monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(settings, "EMAIL_VERIFICATION_REQUIRED", True)
    monkeypatch.setattr(
        "app.routers.auth.send_verification_email",
        lambda to, token: sent.append((to, token)),
    )

    first = _register(client, "duplicate@example.com")
    second = _register(client, "duplicate@example.com")

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["message"] == second.json()["message"]
    assert len(sent) == 1


def test_resend_invalidates_the_previous_token(client: TestClient, db_session, monkeypatch):
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(settings, "EMAIL_VERIFICATION_REQUIRED", True)
    monkeypatch.setattr(
        "app.routers.auth.send_verification_email",
        lambda to, token: sent.append((to, token)),
    )

    _register(client, "resend@example.com")
    first_token = sent[0][1]

    resent = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "resend@example.com"},
    )
    assert resent.status_code == 202
    assert len(sent) == 2
    assert sent[1][1] != first_token

    assert client.post("/api/v1/auth/verify-email", json={"token": first_token}).status_code == 400
    assert client.post("/api/v1/auth/verify-email", json={"token": sent[1][1]}).status_code == 200


def test_resend_unknown_email_is_generic(client: TestClient, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_VERIFICATION_REQUIRED", True)

    response = client.post(
        "/api/v1/auth/resend-verification",
        json={"email": "missing@example.com"},
    )

    assert response.status_code == 202
    assert "If the account exists" in response.json()["message"]


def test_expired_token_is_rejected(client: TestClient, db_session, monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_VERIFICATION_REQUIRED", True)
    user = models.User(
        email="expired@example.com",
        hashed_password=get_password_hash("password123"),
        email_verified=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    raw = issue_token(db_session, user)
    record = db_session.query(models.EmailVerificationToken).one()
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    assert consume_token(db_session, raw) is None
    assert client.post("/api/v1/auth/verify-email", json={"token": raw}).status_code == 400
