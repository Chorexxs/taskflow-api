"""Stable identifiers: id/slug for projects and id for tasks (T-036/T-037)."""

from fastapi.testclient import TestClient

from app.routers import projects as projects_router
from app.routers import tasks as tasks_router


class RecordingLogger:
    def __init__(self):
        self.events = []

    def warning(self, event, **kwargs):
        self.events.append((event, kwargs))

    def info(self, event, **kwargs):
        pass

    def error(self, event, **kwargs):
        pass


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: TestClient, email: str) -> dict:
    assert client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    ).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _setup(client: TestClient):
    owner = _register_and_login(client, "ids-owner@example.com")
    assert client.post(
        "/api/v1/teams/",
        json={"name": "Identifiers", "slug": "identifiers"},
        headers=_headers(owner["access_token"]),
    ).status_code == 201
    return owner


def _create_project(client: TestClient, token: str, name: str, slug: str | None = None):
    payload = {"name": name}
    if slug is not None:
        payload["slug"] = slug
    return client.post(
        "/api/v1/teams/identifiers/projects/",
        json=payload,
        headers=_headers(token),
    )


def test_project_slug_is_generated_and_deduplicated_per_team(client: TestClient):
    owner = _setup(client)

    first = _create_project(client, owner["access_token"], "Same Name")
    second = _create_project(client, owner["access_token"], "Same Name")

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["slug"] == "same-name"
    assert second.json()["slug"] == "same-name-2"

    by_id = client.get(
        f"/api/v1/teams/identifiers/projects/{first.json()['id']}",
        headers=_headers(owner["access_token"]),
    )
    by_slug = client.get(
        f"/api/v1/teams/identifiers/projects/{second.json()['slug']}",
        headers=_headers(owner["access_token"]),
    )
    assert by_id.status_code == 200
    assert by_slug.status_code == 200
    assert by_slug.json()["id"] == second.json()["id"]


def test_explicit_slug_is_normalized_and_unique(client: TestClient):
    owner = _setup(client)
    token = owner["access_token"]

    first = _create_project(client, token, "Website", slug="My Website!")
    assert first.status_code == 201, first.text
    assert first.json()["slug"] == "my-website"

    duplicate = _create_project(client, token, "Other", slug="my-website")
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


def test_same_slug_is_allowed_in_another_team(client: TestClient):
    owner = _setup(client)
    assert client.post(
        "/api/v1/teams/",
        json={"name": "Other Team", "slug": "other-identifiers"},
        headers=_headers(owner["access_token"]),
    ).status_code == 201

    assert _create_project(client, owner["access_token"], "Shared", slug="shared").status_code == 201
    response = client.post(
        "/api/v1/teams/other-identifiers/projects/",
        json={"name": "Shared", "slug": "shared"},
        headers=_headers(owner["access_token"]),
    )
    assert response.status_code == 201


def test_ambiguous_project_name_returns_409_and_warns(client: TestClient, monkeypatch):
    recorder = RecordingLogger()
    monkeypatch.setattr(projects_router, "logger", recorder)
    owner = _setup(client)
    _create_project(client, owner["access_token"], "Duplicate")
    _create_project(client, owner["access_token"], "Duplicate")

    response = client.get(
        "/api/v1/teams/identifiers/projects/Duplicate",
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 409
    assert recorder.events == []


def test_unique_legacy_project_name_still_works_with_warning(
    client: TestClient, monkeypatch
):
    recorder = RecordingLogger()
    monkeypatch.setattr(projects_router, "logger", recorder)
    owner = _setup(client)
    created = _create_project(client, owner["access_token"], "Legacy Name")
    assert created.status_code == 201

    response = client.get(
        "/api/v1/teams/identifiers/projects/Legacy Name",
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created.json()["id"]
    assert recorder.events[0][0] == "deprecated_project_name_lookup"


def test_duplicate_task_titles_return_409_and_id_lookup_works(
    client: TestClient, monkeypatch
):
    recorder = RecordingLogger()
    monkeypatch.setattr(tasks_router, "logger", recorder)
    owner = _setup(client)
    token = owner["access_token"]
    project = _create_project(client, token, "Tasks")
    assert project.status_code == 201
    project_id = project.json()["id"]

    created = []
    for _ in range(2):
        response = client.post(
            f"/api/v1/teams/identifiers/projects/{project_id}/tasks/",
            json={"title": "Duplicate Task"},
            headers=_headers(token),
        )
        assert response.status_code == 201, response.text
        created.append(response.json())

    ambiguous = client.get(
        f"/api/v1/teams/identifiers/projects/{project_id}/tasks/Duplicate Task",
        headers=_headers(token),
    )
    assert ambiguous.status_code == 409

    by_id = client.get(
        f"/api/v1/teams/identifiers/projects/{project_id}/tasks/{created[1]['id']}",
        headers=_headers(token),
    )
    assert by_id.status_code == 200
    assert by_id.json()["id"] == created[1]["id"]
    assert recorder.events == []
