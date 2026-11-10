"""Task deletion must clean up attachment files and audit the action."""

from fastapi.testclient import TestClient


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup_task(client: TestClient):
    client.post(
        "/api/v1/auth/register", json={"email": "task-life@example.com", "password": "password123"}
    )
    token = client.post(
        "/api/v1/auth/login",
        data={"username": "task-life@example.com", "password": "password123"},
    ).json()["access_token"]
    assert (
        client.post(
            "/api/v1/teams/",
            json={"name": "Task Life", "slug": "task-life"},
            headers=_headers(token),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/task-life/projects/",
            json={"name": "Task Project"},
            headers=_headers(token),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/task-life/projects/Task Project/tasks/",
            json={"title": "Task With File"},
            headers=_headers(token),
        ).status_code
        == 201
    )
    return token


def test_deleting_task_removes_attachment_files(
    client: TestClient, db_session, tmp_path, monkeypatch
):
    from app.config import settings
    from app.routers import attachments as attachments_module

    monkeypatch.setattr(attachments_module, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    token = _setup_task(client)

    upload = client.post(
        "/api/v1/teams/task-life/projects/Task Project/tasks/Task With File/attachments/",
        files={"file": ("evidence.txt", b"payload", "text/plain")},
        headers=_headers(token),
    )
    assert upload.status_code == 201, upload.text
    stored_files = [path for path in tmp_path.rglob("*") if path.is_file()]
    assert len(stored_files) == 1

    deleted = client.delete(
        "/api/v1/teams/task-life/projects/Task Project/tasks/Task With File",
        headers=_headers(token),
    )
    assert deleted.status_code == 204

    assert [path for path in tmp_path.rglob("*") if path.is_file()] == []

    from app import models

    deleted_logs = (
        db_session.query(models.ActivityLog)
        .filter(
            models.ActivityLog.entity_type == "task",
            models.ActivityLog.action == "deleted",
        )
        .all()
    )
    assert len(deleted_logs) == 1
