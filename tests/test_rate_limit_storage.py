"""Tests for the shared rate-limit storage (T-030)."""

import fakeredis
import redis
from limits import parse
from limits.strategies import MovingWindowRateLimiter

from app.config import settings
from app.rate_limit import build_limiter


def test_testing_uses_in_memory_storage():
    """The suite must never depend on a live Redis server."""
    assert settings.rate_limit_storage_uri == "memory://"


def test_redis_storage_is_shared_between_limiter_instances(monkeypatch):
    """Two limiter instances share counters through the same Redis backend."""
    server = fakeredis.FakeServer()

    def fake_from_url(url, **kwargs):
        return fakeredis.FakeRedis(server=server, decode_responses=True)

    monkeypatch.setattr(redis, "from_url", fake_from_url)

    first = build_limiter(storage_uri="redis://shared/0", enabled=True)
    second = build_limiter(storage_uri="redis://shared/0", enabled=True)
    item = parse("3/minute")

    first_strategy = MovingWindowRateLimiter(first._storage)
    second_strategy = MovingWindowRateLimiter(second._storage)

    assert [first_strategy.hit(item, "ip:1") for _ in range(3)] == [True, True, True]
    # The fourth request in the window is rejected by the first instance...
    assert first_strategy.hit(item, "ip:1") is False
    # ...and the second instance sees the same counter.
    assert second_strategy.hit(item, "ip:1") is False
    # A different key still has its own budget.
    assert second_strategy.hit(item, "ip:2") is True
