"""Dedicated Kanban status endpoint (T-045)."""

from fastapi.testclient import TestClient

from app import models


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: TestClient, email: str) -> dict:
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
    return response.json()


def _setup(client: TestClient):
    owner = _register_and_login(client, "status-owner@example.com")
    member = _register_and_login(client, "status-member@example.com")

    assert (
        client.post(
            "/api/v1/teams/",
            json={"name": "Status Team", "slug": "status-team"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/status-team/members",
            json={"email": "status-member@example.com", "role": "member"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/status-team/projects/",
            json={"name": "Status Project"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    task = client.post(
        "/api/v1/teams/status-team/projects/Status Project/tasks/",
        json={"title": "Movable Task"},
        headers=_headers(owner["access_token"]),
    )
    assert task.status_code == 201, task.text
    return owner, member, task.json()


def _status_url(task_id: int) -> str:
    return f"/api/v1/teams/status-team/projects/Status Project/tasks/{task_id}/status"


def test_member_can_move_task_and_activity_is_logged(client: TestClient, db_session):
    _, member, task = _setup(client)

    response = client.patch(
        _status_url(task["id"]),
        json={"status": "in_progress"},
        headers=_headers(member["access_token"]),
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "in_progress"
    assert response.json()["title"] == task["title"]

    member_id = client.get("/api/v1/users/me", headers=_headers(member["access_token"])).json()[
        "id"
    ]
    log = (
        db_session.query(models.ActivityLog)
        .filter(
            models.ActivityLog.entity_type == "task",
            models.ActivityLog.entity_id == task["id"],
            models.ActivityLog.action == "updated_status",
        )
        .one()
    )
    assert log.changed_by == member_id
    assert log.old_value == "todo"
    assert log.new_value == "in_progress"


def test_status_endpoint_rejects_extra_fields(client: TestClient):
    owner, _, task = _setup(client)

    response = client.patch(
        _status_url(task["id"]),
        json={"status": "done", "title": "Hijacked"},
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 422
    detail = client.get(
        f"/api/v1/teams/status-team/projects/Status Project/tasks/{task['id']}",
        headers=_headers(owner["access_token"]),
    ).json()
    assert detail["title"] == "Movable Task"
    assert detail["status"] == "todo"


def test_status_endpoint_requires_team_membership(client: TestClient):
    _, _, task = _setup(client)
    outsider = _register_and_login(client, "status-outsider@example.com")

    response = client.patch(
        _status_url(task["id"]),
        json={"status": "done"},
        headers=_headers(outsider["access_token"]),
    )

    assert response.status_code == 403


def test_status_endpoint_requires_authentication(client: TestClient):
    _, _, task = _setup(client)

    response = client.patch(_status_url(task["id"]), json={"status": "done"})

    assert response.status_code == 401


def test_unknown_status_is_rejected(client: TestClient):
    owner, _, task = _setup(client)

    response = client.patch(
        _status_url(task["id"]),
        json={"status": "blocked"},
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 422
