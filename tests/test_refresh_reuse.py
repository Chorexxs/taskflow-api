"""Refresh-token reuse detection revokes the whole session family (T-034)."""

from fastapi.testclient import TestClient

from app import models


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient) -> dict:
    client.post(
        "/api/v1/auth/register",
        json={"email": "reuse@example.com", "password": "password123"},
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "reuse@example.com", "password": "password123"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_reusing_a_rotated_refresh_token_revokes_all_sessions(client: TestClient, db_session):
    first = _login(client)

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    second = rotated.json()

    # Replay the already-rotated token.
    reuse = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert reuse.status_code == 401
    assert "reuse" in reuse.json()["detail"].lower()

    # Every token from the compromised family is now unusable.
    assert (
        client.post(
            "/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}
        ).status_code
        == 401
    )
    assert (
        client.get("/api/v1/users/me", headers=_headers(second["access_token"])).status_code == 401
    )

    db_session.expire_all()
    user = db_session.query(models.User).filter_by(email="reuse@example.com").one()
    assert user.token_version >= 1

    # A fresh login starts a new valid family.
    fresh = client.post(
        "/api/v1/auth/login",
        data={"username": "reuse@example.com", "password": "password123"},
    )
    assert fresh.status_code == 200
    assert (
        client.get("/api/v1/users/me", headers=_headers(fresh.json()["access_token"])).status_code
        == 200
    )


def test_logged_out_refresh_token_cannot_be_replayed(client: TestClient):
    tokens = _login(client)
    assert (
        client.post(
            "/api/v1/auth/logout",
            headers=_headers(tokens["access_token"]),
            json={"refresh_token": tokens["refresh_token"]},
        ).status_code
        == 204
    )

    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert replay.status_code == 401
