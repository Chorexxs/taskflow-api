"""Permission matrix across every endpoint (T-043).

Each test starts from the same world: an admin/creator, a regular member and an
outsider. The assertions encode the matrix in `AGENTS.md` and
`specs/taskflow/spec.md`.
"""

import pytest
from fastapi.testclient import TestClient

from app import models


def _headers(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


def _register_and_login(client: TestClient, email: str) -> dict:
    register = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "password123"}
    )
    assert register.status_code == 201, register.text
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    payload["id"] = register.json()["id"]
    payload["email"] = email
    return payload


@pytest.fixture
def world(client: TestClient, tmp_path, monkeypatch):
    from app.config import settings
    from app.routers import attachments as attachments_module

    monkeypatch.setattr(attachments_module, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")

    admin = _register_and_login(client, "matrix-admin@example.com")
    member = _register_and_login(client, "matrix-member@example.com")
    outsider = _register_and_login(client, "matrix-outsider@example.com")

    assert client.post(
        "/api/v1/teams/",
        json={"name": "Matrix", "slug": "matrix"},
        headers=_headers(admin["access_token"]),
    ).status_code == 201
    assert client.post(
        "/api/v1/teams/matrix/members",
        json={"email": member["email"], "role": "member"},
        headers=_headers(admin["access_token"]),
    ).status_code == 201

    project = client.post(
        "/api/v1/teams/matrix/projects/",
        json={"name": "Matrix Project"},
        headers=_headers(admin["access_token"]),
    ).json()
    task = client.post(
        "/api/v1/teams/matrix/projects/Matrix Project/tasks/",
        json={"title": "Matrix Task"},
        headers=_headers(admin["access_token"]),
    ).json()

    comment = client.post(
        "/api/v1/teams/matrix/projects/Matrix Project/tasks/Matrix Task/comments/",
        json={"content": "member comment"},
        headers=_headers(member["access_token"]),
    ).json()
    attachment = client.post(
        "/api/v1/teams/matrix/projects/Matrix Project/tasks/Matrix Task/attachments/",
        files={"file": ("matrix.txt", b"payload", "text/plain")},
        headers=_headers(member["access_token"]),
    ).json()

    assert client.post(
        "/api/v1/teams/",
        json={"name": "Other Matrix", "slug": "other-matrix"},
        headers=_headers(admin["access_token"]),
    ).status_code == 201
    other_project = client.post(
        "/api/v1/teams/other-matrix/projects/",
        json={"name": "Other Project"},
        headers=_headers(admin["access_token"]),
    ).json()
    other_task = client.post(
        "/api/v1/teams/other-matrix/projects/Other Project/tasks/",
        json={"title": "Other Task"},
        headers=_headers(admin["access_token"]),
    ).json()

    return {
        "admin": admin,
        "member": member,
        "outsider": outsider,
        "project": project,
        "task": task,
        "comment": comment,
        "attachment": attachment,
        "other_project": other_project,
        "other_task": other_task,
    }


def _task_url(world, suffix=""):
    return (
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{world['task']['id']}{suffix}"
    )


def _comment_url(world, comment_id):
    return (
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{world['task']['id']}/comments/{comment_id}"
    )


def _attachment_url(world, attachment_id):
    return (
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{world['task']['id']}/attachments/{attachment_id}"
    )


# ---------------------------------------------------------------------------
# Authentication and users
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("GET", "/api/v1/users/me"),
        ("PUT", "/api/v1/users/me"),
        ("GET", "/api/v1/teams/"),
        ("POST", "/api/v1/teams/"),
        ("GET", "/api/v1/teams/matrix"),
        ("PATCH", "/api/v1/teams/matrix"),
        ("DELETE", "/api/v1/teams/matrix/members/1"),
    ],
)
def test_protected_endpoints_require_token(client, method, path):
    response = client.request(method, path, json={})
    assert response.status_code == 401
    assert response.headers.get("WWW-Authenticate") == "Bearer"


def test_outsider_cannot_read_team(client, world):
    response = client.get(
        "/api/v1/teams/matrix", headers=_headers(world["outsider"]["access_token"])
    )
    assert response.status_code == 403

    missing = client.get(
        "/api/v1/teams/does-not-exist", headers=_headers(world["member"]["access_token"])
    )
    assert missing.status_code == 404


def test_only_admin_can_edit_team(client, world):
    assert client.patch(
        "/api/v1/teams/matrix",
        json={"name": "Nope"},
        headers=_headers(world["member"]["access_token"]),
    ).status_code == 403
    assert client.patch(
        "/api/v1/teams/matrix",
        json={"name": "Matrix"},
        headers=_headers(world["admin"]["access_token"]),
    ).status_code == 200


