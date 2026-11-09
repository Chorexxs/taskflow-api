"""Regression tests for the P1 security and correctness fixes.

These tests intentionally cover the failure modes found in the baseline:
refresh-token transport/rotation, logout revocation, team-admin removal,
Kanban status permissions, assignee validation and upload hardening.
"""

import pytest
from fastapi.testclient import TestClient

from app.config import Settings


def _register_and_login(client: TestClient, email: str, password: str = "password123") -> dict:
    register = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register.status_code == 201, register.text
    login = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return login.json()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_hierarchy(
    client: TestClient,
    owner_email: str = "owner@example.com",
    member_email: str | None = None,
    task_title: str = "Secure Task",
):
    owner = _register_and_login(client, owner_email)
    slug = "secure-team"
    project_name = "Secure Project"

    assert client.post(
        "/api/v1/teams/",
        json={"name": "Secure Team", "slug": slug},
        headers=_headers(owner["access_token"]),
    ).status_code == 201
    assert client.post(
        f"/api/v1/teams/{slug}/projects/",
        json={"name": project_name},
        headers=_headers(owner["access_token"]),
    ).status_code == 201
    assert client.post(
        f"/api/v1/teams/{slug}/projects/{project_name}/tasks/",
        json={"title": task_title},
        headers=_headers(owner["access_token"]),
    ).status_code == 201

    member = None
    if member_email:
        member = _register_and_login(client, member_email)
        response = client.post(
            f"/api/v1/teams/{slug}/members",
            json={"email": member_email, "role": "member"},
            headers=_headers(owner["access_token"]),
        )
        assert response.status_code == 201, response.text

    return owner, member, slug, project_name, task_title


# ---------------------------------------------------------------------------
# Refresh / logout
# ---------------------------------------------------------------------------


def test_refresh_accepts_json_body_and_rotates_tokens(client: TestClient):
    tokens = _register_and_login(client, "refresh@example.com")
    old_refresh = tokens["refresh_token"]

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )

    assert response.status_code == 200, response.text
    new_tokens = response.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"] != old_refresh

    # The old refresh token has been rotated and cannot be reused.
    reuse = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert reuse.status_code == 401


def test_refresh_requires_a_token(client: TestClient):
    response = client.post("/api/v1/auth/refresh", json={})
    assert response.status_code == 422


def test_refresh_rejects_an_access_token(client: TestClient):
    tokens = _register_and_login(client, "wrongtype@example.com")

    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},
    )
    assert response.status_code == 401


