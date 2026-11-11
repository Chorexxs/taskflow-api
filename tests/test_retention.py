"""Retention housekeeping for notifications and activity (Q-08, T-098)."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app import models
from app.jobs import purge_expired_data


def _user_id(client: TestClient) -> int:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": "retention@example.com", "password": "password123"},
        ).status_code
        == 201
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "retention@example.com", "password": "password123"},
    )
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    return client.get("/api/v1/users/me", headers=headers).json()["id"]


def _seed(db_session, user_id: int, now: datetime) -> tuple[int, int, int, int]:
    """Insert old and recent rows for both tables."""
    old_notification = models.Notification(
        user_id=user_id,
        type="assigned",
        entity_type="task",
        entity_id=1,
        message="old notification",
        created_at=now - timedelta(days=120),
    )
    fresh_notification = models.Notification(
        user_id=user_id,
        type="assigned",
        entity_type="task",
        entity_id=2,
        message="fresh notification",
        created_at=now - timedelta(days=10),
    )
    old_activity = models.ActivityLog(
        entity_type="task",
        entity_id=1,
        action="created",
        changed_by=user_id,
        created_at=now - timedelta(days=400),
    )
    fresh_activity = models.ActivityLog(
        entity_type="task",
        entity_id=2,
        action="created",
        changed_by=user_id,
        created_at=now - timedelta(days=30),
    )
    db_session.add_all([old_notification, fresh_notification, old_activity, fresh_activity])
    db_session.commit()
    for row in (old_notification, fresh_notification, old_activity, fresh_activity):
        db_session.refresh(row)
    return (
        old_notification.id,
        fresh_notification.id,
        old_activity.id,
        fresh_activity.id,
    )


def test_purge_deletes_only_rows_outside_the_retention_window(client: TestClient, db_session):
    now = datetime.now(timezone.utc)
    user_id = _user_id(client)
    old_notification, fresh_notification, old_activity, fresh_activity = _seed(
        db_session, user_id, now
    )

    counts = purge_expired_data(db_session, now=now)

    assert counts == {"notifications": 1, "activity": 1}
    remaining_notifications = {row.id for row in db_session.query(models.Notification).all()}
    remaining_activity = {row.id for row in db_session.query(models.ActivityLog).all()}
    assert remaining_notifications == {fresh_notification}
    assert remaining_activity == {fresh_activity}
    assert old_notification not in remaining_notifications
    assert old_activity not in remaining_activity


def test_purge_is_idempotent(client: TestClient, db_session):
    now = datetime.now(timezone.utc)
    user_id = _user_id(client)
    _seed(db_session, user_id, now)

    first = purge_expired_data(db_session, now=now)
    second = purge_expired_data(db_session, now=now)

    assert first == {"notifications": 1, "activity": 1}
    assert second == {"notifications": 0, "activity": 0}


def test_purge_accepts_custom_windows(client: TestClient, db_session):
    now = datetime.now(timezone.utc)
    user_id = _user_id(client)
    _seed(db_session, user_id, now)

    counts = purge_expired_data(
        db_session,
        now=now,
        notification_days=30,
        activity_days=60,
    )

    assert counts == {"notifications": 1, "activity": 1}
    # The 30-day-old activity entry is inside the 60-day window.
    assert db_session.query(models.ActivityLog).count() == 1
