"""SECRET_KEY rotation with a previous verification key (T-103)."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from app.auth import decode_token, verification_keys
from app.config import Settings, settings

NEW_KEY = "new-rotation-key-0123456789abcdef-32+"
OLD_KEY = "old-rotation-key-0123456789abcdef-32+"


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: TestClient, email: str) -> str:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "password123"},
        ).status_code
        == 201
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _token(email: str, key: str, *, expired: bool = False) -> str:
    now = datetime.now(timezone.utc)
    expires = now - timedelta(minutes=1) if expired else now + timedelta(minutes=5)
    return jwt.encode(
        {"sub": email, "type": "access", "exp": expires},
        key,
        algorithm=settings.ALGORITHM,
    )


def test_decode_accepts_the_previous_key(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", NEW_KEY)
    monkeypatch.setattr(settings, "SECRET_KEY_PREVIOUS", OLD_KEY)

    payload = decode_token(_token("rotated@example.com", OLD_KEY))

    assert payload["sub"] == "rotated@example.com"


def test_decode_rejects_the_previous_key_after_the_window(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", NEW_KEY)
    monkeypatch.setattr(settings, "SECRET_KEY_PREVIOUS", "")

    with pytest.raises(jwt.InvalidSignatureError):
        decode_token(_token("rotated@example.com", OLD_KEY))


def test_expired_tokens_still_verify_with_the_previous_key(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", NEW_KEY)
    monkeypatch.setattr(settings, "SECRET_KEY_PREVIOUS", OLD_KEY)

    payload = decode_token(
        _token("rotated@example.com", OLD_KEY, expired=True),
        options={"verify_exp": False},
    )

    assert payload["sub"] == "rotated@example.com"


def test_expired_tokens_are_rejected_without_disabling_exp(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", NEW_KEY)
    monkeypatch.setattr(settings, "SECRET_KEY_PREVIOUS", OLD_KEY)

    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(_token("rotated@example.com", OLD_KEY, expired=True))


def test_verification_keys_ignore_duplicates(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", NEW_KEY)
    monkeypatch.setattr(settings, "SECRET_KEY_PREVIOUS", NEW_KEY)

    assert verification_keys() == (NEW_KEY,)


def test_existing_session_survives_the_rotation_window(client, monkeypatch):
    email = "rotate-session@example.com"
    token = _register_and_login(client, email)
    old_key = settings.secret_key

    monkeypatch.setattr(settings, "SECRET_KEY", NEW_KEY)
    monkeypatch.setattr(settings, "SECRET_KEY_PREVIOUS", old_key)
    accepted = client.get("/api/v1/users/me", headers=_headers(token))
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["email"] == email

    # Once the previous key is retired, the old token stops working.
    monkeypatch.setattr(settings, "SECRET_KEY_PREVIOUS", "")
    rejected = client.get("/api/v1/users/me", headers=_headers(token))
    assert rejected.status_code == 401


def test_tokens_signed_with_the_new_key_are_accepted(client, monkeypatch):
    email = "rotate-new-key@example.com"
    _register_and_login(client, email)

    monkeypatch.setattr(settings, "SECRET_KEY", NEW_KEY)
    monkeypatch.setattr(settings, "SECRET_KEY_PREVIOUS", "")

    response = client.get("/api/v1/users/me", headers=_headers(_token(email, NEW_KEY)))

    assert response.status_code == 200, response.text
    assert response.json()["email"] == email


def test_previous_key_must_differ_from_the_primary_key():
    config = Settings(
        ENVIRONMENT="production",
        SECRET_KEY=NEW_KEY,
        SECRET_KEY_PREVIOUS=NEW_KEY,
        DATABASE_URL="postgresql://user:pass@localhost/db",
        DB_SSLMODE="require",
    )

    with pytest.raises(RuntimeError, match="SECRET_KEY_PREVIOUS"):
        config.validate_runtime()
