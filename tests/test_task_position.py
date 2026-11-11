"""Stable Kanban ordering (FR-TASK-08 / M-05, T-096)."""

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


def _setup(client: TestClient, titles: list[str]):
    owner = _register_and_login(client, "position-owner@example.com")
    assert (
        client.post(
            "/api/v1/teams/",
            json={"name": "Position Team", "slug": "position-team"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/position-team/projects/",
            json={"name": "Position Project"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )

    tasks = []
    for title in titles:
        response = client.post(
            "/api/v1/teams/position-team/projects/Position Project/tasks/",
            json={"title": title},
            headers=_headers(owner["access_token"]),
        )
        assert response.status_code == 201, response.text
        tasks.append(response.json())
    return owner, tasks


def _status_url(task_id: int) -> str:
    return f"/api/v1/teams/position-team/projects/Position Project/tasks/{task_id}/status"


def _list_tasks(client: TestClient, owner: dict) -> list[dict]:
    response = client.get(
        "/api/v1/teams/position-team/projects/Position Project/tasks/",
        params={"sort_by": "position", "order": "asc", "page_size": 100},
        headers=_headers(owner["access_token"]),
    )
    assert response.status_code == 200, response.text
    return response.json()["items"]


def test_new_tasks_are_appended_with_increasing_positions(client: TestClient):
    _, tasks = _setup(client, ["First", "Second", "Third"])

    positions = [task["position"] for task in tasks]
    assert positions == sorted(positions)
    assert len(set(positions)) == 3
    assert all(position > 0 for position in positions)


def test_tasks_can_be_listed_in_kanban_order(client: TestClient):
    owner, tasks = _setup(client, ["First", "Second", "Third"])

    items = _list_tasks(client, owner)

    assert [task["id"] for task in items] == [task["id"] for task in tasks]


def test_reorder_inside_the_same_column_is_persisted(client: TestClient, db_session):
    owner, tasks = _setup(client, ["First", "Second", "Third"])
    first, second, third = tasks

    response = client.patch(
        _status_url(third["id"]),
        json={
            "status": "todo",
            "position": (first["position"] + second["position"]) / 2,
        },
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 200, response.text
    moved = response.json()
    assert moved["status"] == "todo"
    assert first["position"] < moved["position"] < second["position"]

    items = _list_tasks(client, owner)
    assert [task["id"] for task in items] == [first["id"], third["id"], second["id"]]

    # Reordering is not a status change, so it must not pollute the activity log.
    assert (
        db_session.query(models.ActivityLog)
        .filter(models.ActivityLog.action == "updated_status")
        .count()
        == 0
    )


def test_moving_without_position_appends_to_the_destination_column(client: TestClient):
    owner, tasks = _setup(client, ["First", "Second"])
    first = tasks[0]

    response = client.patch(
        _status_url(first["id"]),
        json={"status": "in_progress"},
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 200, response.text
    moved = response.json()
    assert moved["status"] == "in_progress"
    assert moved["position"] == 1024


def test_moving_with_explicit_position_sets_status_and_position_atomically(
    client: TestClient, db_session
):
    owner, tasks = _setup(client, ["First"])
    task = tasks[0]

    response = client.patch(
        _status_url(task["id"]),
        json={"status": "done", "position": 42.5},
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 200, response.text
    moved = response.json()
    assert moved["status"] == "done"
    assert moved["position"] == 42.5

    stored = db_session.query(models.Task).filter(models.Task.id == task["id"]).one()
    assert stored.status == "done"
    assert float(stored.position) == 42.5
    assert (
        db_session.query(models.ActivityLog)
        .filter(models.ActivityLog.action == "updated_status")
        .count()
        == 1
    )


def test_position_out_of_range_is_rejected(client: TestClient):
    owner, tasks = _setup(client, ["First"])

    response = client.patch(
        _status_url(tasks[0]["id"]),
        json={"status": "done", "position": 1e12},
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 422
