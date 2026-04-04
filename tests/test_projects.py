import pytest
from fastapi.testclient import TestClient


def setup_team(client: TestClient, email: str, password: str = "password123"):
    client.post("/auth/register", json={"email": email, "password": password})
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    client.post("/teams/", json={"name": "Test Team", "slug": "test-team"}, headers={"Authorization": f"Bearer {token}"})
    return token


def test_create_project(client: TestClient):
    token = setup_team(client, "projowner@example.com")

    response = client.post(
        "/teams/test-team/projects/",
        json={"name": "New Project", "description": "Project description"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Project"
    assert data["status"] == "active"


def test_list_projects(client: TestClient):
    token = setup_team(client, "listowner@example.com")

    client.post(
        "/teams/test-team/projects/",
        json={"name": "Project 1"},
        headers={"Authorization": f"Bearer {token}"}
    )
    client.post(
        "/teams/test-team/projects/",
        json={"name": "Project 2"},
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.get(
        "/teams/test-team/projects/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_get_project(client: TestClient):
    token = setup_team(client, "getowner@example.com")

    client.post(
        "/teams/test-team/projects/",
        json={"name": "Get Project"},
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.get(
        "/teams/test-team/projects/Get Project",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Get Project"


def test_update_project_as_admin(client: TestClient):
    token = setup_team(client, "updateowner@example.com")

    client.post(
        "/teams/test-team/projects/",
        json={"name": "Original Name"},
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.patch(
        "/teams/test-team/projects/Original Name",
        json={"name": "Updated Name", "description": "New description"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "New description"


def test_archive_project_as_admin(client: TestClient):
    token = setup_team(client, "archiveowner@example.com")

    client.post(
        "/teams/test-team/projects/",
        json={"name": "To Archive"},
        headers={"Authorization": f"Bearer {token}"}
    )

    response = client.delete(
        "/teams/test-team/projects/To Archive",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 204

    response = client.get(
        "/teams/test-team/projects/To Archive",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.json()["status"] == "archived"


def test_member_cannot_archive_project(client: TestClient):
    client.post("/auth/register", json={"email": "member@example.com", "password": "password123"})
    token = setup_team(client, "teamadmin@example.com")

    client.post(
        "/teams/test-team/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {token}"}
    )

    client.post(
        "/teams/test-team/projects/",
        json={"name": "Protected Project"},
        headers={"Authorization": f"Bearer {token}"}
    )

    member_token = client.post("/auth/login", data={"username": "member@example.com", "password": "password123"}).json()["access_token"]

    response = client.delete(
        "/teams/test-team/projects/Protected Project",
        headers={"Authorization": f"Bearer {member_token}"}
    )
    assert response.status_code == 403
