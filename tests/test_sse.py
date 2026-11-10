"""Server-Sent Events stream for notifications (T-059)."""

import asyncio
import json

from fastapi.testclient import TestClient

from app import models
from app.config import settings
from app.routers.notifications import iter_notification_events


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


class FakeRequest:
    """Minimal request stub with a configurable disconnect counter."""

    def __init__(self, disconnect_after: int = 1000):
        self.calls = 0
        self.disconnect_after = disconnect_after

    async def is_disconnected(self) -> bool:
        self.calls += 1
        return self.calls > self.disconnect_after


def _setup(client: TestClient, db_session) -> tuple[str, dict]:
    assert client.post(
        "/api/v1/auth/register",
        json={"email": "sse@example.com", "password": "password123"},
    ).status_code == 201
    token = client.post(
        "/api/v1/auth/login",
        data={"username": "sse@example.com", "password": "password123"},
    ).json()["access_token"]
    user_id = client.get("/api/v1/users/me", headers=_headers(token)).json()["id"]

    notification = models.Notification(
        user_id=user_id,
        type="commented",
        entity_type="task",
        entity_id=1,
        message="New comment on your task",
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)
    return token, {"id": notification.id, "user_id": user_id}


def test_sse_streams_notification_and_heartbeat(
    client: TestClient, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "SSE_POLL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "SSE_HEARTBEAT_SECONDS", 0.03)
    _, notification = _setup(client, db_session)
    assert (
        db_session.query(models.Notification)
        .filter(models.Notification.user_id == notification["user_id"])
        .count()
        == 1
    )

    async def consume():
        request = FakeRequest()
        generator = iter_notification_events(
            request, db_session, notification["user_id"], start_after=0
        )
        payload = None
        heartbeat = False
        try:
            for _ in range(100):
                frame = await asyncio.wait_for(generator.__anext__(), timeout=2)
                data_lines = [
                    line for line in frame.splitlines() if line.startswith("data: ")
                ]
                if data_lines:
                    payload = json.loads(data_lines[0][len("data: "):])
                elif frame.strip() == ": heartbeat":
                    heartbeat = True
                if payload is not None and heartbeat:
                    break
        finally:
            await generator.aclose()
        return payload, heartbeat

    payload, heartbeat = asyncio.run(consume())

    assert payload is not None
    assert payload["id"] == notification["id"]
    assert payload["message"] == "New comment on your task"
    assert heartbeat is True


def test_sse_requires_authentication(client: TestClient):
    response = client.get("/api/v1/notifications/stream")
    assert response.status_code == 401
