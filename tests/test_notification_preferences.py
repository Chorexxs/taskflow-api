"""Notification preferences and per-event deduplication (T-058)."""

from fastapi.testclient import TestClient

from app import crud, models


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
    payload = response.json()
    payload["id"] = client.get(
        "/api/v1/users/me", headers=_headers(payload["access_token"])
    ).json()["id"]
    return payload


def _setup(client: TestClient):
    owner = _register_and_login(client, "prefs-owner@example.com")
    member = _register_and_login(client, "prefs-member@example.com")
    assert (
        client.post(
            "/api/v1/teams/",
            json={"name": "Prefs", "slug": "prefs"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/prefs/members",
            json={"email": "prefs-member@example.com", "role": "member"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/prefs/projects/",
            json={"name": "Prefs Project"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    task = client.post(
        "/api/v1/teams/prefs/projects/Prefs Project/tasks/",
        json={"title": "Prefs Task", "assigned_to": member["id"]},
        headers=_headers(owner["access_token"]),
    )
    assert task.status_code == 201, task.text
    return owner, member, task.json()


def _assign(client: TestClient, token: str, task_id: int, user_id: int | None):
    return client.patch(
        f"/api/v1/teams/prefs/projects/Prefs Project/tasks/{task_id}/assign",
        json={"user_id": user_id},
        headers=_headers(token),
    )


def test_muted_type_does_not_create_notifications(client: TestClient, db_session):
    owner, member, task = _setup(client)

    assert _assign(client, owner["access_token"], task["id"], owner["id"]).status_code == 200
    muted = client.put(
        "/api/v1/users/me/notification-preferences",
        json={"muted_types": ["assigned"]},
        headers=_headers(member["access_token"]),
    )
    assert muted.status_code == 200
    assert muted.json() == {"muted_types": ["assigned"]}

    assert _assign(client, owner["access_token"], task["id"], member["id"]).status_code == 200
    assert (
        db_session.query(models.Notification)
        .filter(
            models.Notification.user_id == member["id"],
            models.Notification.type == "assigned",
        )
        .count()
        == 0
    )

    # Unmuting restores delivery.
    client.put(
        "/api/v1/users/me/notification-preferences",
        json={"muted_types": []},
        headers=_headers(member["access_token"]),
    )
    _assign(client, owner["access_token"], task["id"], owner["id"])
    assert _assign(client, owner["access_token"], task["id"], member["id"]).status_code == 200

    assert (
        db_session.query(models.Notification)
        .filter(
            models.Notification.user_id == member["id"],
            models.Notification.type == "assigned",
        )
        .count()
        == 1
    )

    fetched = client.get(
        "/api/v1/users/me/notification-preferences",
        headers=_headers(member["access_token"]),
    )
    assert fetched.json() == {"muted_types": []}


def test_invalid_preference_type_is_rejected(client: TestClient):
    owner, _, _ = _setup(client)

    response = client.put(
        "/api/v1/users/me/notification-preferences",
        json={"muted_types": ["everything"]},
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 422


def test_dedupe_key_makes_notification_creation_idempotent(client: TestClient, db_session):
    owner, member, task = _setup(client)
    db_session.query(models.Notification).delete()
    db_session.commit()

    first = crud.create_notification(
        db_session,
        user_id=member["id"],
        notification_type="assigned",
        entity_type="task",
        entity_id=task["id"],
        message="Assigned",
        dedupe_key=f"assigned:{task['id']}:{member['id']}",
    )
    second = crud.create_notification(
        db_session,
        user_id=member["id"],
        notification_type="assigned",
        entity_type="task",
        entity_id=task["id"],
        message="Assigned again",
        dedupe_key=f"assigned:{task['id']}:{member['id']}",
    )

    assert first.id == second.id
    assert db_session.query(models.Notification).count() == 1
