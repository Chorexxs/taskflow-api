import pytest
from fastapi.testclient import TestClient


def test_create_team(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "teamowner@example.com", "password": "password123"}
    )
    assert response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "teamowner@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]

    response = client.post(
        "/api/v1/teams/",
        json={"name": "My Team", "slug": "my-team", "description": "A test team"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My Team"
    assert data["slug"] == "my-team"


def test_create_team_duplicate_slug(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "owner2@example.com", "password": "password123"}
    )

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "owner2@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]

    client.post(
        "/api/v1/teams/",
        json={"name": "Team One", "slug": "duplicate-slug"},
        headers={"Authorization": f"Bearer {token}"}
    )
    response = client.post(
        "/api/v1/teams/",
        json={"name": "Team Two", "slug": "duplicate-slug"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_invite_member_as_admin(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "teamowner@example.com", "password": "password123"}
    )
    client.post(
        "/api/v1/auth/register",
        json={"email": "member@example.com", "password": "password123"}
    )

    owner_token = client.post(
        "/api/v1/auth/login",
        data={"username": "teamowner@example.com", "password": "password123"}
    ).json()["access_token"]

    client.post(
        "/api/v1/teams/",
        json={"name": "Test Team", "slug": "test-team"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    response = client.post(
        "/api/v1/teams/test-team/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    if response.status_code != 201:
        print("ERROR:", response.json())
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "member@example.com"
    assert data["role"] == "member"


def test_invite_member_as_member_returns_403(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "teamowner2@example.com", "password": "password123"}
    )
    client.post(
        "/api/v1/auth/register",
        json={"email": "member2@example.com", "password": "password123"}
    )

    owner_token = client.post(
        "/api/v1/auth/login",
        data={"username": "teamowner2@example.com", "password": "password123"}
    ).json()["access_token"]

    client.post(
        "/api/v1/teams/",
        json={"name": "Team2", "slug": "team2"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    client.post(
        "/api/v1/teams/team2/members",
        json={"email": "member2@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    member_token = client.post(
        "/api/v1/auth/login",
        data={"username": "member2@example.com", "password": "password123"}
    ).json()["access_token"]

    client.post(
        "/api/v1/auth/register",
        json={"email": "another@example.com", "password": "password123"}
    )

    response = client.post(
        "/api/v1/teams/team2/members",
        json={"email": "another@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {member_token}"}
    )
    assert response.status_code == 403


def test_member_leave_team(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "leaver@example.com", "password": "password123"}
    )
    client.post(
        "/api/v1/auth/register",
        json={"email": "teamowner3@example.com", "password": "password123"}
    )

    owner_token = client.post(
        "/api/v1/auth/login",
        data={"username": "teamowner3@example.com", "password": "password123"}
    ).json()["access_token"]

    client.post(
        "/api/v1/teams/",
        json={"name": "Team3", "slug": "team3"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    client.post(
        "/api/v1/teams/team3/members",
        json={"email": "leaver@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    member_token = client.post(
        "/api/v1/auth/login",
        data={"username": "leaver@example.com", "password": "password123"}
    ).json()["access_token"]

    response = client.delete(
        "/api/v1/teams/team3/members/2",
        headers={"Authorization": f"Bearer {member_token}"}
    )
    if response.status_code != 204:
        print("ERROR:", response.json())
    assert response.status_code == 204


def test_admin_remove_member(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "password123"}
    )
    client.post(
        "/api/v1/auth/register",
        json={"email": "toremove@example.com", "password": "password123"}
    )

    admin_token = client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "password123"}
    ).json()["access_token"]

    client.post(
        "/api/v1/teams/",
        json={"name": "Team4", "slug": "team4"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    client.post(
        "/api/v1/teams/team4/members",
        json={"email": "toremove@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    response = client.delete(
        "/api/v1/teams/team4/members/2",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code != 204:
        print("ERROR:", response.json())
    assert response.status_code == 204


def test_update_member_role(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "admin2@example.com", "password": "password123"}
    )
    client.post(
        "/api/v1/auth/register",
        json={"email": "member3@example.com", "password": "password123"}
    )

    admin_token = client.post(
        "/api/v1/auth/login",
        data={"username": "admin2@example.com", "password": "password123"}
    ).json()["access_token"]

    client.post(
        "/api/v1/teams/",
        json={"name": "Team5", "slug": "team5"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    client.post(
        "/api/v1/teams/team5/members",
        json={"email": "member3@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    response = client.patch(
        "/api/v1/teams/team5/members/2",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if response.status_code != 200:
        print("ERROR:", response.json())
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
