"""Server-Sent Events stream for notifications (T-059, hardened in T-081)."""

import asyncio
import json

import fakeredis
import fakeredis.aioredis
from fastapi.testclient import TestClient

from app import models
from app.config import settings
from app.events import NotificationEventBus, SSEConnectionLimiter
from app.routers import notifications as notifications_router
from app.routers.notifications import guarded_notification_events, iter_notification_events


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
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": "sse@example.com", "password": "password123"},
        ).status_code
        == 201
    )
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


def test_sse_streams_notification_and_heartbeat(client: TestClient, db_session, monkeypatch):
    monkeypatch.setattr(settings, "SSE_FALLBACK_POLL_SECONDS", 0.01)
    monkeypatch.setattr(settings, "SSE_HEARTBEAT_SECONDS", 0.03)
    _, notification = _setup(client, db_session)

    async def consume():
        request = FakeRequest()
        generator = iter_notification_events(
            request,
            notification["user_id"],
            start_after=0,
            bus=NotificationEventBus(redis_url=""),
        )
        payload = None
        heartbeat = False
        try:
            for _ in range(100):
                frame = await asyncio.wait_for(generator.__anext__(), timeout=2)
                data_lines = [line for line in frame.splitlines() if line.startswith("data: ")]
                if data_lines:
                    payload = json.loads(data_lines[0][len("data: ") :])
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


def test_sse_delivers_buffer_event_without_waiting_for_poll(
    client: TestClient, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "SSE_FALLBACK_POLL_SECONDS", 60)
    monkeypatch.setattr(settings, "SSE_HEARTBEAT_SECONDS", 30)
    _, notification = _setup(client, db_session)
    bus = NotificationEventBus(redis_url="")

    async def consume():
        generator = iter_notification_events(
            FakeRequest(),
            notification["user_id"],
            start_after=notification["id"],
            bus=bus,
        )

        async def publish_later():
            await asyncio.sleep(0.02)
            bus.publish(notification["user_id"], {"id": notification["id"] + 1})

        publisher = asyncio.create_task(publish_later())
        try:
            frame = await asyncio.wait_for(generator.__anext__(), timeout=1)
        finally:
            await generator.aclose()
            await publisher
        return frame

    frame = asyncio.run(consume())

    assert f"id: {notification['id'] + 1}" in frame
    assert "event: notification" in frame


def test_sse_requires_authentication(client: TestClient):
    response = client.get("/api/v1/notifications/stream")
    assert response.status_code == 401


def test_sse_connection_limit_returns_503(client: TestClient, db_session, monkeypatch):
    token, notification = _setup(client, db_session)
    limiter = SSEConnectionLimiter(max_total=1, max_per_user=1)
    assert limiter.acquire(notification["user_id"]) is True
    monkeypatch.setattr(notifications_router, "sse_limiter", limiter)

    response = client.get("/api/v1/notifications/stream", headers=_headers(token))

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "5"
    assert "Too many" in response.json()["detail"]


def test_stream_releases_the_limiter_slot_when_it_closes(monkeypatch):
    """The generator's finally must free the slot on disconnect (T-121)."""

    async def fake_events(*args, **kwargs):
        yield "data: hello\n\n"

    monkeypatch.setattr(notifications_router, "iter_notification_events", fake_events)
    limiter = SSEConnectionLimiter(max_total=1, max_per_user=1)
    assert limiter.acquire(7) is True

    async def scenario():
        generator = guarded_notification_events(
            FakeRequest(),
            7,
            0,
            session_factory=None,
            limiter=limiter,
        )
        assert await generator.__anext__() == "data: hello\n\n"
        await generator.aclose()
        return limiter.snapshot()

    assert asyncio.run(scenario()) == (0, {})


def test_connection_limiter_tracks_total_and_per_user():
    limiter = SSEConnectionLimiter(max_total=2, max_per_user=1)

    assert limiter.acquire(1) is True
    assert limiter.acquire(1) is False
    assert limiter.acquire(2) is True
    assert limiter.acquire(3) is False

    limiter.release(1)
    assert limiter.acquire(3) is True

    total, per_user = limiter.snapshot()
    assert total == 2
    assert per_user == {2: 1, 3: 1}


def test_bus_relays_events_through_redis_pubsub():
    server = fakeredis.FakeServer()
    bus = NotificationEventBus(redis_url="redis://fake", retry_seconds=0)
    bus.sync_client_factory = lambda: fakeredis.FakeRedis(server=server, decode_responses=True)
    bus.async_client_factory = lambda: fakeredis.aioredis.FakeRedis(
        server=server, decode_responses=True
    )
    publisher = NotificationEventBus(redis_url="redis://fake", retry_seconds=0)
    publisher.sync_client_factory = lambda: fakeredis.FakeRedis(
        server=server, decode_responses=True
    )

    async def scenario():
        async with bus.subscription(7) as queue:
            publisher.publish(7, {"id": 42, "message": "from redis"})
            return await bus.wait_for_event(queue, timeout=1)

    event = asyncio.run(scenario())

    assert event == {"id": 42, "message": "from redis"}


def test_create_notification_publishes_to_bus(client: TestClient, db_session, monkeypatch):
    from app import crud

    _, notification = _setup(client, db_session)
    published: list[tuple[int, dict]] = []
    monkeypatch.setattr(
        "app.crud.notification_bus.publish",
        lambda user_id, payload: published.append((user_id, payload)),
    )

    created = crud.create_notification(
        db_session,
        user_id=notification["user_id"],
        notification_type="commented",
        entity_type="task",
        entity_id=2,
        message="A new comment",
    )

    assert created is not None
    assert published
    user_id, payload = published[0]
    assert user_id == notification["user_id"]
    assert payload["id"] == created.id
    assert payload["message"] == "A new comment"