def test_logout_revokes_refresh_token_and_is_idempotent(client: TestClient):
    tokens = _register_and_login(client, "logout@example.com")

    response = client.post(
        "/api/v1/auth/logout",
        headers=_headers(tokens["access_token"]),
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 204

    refresh_after_logout = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_after_logout.status_code == 401

    # Logout must not fail just because the tokens were already revoked.
    repeated = client.post(
        "/api/v1/auth/logout",
        headers=_headers(tokens["access_token"]),
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert repeated.status_code == 204


def test_logout_without_tokens_is_rejected(client: TestClient):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Team membership authorization
# ---------------------------------------------------------------------------


def test_member_cannot_remove_admin(client: TestClient):
    owner, member, slug, _, _ = _create_hierarchy(
        client,
        owner_email="admin-owner@example.com",
        member_email="plain-member@example.com",
    )

    response = client.delete(
        f"/api/v1/teams/{slug}/members/1",
        headers=_headers(member["access_token"]),
    )
    assert response.status_code == 403

    # The admin is still a member.
    assert client.get(
        f"/api/v1/teams/{slug}",
        headers=_headers(owner["access_token"]),
    ).status_code == 200


def test_member_cannot_remove_another_member(client: TestClient):
    owner, member_a, slug, _, _ = _create_hierarchy(
        client,
        owner_email="admin-owner2@example.com",
        member_email="member-a@example.com",
    )
    member_b = _register_and_login(client, "member-b@example.com")
    assert client.post(
        f"/api/v1/teams/{slug}/members",
        json={"email": "member-b@example.com", "role": "member"},
        headers=_headers(owner["access_token"]),
    ).status_code == 201

    response = client.delete(
        f"/api/v1/teams/{slug}/members/3",
        headers=_headers(member_a["access_token"]),
    )
    assert response.status_code == 403

    # Member B is still in the team.
    assert client.get(
        f"/api/v1/teams/{slug}/members",
        headers=_headers(member_b["access_token"]),
    ).status_code == 200


def test_last_admin_cannot_leave_the_team(client: TestClient):
    owner, _, slug, _, _ = _create_hierarchy(
        client,
        owner_email="last-admin@example.com",
    )

    response = client.delete(
        f"/api/v1/teams/{slug}/members/1",
        headers=_headers(owner["access_token"]),
    )
    assert response.status_code == 409


# ---------------------------------------------------------------------------
# Task permissions and assignment validation
# ---------------------------------------------------------------------------


def test_member_can_change_only_task_status(client: TestClient):
    owner, member, slug, project, task = _create_hierarchy(
        client,
        owner_email="task-admin@example.com",
        member_email="task-member@example.com",
    )
    url = f"/api/v1/teams/{slug}/projects/{project}/tasks/{task}"

    moved = client.patch(
        url,
        json={"status": "in_progress"},
        headers=_headers(member["access_token"]),
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["status"] == "in_progress"

    forbidden = client.patch(
        url,
        json={"title": "Hijacked title"},
        headers=_headers(member["access_token"]),
    )
    assert forbidden.status_code == 403

    mixed = client.patch(
        url,
        json={"status": "done", "title": "Hijacked title"},
        headers=_headers(member["access_token"]),
    )
    assert mixed.status_code == 403


def test_task_creation_rejects_non_member_assignee(client: TestClient):
    owner, _, slug, project, _ = _create_hierarchy(
        client,
        owner_email="assignee-owner@example.com",
    )
    outsider = _register_and_login(client, "assignee-outsider@example.com")

    response = client.post(
        f"/api/v1/teams/{slug}/projects/{project}/tasks/",
        json={"title": "Invalid assignment", "assigned_to": 2},
        headers=_headers(owner["access_token"]),
    )
    assert response.status_code == 400
    assert outsider["access_token"]


# ---------------------------------------------------------------------------
# Upload hardening
# ---------------------------------------------------------------------------


@pytest.fixture()
def upload_dir(tmp_path, monkeypatch):
    from app.routers import attachments as attachments_module

    monkeypatch.setattr(attachments_module, "UPLOAD_DIR", str(tmp_path))
    return tmp_path


def _attachments_url(slug: str = "secure-team", project: str = "Secure Project", task: str = "Secure Task"):
    return f"/api/v1/teams/{slug}/projects/{project}/tasks/{task}/attachments/"


def test_upload_sanitizes_path_traversal(client: TestClient, upload_dir):
    owner, _, _, _, _ = _create_hierarchy(
        client,
        owner_email="traversal@example.com",
    )

    response = client.post(
        _attachments_url(),
        files={"file": ("../../evil.txt", b"content", "text/plain")},
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["filename"] == "evil.txt"
    assert "file_path" not in payload

    stored_files = [path for path in upload_dir.rglob("*") if path.is_file()]
    assert len(stored_files) == 1
    assert upload_dir.resolve() in stored_files[0].resolve().parents


def test_upload_rejects_disallowed_extension(client: TestClient, upload_dir):
    owner, _, _, _, _ = _create_hierarchy(
        client,
        owner_email="blocked@example.com",
    )

    response = client.post(
        _attachments_url(),
        files={"file": ("payload.exe", b"not allowed", "application/x-msdownload")},
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 415
    assert not [path for path in upload_dir.rglob("*") if path.is_file()]


def test_upload_enforces_streaming_size_limit(client: TestClient, upload_dir, monkeypatch):
    from app.routers import attachments as attachments_module

    monkeypatch.setattr(attachments_module, "MAX_FILE_SIZE", 10)
    owner, _, _, _, _ = _create_hierarchy(
        client,
        owner_email="toolarge@example.com",
    )

    response = client.post(
        _attachments_url(),
        files={"file": ("large.txt", b"x" * 11, "text/plain")},
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 413
    assert not [path for path in upload_dir.rglob("*") if path.is_file()]


def test_duplicate_filenames_get_distinct_storage_keys(client: TestClient, upload_dir):
    owner, _, _, _, _ = _create_hierarchy(
        client,
        owner_email="duplicate@example.com",
    )

    for _ in range(2):
        response = client.post(
            _attachments_url(),
            files={"file": ("same.txt", b"content", "text/plain")},
            headers=_headers(owner["access_token"]),
        )
        assert response.status_code == 201, response.text

    stored_files = [path for path in upload_dir.rglob("*") if path.is_file()]
    assert len(stored_files) == 2

    listed = client.get(
        _attachments_url(),
        headers=_headers(owner["access_token"]),
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 2


# ---------------------------------------------------------------------------
# CORS and configuration
# ---------------------------------------------------------------------------


def test_cors_only_allows_configured_origins(client: TestClient):
    allowed = client.get("/", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"

    rejected = client.get("/", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in rejected.headers


def test_production_requires_a_secret_key():
    config = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="",
        DATABASE_URL="postgresql://user:pass@localhost/db",
    )

    with pytest.raises(RuntimeError):
        _ = config.secret_key


def test_development_uses_a_fallback_secret_key():
    config = Settings(
        ENVIRONMENT="development",
        SECRET_KEY="",
        DATABASE_URL="postgresql://user:pass@localhost/db",
    )

    assert config.secret_key
    assert config.secret_key != ""
