"""Removing a team member unassigns their tasks (T-042)."""

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
    payload = response.json()
    payload["id"] = client.get(
        "/api/v1/users/me", headers=_headers(payload["access_token"])
    ).json()["id"]
    return payload


def test_removed_member_tasks_are_unassigned_and_audited(client: TestClient, db_session):
    owner = _register_and_login(client, "removal-owner@example.com")
    member = _register_and_login(client, "removal-member@example.com")

    assert (
        client.post(
            "/api/v1/teams/",
            json={"name": "Removal Team", "slug": "removal-team"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/removal-team/members",
            json={"email": "removal-member@example.com", "role": "member"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/removal-team/projects/",
            json={"name": "Removal Project"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    task = client.post(
        "/api/v1/teams/removal-team/projects/Removal Project/tasks/",
        json={"title": "Assigned Work", "assigned_to": member["id"]},
        headers=_headers(owner["access_token"]),
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]
    assert task.json()["assigned_to"] == member["id"]

    removed = client.delete(
        f"/api/v1/teams/removal-team/members/{member['id']}",
        headers=_headers(owner["access_token"]),
    )
    assert removed.status_code == 204

    after = client.get(
        f"/api/v1/teams/removal-team/projects/Removal Project/tasks/{task_id}",
        headers=_headers(owner["access_token"]),
    )
    assert after.status_code == 200
    assert after.json()["assigned_to"] is None

    log = (
        db_session.query(models.ActivityLog)
        .filter(
            models.ActivityLog.entity_type == "task",
            models.ActivityLog.entity_id == task_id,
            models.ActivityLog.action == "unassigned",
        )
        .one()
    )
    assert log.changed_by == owner["id"]

    forbidden = client.get(
        "/api/v1/teams/removal-team",
        headers=_headers(member["access_token"]),
    )
    assert forbidden.status_code == 403