def test_only_admin_can_manage_members(client, world):
    assert client.post(
        "/api/v1/teams/matrix/members",
        json={"email": world["outsider"]["email"], "role": "member"},
        headers=_headers(world["member"]["access_token"]),
    ).status_code == 403
    assert client.post(
        "/api/v1/teams/matrix/members",
        json={"email": world["outsider"]["email"], "role": "member"},
        headers=_headers(world["admin"]["access_token"]),
    ).status_code == 201
    assert client.patch(
        f"/api/v1/teams/matrix/members/{world['outsider']['id']}",
        json={"role": "admin"},
        headers=_headers(world["member"]["access_token"]),
    ).status_code == 403
    assert client.delete(
        f"/api/v1/teams/matrix/members/{world['outsider']['id']}",
        headers=_headers(world["member"]["access_token"]),
    ).status_code == 403


def test_last_admin_cannot_leave_team(client, world):
    response = client.delete(
        f"/api/v1/teams/matrix/members/{world['admin']['id']}",
        headers=_headers(world["admin"]["access_token"]),
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


def test_project_permissions(client, world):
    member = _headers(world["member"]["access_token"])
    outsider = _headers(world["outsider"]["access_token"])
    admin = _headers(world["admin"]["access_token"])

    assert client.post(
        "/api/v1/teams/matrix/projects/", json={"name": "Member Project"}, headers=member
    ).status_code == 201
    assert client.post(
        "/api/v1/teams/matrix/projects/", json={"name": "Nope"}, headers=outsider
    ).status_code == 403

    assert client.get("/api/v1/teams/matrix/projects/", headers=member).status_code == 200
    assert client.get("/api/v1/teams/matrix/projects/", headers=outsider).status_code == 403

    project_url = f"/api/v1/teams/matrix/projects/{world['project']['id']}"
    assert client.get(project_url, headers=member).status_code == 200
    assert client.get(project_url, headers=outsider).status_code == 403
    assert client.get(
        "/api/v1/teams/matrix/projects/99999", headers=member
    ).status_code == 404

    assert client.patch(
        project_url, json={"name": "Matrix Project"}, headers=member
    ).status_code == 403
    assert client.patch(
        project_url, json={"name": "Matrix Project"}, headers=admin
    ).status_code == 200
    assert client.delete(project_url, headers=member).status_code == 403
    assert client.post(f"{project_url}/archive", headers=member).status_code == 403
    assert client.post(f"{project_url}/restore", headers=member).status_code == 403
    assert client.get(f"{project_url}/activity", headers=member).status_code == 200
    assert client.get(f"{project_url}/activity", headers=outsider).status_code == 403


def test_project_from_another_team_is_404(client, world):
    response = client.get(
        f"/api/v1/teams/matrix/projects/{world['other_project']['id']}",
        headers=_headers(world["member"]["access_token"]),
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


def test_task_permissions(client, world):
    member = _headers(world["member"]["access_token"])
    outsider = _headers(world["outsider"]["access_token"])
    admin = _headers(world["admin"]["access_token"])

    assert client.post(
        "/api/v1/teams/matrix/projects/Matrix Project/tasks/",
        json={"title": "Member Task"},
        headers=member,
    ).status_code == 201
    assert client.post(
        "/api/v1/teams/matrix/projects/Matrix Project/tasks/",
        json={"title": "Nope"},
        headers=outsider,
    ).status_code == 403

    assert client.get(
        "/api/v1/teams/matrix/projects/Matrix Project/tasks/", headers=member
    ).status_code == 200
    assert client.get(
        "/api/v1/teams/matrix/projects/Matrix Project/tasks/", headers=outsider
    ).status_code == 403

    assert client.get(_task_url(world), headers=member).status_code == 200
    assert client.get(_task_url(world), headers=outsider).status_code == 403
    assert client.get(
        _task_url(world).replace(str(world["task"]["id"]), "99999"), headers=member
    ).status_code == 404

    # A member may move the task but cannot edit its title.
    assert client.patch(
        _task_url(world), json={"title": "Hijacked"}, headers=member
    ).status_code == 403
    assert client.patch(
        _task_url(world), json={"status": "in_progress"}, headers=member
    ).status_code == 200
    assert client.patch(
        _task_url(world, "/status"), json={"status": "done"}, headers=member
    ).status_code == 200
    assert client.patch(
        _task_url(world, "/status"), json={"status": "done"}, headers=outsider
    ).status_code == 403

    assert client.patch(
        _task_url(world, "/assign"),
        json={"user_id": world["member"]["id"]},
        headers=member,
    ).status_code == 403
    assert client.patch(
        _task_url(world, "/assign"),
        json={"user_id": world["member"]["id"]},
        headers=admin,
    ).status_code == 200

    assert client.delete(_task_url(world), headers=member).status_code == 403
    assert client.delete(_task_url(world), headers=admin).status_code == 204


def test_task_from_another_team_is_404(client, world):
    response = client.get(
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{world['other_task']['id']}",
        headers=_headers(world["member"]["access_token"]),
    )
    assert response.status_code == 404


def test_creator_can_assign_even_without_being_admin(client, world):
    member = _headers(world["member"]["access_token"])
    task = client.post(
        "/api/v1/teams/matrix/projects/Matrix Project/tasks/",
        json={"title": "Member Owned"},
        headers=member,
    ).json()

    response = client.patch(
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{task['id']}/assign",
        json={"user_id": world["member"]["id"]},
        headers=member,
    )

    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# Comments
# ---------------------------------------------------------------------------


def test_comment_permissions(client, world):
    member = _headers(world["member"]["access_token"])
    outsider = _headers(world["outsider"]["access_token"])
    admin = _headers(world["admin"]["access_token"])

    assert client.post(
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{world['task']['id']}/comments/",
        json={"content": "Nope"},
        headers=outsider,
    ).status_code == 403
    assert client.get(
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{world['task']['id']}/comments/",
        headers=member,
    ).status_code == 200
    assert client.get(
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{world['task']['id']}/comments/",
        headers=outsider,
    ).status_code == 403

    url = _comment_url(world, world["comment"]["id"])
    assert client.patch(
        url, json={"content": "edited"}, headers=member
    ).status_code == 200
    assert client.patch(
        url, json={"content": "admin edit"}, headers=admin
    ).status_code == 403
    assert client.patch(
        url, json={"content": "outside edit"}, headers=outsider
    ).status_code == 403

    # A second member comment owned by the admin can be deleted by the member?
    admin_comment = client.post(
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{world['task']['id']}/comments/",
        json={"content": "admin comment"},
        headers=admin,
    ).json()
    admin_url = _comment_url(world, admin_comment["id"])
    assert client.delete(admin_url, headers=member).status_code == 403
    assert client.delete(admin_url, headers=admin).status_code == 204
    assert client.delete(url, headers=member).status_code == 204


def test_comment_from_another_task_is_404(client, world):
    url = (
        f"/api/v1/teams/matrix/projects/{world['other_project']['id']}"
        f"/tasks/{world['other_task']['id']}/comments/{world['comment']['id']}"
    )
    response = client.delete(url, headers=_headers(world["admin"]["access_token"]))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Attachments and notifications
# ---------------------------------------------------------------------------


def test_attachment_permissions(client, world):
    member = _headers(world["member"]["access_token"])
    outsider = _headers(world["outsider"]["access_token"])
    admin = _headers(world["admin"]["access_token"])
    base = (
        f"/api/v1/teams/matrix/projects/{world['project']['id']}"
        f"/tasks/{world['task']['id']}/attachments/"
    )

    assert client.get(base, headers=member).status_code == 200
    assert client.get(base, headers=outsider).status_code == 403
    assert client.post(
        base,
        files={"file": ("outside.txt", b"payload", "text/plain")},
        headers=outsider,
    ).status_code == 403

    download = f"{_attachment_url(world, world['attachment']['id'])}/download"
    assert client.get(download, headers=member).status_code == 200
    assert client.get(download, headers=outsider).status_code == 403

    second = client.post(
        base,
        files={"file": ("admin.txt", b"payload", "text/plain")},
        headers=admin,
    ).json()
    assert client.delete(
        _attachment_url(world, second["id"]), headers=member
    ).status_code == 403
    assert client.delete(
        _attachment_url(world, second["id"]), headers=admin
    ).status_code == 204
    assert client.delete(
        _attachment_url(world, world["attachment"]["id"]), headers=member
    ).status_code == 204


def test_notifications_are_private(client, world, db_session):
    member = _headers(world["member"]["access_token"])
    admin = world["admin"]

    assert client.get("/api/v1/notifications/", headers=member).status_code == 200
    assert client.get("/api/v1/notifications/unread-count", headers=member).status_code == 200

    notification = models.Notification(
        user_id=admin["id"],
        type="assigned",
        entity_type="task",
        entity_id=world["task"]["id"],
        message="Assigned to you",
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)

    assert client.patch(
        f"/api/v1/notifications/{notification.id}/read", headers=member
    ).status_code == 403
