"""Notification event bus and SSE connection accounting (T-081).

The bus decouples notification creation from the SSE streams:

- ``publish`` pushes an event to every local subscriber and, when Redis is
  available, to a per-user pub/sub channel so other API instances can relay it.
- ``subscription`` yields a queue that receives the events for one user.

Redis is optional. If it is unreachable the bus keeps working in-process and
retries after a short cooldown, so a single instance never loses notifications
just because Redis is down. The SSE router also reconciles from the database
periodically, which covers events lost while no subscriber was connected.
"""

from __future__ import annotations

import asyncio
import json
import threading
import time
from collections import defaultdict
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_CHANNEL_PREFIX = "taskflow:notifications"
REDIS_RETRY_SECONDS = 30.0
REDIS_TIMEOUT_SECONDS = 0.2
QUEUE_MAX_SIZE = 100


class NotificationEventBus:
    """In-process fan-out with optional Redis pub/sub relay."""

    def __init__(
        self,
        redis_url: str | None = None,
        *,
        channel_prefix: str = DEFAULT_CHANNEL_PREFIX,
        retry_seconds: float = REDIS_RETRY_SECONDS,
    ) -> None:
        self._redis_url = (settings.REDIS_URL if redis_url is None else redis_url).strip()
        self._channel_prefix = channel_prefix.rstrip(":")
        self._retry_seconds = retry_seconds
        self._queues: dict[int, set[asyncio.Queue[dict]]] = defaultdict(set)
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._listener_task: asyncio.Task[None] | None = None
        self._listener_ready: asyncio.Event | None = None
        self._redis_available = bool(self._redis_url)
        self._next_retry = 0.0
        self._sync_client: Any = None
        self._async_client: Any = None

        # Injectable factories keep tests deterministic.
        self.sync_client_factory: Callable[[], Any] | None = None
        self.async_client_factory: Callable[[], Any] | None = None

    @property
    def redis_configured(self) -> bool:
        return bool(self._redis_url)

    def _channel(self, user_id: int) -> str:
        return f"{self._channel_prefix}:{user_id}"

    def _reset_for_loop(self) -> None:
        loop = asyncio.get_running_loop()
        if self._loop is not loop:
            # TestClient and some workers create a new loop per request/worker.
            self._loop = loop
            self._listener_task = None
            self._listener_ready = None
            self._async_client = None
            self._queues.clear()

    def _dispatch_local(self, user_id: int, payload: dict) -> None:
        with self._lock:
            queues = list(self._queues.get(user_id, ()))
            loop = self._loop
        for queue in queues:
            if loop is not None and loop.is_running():
                # Notification creation runs in FastAPI's threadpool; asyncio
                # queues must be touched from their event loop thread.
                try:
                    loop.call_soon_threadsafe(self._enqueue, queue, user_id, payload)
                except RuntimeError:  # loop closed during shutdown
                    pass
            else:
                self._enqueue(queue, user_id, payload)

    @staticmethod
    def _enqueue(queue: asyncio.Queue[dict], user_id: int, payload: dict) -> None:
        try:
            queue.put_nowait(payload)
        except asyncio.QueueFull:
            # The stream reconciles from the database, so dropping is safe.
            logger.warning("sse_local_queue_full", user_id=user_id)

    def _mark_redis_down(self, exc: Exception) -> None:
        self._redis_available = False
        self._next_retry = time.monotonic() + self._retry_seconds
        logger.warning("sse_redis_unavailable", error=str(exc))

    def _get_sync_client(self) -> Any:
        if self._sync_client is None:
            if self.sync_client_factory is not None:
                self._sync_client = self.sync_client_factory()
            else:
                import redis

                self._sync_client = redis.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
                    socket_timeout=REDIS_TIMEOUT_SECONDS,
                )
        return self._sync_client

    def _get_async_client(self) -> Any:
        if self._async_client is None:
            if self.async_client_factory is not None:
                self._async_client = self.async_client_factory()
            else:
                from redis import asyncio as redis_asyncio

                self._async_client = redis_asyncio.from_url(
                    self._redis_url,
                    decode_responses=True,
                    socket_connect_timeout=REDIS_TIMEOUT_SECONDS,
                    socket_timeout=REDIS_TIMEOUT_SECONDS,
                )
        return self._async_client

    def publish(self, user_id: int, payload: dict) -> None:
        """Publish an event locally and, best effort, through Redis."""
        self._dispatch_local(user_id, payload)

        if not self._redis_url or not self._redis_available:
            return
        if time.monotonic() < self._next_retry:
            return
        try:
            self._get_sync_client().publish(
                self._channel(user_id), json.dumps(payload, separators=(",", ":"))
            )
        except Exception as exc:  # pragma: no cover - depends on infrastructure
            self._mark_redis_down(exc)

    async def _wait_until_ready(self) -> None:
        if self._listener_ready is None:
            return
        try:
            await asyncio.wait_for(self._listener_ready.wait(), timeout=0.5)
        except asyncio.TimeoutError:
            # Do not block the first SSE frame on Redis; retry in background.
            pass

    async def _ensure_listener(self) -> None:
        if not self._redis_url or not self._redis_available:
            return
        if time.monotonic() < self._next_retry:
            return
        if self._listener_task is not None and not self._listener_task.done():
            await self._wait_until_ready()
            return

        self._listener_ready = asyncio.Event()
        self._listener_task = asyncio.create_task(
            self._listen_redis(), name="notification-sse-redis"
        )
        await self._wait_until_ready()

    async def _listen_redis(self) -> None:
        pubsub = None
        client = None
        assert self._listener_ready is not None
        try:
            client = self._get_async_client()
            pubsub = client.pubsub()
            await pubsub.psubscribe(f"{self._channel_prefix}:*")
            self._redis_available = True
            self._listener_ready.set()
            async for message in pubsub.listen():
                if message.get("type") != "pmessage":
                    continue
                channel = message.get("channel")
                if isinstance(channel, bytes):
                    channel = channel.decode()
                try:
                    user_id = int(str(channel).rsplit(":", 1)[1])
                except (IndexError, ValueError):
                    continue
                data = message.get("data")
                if isinstance(data, bytes):
                    data = data.decode()
                try:
                    payload = json.loads(data)
                except (TypeError, ValueError):
                    continue
                self._dispatch_local(user_id, payload)
        except asyncio.CancelledError:  # pragma: no cover - shutdown
            raise
        except Exception as exc:  # pragma: no cover - depends on infrastructure
            self._mark_redis_down(exc)
        finally:
            self._listener_ready.set()
            self._listener_task = None
            if pubsub is not None:
                try:
                    await pubsub.aclose()
                except Exception:
                    pass
            if client is not None:
                try:
                    await client.aclose()
                except Exception:
                    pass
            self._async_client = None

    @asynccontextmanager
    async def subscription(self, user_id: int) -> AsyncIterator[asyncio.Queue[dict]]:
        """Register a queue that receives every event for ``user_id``."""
        self._reset_for_loop()
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=QUEUE_MAX_SIZE)
        with self._lock:
            self._queues[user_id].add(queue)
        try:
            await self._ensure_listener()
            yield queue
        finally:
            with self._lock:
                queues = self._queues.get(user_id)
                if queues is not None:
                    queues.discard(queue)
                    if not queues:
                        self._queues.pop(user_id, None)

    async def wait_for_event(self, queue: asyncio.Queue[dict], timeout: float) -> dict | None:
        """Return the next event or ``None`` when the timeout expires."""
        try:
            return await asyncio.wait_for(queue.get(), timeout=max(timeout, 0.01))
        except asyncio.TimeoutError:
            return None


class SSEConnectionLimiter:
    """Track concurrent SSE streams globally and per user."""

    def __init__(self, max_total: int, max_per_user: int) -> None:
        self.max_total = max_total
        self.max_per_user = max_per_user
        self._total = 0
        self._per_user: dict[int, int] = defaultdict(int)
        self._lock = threading.Lock()

    def acquire(self, user_id: int) -> bool:
        with self._lock:
            if self.max_total > 0 and self._total >= self.max_total:
                return False
            if self.max_per_user > 0 and self._per_user[user_id] >= self.max_per_user:
                return False
            self._total += 1
            self._per_user[user_id] += 1
            return True

    def release(self, user_id: int) -> None:
        with self._lock:
            if self._total > 0:
                self._total -= 1
            if self._per_user.get(user_id, 0) > 1:
                self._per_user[user_id] -= 1
            else:
                self._per_user.pop(user_id, None)

    def snapshot(self) -> tuple[int, dict[int, int]]:
        with self._lock:
            return self._total, dict(self._per_user)


notification_bus = NotificationEventBus()
sse_limiter = SSEConnectionLimiter(
    max_total=settings.SSE_MAX_CONNECTIONS,
    max_per_user=settings.SSE_MAX_CONNECTIONS_PER_USER,
)
