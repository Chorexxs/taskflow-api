"""Project archive/restore lifecycle tests."""

from fastapi.testclient import TestClient


def _login(client: TestClient, email: str) -> str:
    client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
    return client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    ).json()["access_token"]


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup_project(client: TestClient):
    admin_token = _login(client, "project-admin@example.com")
    member_token = _login(client, "project-member@example.com")
    assert client.post(
        "/api/v1/teams/",
        json={"name": "Project Team", "slug": "project-team"},
        headers=_headers(admin_token),
    ).status_code == 201
    assert client.post(
        "/api/v1/teams/project-team/members",
        json={"email": "project-member@example.com", "role": "member"},
        headers=_headers(admin_token),
    ).status_code == 201
    assert client.post(
        "/api/v1/teams/project-team/projects/",
        json={"name": "Lifecycle Project"},
        headers=_headers(admin_token),
    ).status_code == 201
    return admin_token, member_token


def test_admin_can_archive_and_restore_project(client: TestClient):
    admin_token, _ = _setup_project(client)

    archived = client.post(
        "/api/v1/teams/project-team/projects/Lifecycle Project/archive",
        headers=_headers(admin_token),
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["status"] == "archived"

    default_list = client.get(
        "/api/v1/teams/project-team/projects/",
        headers=_headers(admin_token),
    )
    assert default_list.status_code == 200
    assert default_list.json() == []

    with_archived = client.get(
        "/api/v1/teams/project-team/projects/?include_archived=true",
        headers=_headers(admin_token),
    )
    assert [project["status"] for project in with_archived.json()] == ["archived"]

    restored = client.post(
        "/api/v1/teams/project-team/projects/Lifecycle Project/restore",
        headers=_headers(admin_token),
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"

    default_list = client.get(
        "/api/v1/teams/project-team/projects/",
        headers=_headers(admin_token),
    )
    assert [project["status"] for project in default_list.json()] == ["active"]


def test_member_cannot_archive_or_restore_project(client: TestClient):
    _, member_token = _setup_project(client)

    archive = client.post(
        "/api/v1/teams/project-team/projects/Lifecycle Project/archive",
        headers=_headers(member_token),
    )
    assert archive.status_code == 403

    restore = client.post(
        "/api/v1/teams/project-team/projects/Lifecycle Project/restore",
        headers=_headers(member_token),
    )
    assert restore.status_code == 403


def test_archive_and_restore_are_idempotent(client: TestClient):
    admin_token, _ = _setup_project(client)

    for _ in range(2):
        response = client.post(
            "/api/v1/teams/project-team/projects/Lifecycle Project/archive",
            headers=_headers(admin_token),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "archived"

    for _ in range(2):
        response = client.post(
            "/api/v1/teams/project-team/projects/Lifecycle Project/restore",
            headers=_headers(admin_token),
        )
        assert response.status_code == 200
        assert response.json()["status"] == "active"
