"""Idempotent POST handling for critical resources (T-100)."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import models, schemas
from app.idempotency import IdempotencyGuard, request_fingerprint


def _headers(token: str, key: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


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


def _setup_team(client: TestClient, owner: dict) -> None:
    response = client.post(
        "/api/v1/teams/",
        json={"name": "Idempotent Team", "slug": "idempotent-team"},
        headers=_headers(owner["access_token"]),
    )
    assert response.status_code == 201, response.text


def test_team_creation_replays_the_first_response(client: TestClient):
    owner = _register_and_login(client, "idem-team@example.com")
    payload = {"name": "Retry Team", "slug": "retry-team"}

    first = client.post(
        "/api/v1/teams/",
        json=payload,
        headers=_headers(owner["access_token"], "team-key-1"),
    )
    second = client.post(
        "/api/v1/teams/",
        json=payload,
        headers=_headers(owner["access_token"], "team-key-1"),
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert second.json() == first.json()
    assert second.headers["Idempotent-Replayed"] == "true"

    teams = client.get("/api/v1/teams/", headers=_headers(owner["access_token"])).json()["items"]
    assert sum(1 for team in teams if team["slug"] == "retry-team") == 1


def test_same_key_with_a_different_payload_is_rejected(client: TestClient):
    owner = _register_and_login(client, "idem-mismatch@example.com")
    first = client.post(
        "/api/v1/teams/",
        json={"name": "Original", "slug": "original-team"},
        headers=_headers(owner["access_token"], "mismatch-key"),
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/teams/",
        json={"name": "Changed", "slug": "changed-team"},
        headers=_headers(owner["access_token"], "mismatch-key"),
    )

    assert second.status_code == 422
    assert "different request" in second.json()["detail"]


def test_keys_are_scoped_per_user(client: TestClient):
    alice = _register_and_login(client, "idem-alice@example.com")
    bob = _register_and_login(client, "idem-bob@example.com")

    first = client.post(
        "/api/v1/teams/",
        json={"name": "Alice Team", "slug": "alice-team"},
        headers=_headers(alice["access_token"], "shared-key"),
    )
    second = client.post(
        "/api/v1/teams/",
        json={"name": "Bob Team", "slug": "bob-team"},
        headers=_headers(bob["access_token"], "shared-key"),
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert "Idempotent-Replayed" not in second.headers
    assert second.json()["slug"] == "bob-team"


def test_project_task_and_comment_creations_are_idempotent(client: TestClient):
    owner = _register_and_login(client, "idem-flow@example.com")
    _setup_team(client, owner)
    auth = _headers(owner["access_token"])

    project_payload = {"name": "Idempotent Project"}
    project = client.post(
        "/api/v1/teams/idempotent-team/projects/",
        json=project_payload,
        headers=_headers(owner["access_token"], "project-key"),
    )
    assert project.status_code == 201, project.text
    project_replay = client.post(
        "/api/v1/teams/idempotent-team/projects/",
        json=project_payload,
        headers=_headers(owner["access_token"], "project-key"),
    )
    assert project_replay.headers["Idempotent-Replayed"] == "true"
    assert project_replay.json() == project.json()

    task_payload = {"title": "Idempotent Task"}
    task = client.post(
        "/api/v1/teams/idempotent-team/projects/Idempotent Project/tasks/",
        json=task_payload,
        headers=_headers(owner["access_token"], "task-key"),
    )
    assert task.status_code == 201, task.text
    task_replay = client.post(
        "/api/v1/teams/idempotent-team/projects/Idempotent Project/tasks/",
        json=task_payload,
        headers=_headers(owner["access_token"], "task-key"),
    )
    assert task_replay.headers["Idempotent-Replayed"] == "true"
    assert task_replay.json() == task.json()

    task_id = task.json()["id"]
    comment_payload = {"content": "Idempotent comment"}
    comment_url = (
        f"/api/v1/teams/idempotent-team/projects/Idempotent Project/tasks/{task_id}/comments/"
    )
    comment = client.post(
        comment_url,
        json=comment_payload,
        headers=_headers(owner["access_token"], "comment-key"),
    )
    assert comment.status_code == 201, comment.text
    comment_replay = client.post(
        comment_url,
        json=comment_payload,
        headers=_headers(owner["access_token"], "comment-key"),
    )
    assert comment_replay.headers["Idempotent-Replayed"] == "true"
    assert comment_replay.json() == comment.json()

    comments = client.get(comment_url, headers=auth).json()["items"]
    assert len(comments) == 1
    tasks = client.get(
        "/api/v1/teams/idempotent-team/projects/Idempotent Project/tasks/",
        headers=auth,
    ).json()["items"]
    assert len(tasks) == 1


def test_attachment_upload_is_idempotent(client: TestClient):
    owner = _register_and_login(client, "idem-upload@example.com")
    _setup_team(client, owner)
    auth = _headers(owner["access_token"])
    project = client.post(
        "/api/v1/teams/idempotent-team/projects/",
        json={"name": "Upload Project"},
        headers=auth,
    )
    assert project.status_code == 201, project.text
    task = client.post(
        "/api/v1/teams/idempotent-team/projects/Upload Project/tasks/",
        json={"title": "Upload Task"},
        headers=auth,
    )
    assert task.status_code == 201, task.text
    url = (
        "/api/v1/teams/idempotent-team/projects/Upload Project"
        f"/tasks/{task.json()['id']}/attachments/"
    )
    files = {"file": ("note.txt", b"idempotent bytes", "text/plain")}

    first = client.post(url, files=files, headers=_headers(owner["access_token"], "upload-key"))
    second = client.post(url, files=files, headers=_headers(owner["access_token"], "upload-key"))

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert second.headers["Idempotent-Replayed"] == "true"
    assert second.json() == first.json()
    listed = client.get(url, headers=auth).json()["items"]
    assert len(listed) == 1


def test_a_failed_request_releases_the_key(client: TestClient):
    owner = _register_and_login(client, "idem-release@example.com")
    outsider = _register_and_login(client, "idem-outsider@example.com")
    _setup_team(client, owner)
    assert (
        client.post(
            "/api/v1/teams/idempotent-team/projects/",
            json={"name": "Release Project"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    outsider_id = client.get("/api/v1/users/me", headers=_headers(outsider["access_token"])).json()[
        "id"
    ]
    url = "/api/v1/teams/idempotent-team/projects/Release Project/tasks/"

    invalid = client.post(
        url,
        json={"title": "Invalid assignment", "assigned_to": outsider_id},
        headers=_headers(owner["access_token"], "release-key"),
    )
    assert invalid.status_code == 400

    retry = client.post(
        url,
        json={"title": "Valid retry"},
        headers=_headers(owner["access_token"], "release-key"),
    )

    assert retry.status_code == 201, retry.text
    assert "Idempotent-Replayed" not in retry.headers
    assert retry.json()["title"] == "Valid retry"


def test_in_flight_request_returns_conflict(client: TestClient, db_session):
    owner = _register_and_login(client, "idem-busy@example.com")
    user_id = client.get("/api/v1/users/me", headers=_headers(owner["access_token"])).json()["id"]
    payload = {"name": "Busy Team", "slug": "busy-team"}
    db_session.add(
        models.IdempotencyKey(
            user_id=user_id,
            key="busy-key",
            method="POST",
            path="/api/v1/teams/",
            request_hash=request_fingerprint(
                "POST", "/api/v1/teams/", schemas.TeamCreate(**payload)
            ),
            created_at=datetime.now(timezone.utc),
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/teams/",
        json=payload,
        headers=_headers(owner["access_token"], "busy-key"),
    )

    assert response.status_code == 409


def test_stale_in_flight_reservation_is_taken_over(client: TestClient, db_session):
    owner = _register_and_login(client, "idem-stale@example.com")
    user_id = client.get("/api/v1/users/me", headers=_headers(owner["access_token"])).json()["id"]
    payload = {"name": "Stale Team", "slug": "stale-team"}
    db_session.add(
        models.IdempotencyKey(
            user_id=user_id,
            key="stale-key",
            method="POST",
            path="/api/v1/teams/",
            request_hash=request_fingerprint(
                "POST", "/api/v1/teams/", schemas.TeamCreate(**payload)
            ),
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/teams/",
        json=payload,
        headers=_headers(owner["access_token"], "stale-key"),
    )

    assert response.status_code == 201, response.text
    record = (
        db_session.query(models.IdempotencyKey)
        .filter(models.IdempotencyKey.key == "stale-key")
        .one()
    )
    assert record.status_code == 201
    assert record.completed_at is not None


def test_invalid_key_is_rejected(client: TestClient):
    owner = _register_and_login(client, "idem-invalid@example.com")

    response = client.post(
        "/api/v1/teams/",
        json={"name": "Invalid Key Team", "slug": "invalid-key-team"},
        headers=_headers(owner["access_token"], "bad key with spaces"),
    )

    assert response.status_code == 400


def test_release_discards_uncommitted_business_changes(db_session):
    """A failed idempotent request must not persist half-written rows."""
    user = models.User(
        email="idem-release@example.com",
        hashed_password="not-used",
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    db_session.commit()

    guard = IdempotencyGuard(
        db=db_session,
        user_id=user.id,
        key="release-key",
        method="POST",
        path="/api/v1/teams/",
    )
    guard.replay({})
    assert guard.record is not None

    # Business work flushed but not committed yet, like create_task(commit=False).
    db_session.add(models.Team(name="Half written", slug="half-written", created_by=user.id))
    db_session.flush()

    guard.release()

    assert db_session.query(models.Team).filter_by(slug="half-written").first() is None
    assert (
        db_session.query(models.IdempotencyKey).filter_by(key="release-key").first() is None
    )
