"""Tests for team editing and membership lifecycle."""

from fastapi.testclient import TestClient


def _login(client: TestClient, email: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    return client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    ).json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _team_with_member(client: TestClient):
    admin_token = _login(client, "team-admin@example.com")
    member_token = _login(client, "team-member@example.com")
    assert client.post(
        "/api/v1/teams/",
        json={"name": "Original Name", "slug": "editable-team", "description": "Original"},
        headers=_headers(admin_token),
    ).status_code == 201
    assert client.post(
        "/api/v1/teams/editable-team/members",
        json={"email": "team-member@example.com", "role": "member"},
        headers=_headers(admin_token),
    ).status_code == 201
    return admin_token, member_token


def test_admin_can_update_team(client: TestClient):
    admin_token, _ = _team_with_member(client)

    response = client.patch(
        "/api/v1/teams/editable-team",
        json={"name": "Updated Name", "description": "Updated description"},
        headers=_headers(admin_token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Updated Name"
    assert response.json()["description"] == "Updated description"

    fetched = client.get("/api/v1/teams/editable-team", headers=_headers(admin_token))
    assert fetched.json()["name"] == "Updated Name"


def test_member_cannot_update_team(client: TestClient):
    _, member_token = _team_with_member(client)

    response = client.patch(
        "/api/v1/teams/editable-team",
        json={"name": "Hijacked"},
        headers=_headers(member_token),
    )
    assert response.status_code == 403


def test_team_update_rejects_empty_name(client: TestClient):
    admin_token, _ = _team_with_member(client)

    response = client.patch(
        "/api/v1/teams/editable-team",
        json={"name": "   "},
        headers=_headers(admin_token),
    )
    assert response.status_code == 400


def test_team_update_requires_authentication(client: TestClient):
    response = client.patch("/api/v1/teams/editable-team", json={"name": "Nope"})
    assert response.status_code == 401
