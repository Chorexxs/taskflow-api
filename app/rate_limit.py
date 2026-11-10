"""Shared rate-limiting configuration.

A single :class:`slowapi.Limiter` instance is used by the application and by
every router. The storage backend is Redis when one is configured (ADR-010),
so multiple API instances share the same counters. If Redis is unreachable the
limiter falls back to an in-memory store instead of failing requests.
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def build_limiter(
    *,
    storage_uri: str | None = None,
    enabled: bool | None = None,
) -> Limiter:
    """Create a limiter with the shared storage configuration.

    Args:
        storage_uri: Explicit backend URI. ``None`` uses the application
            settings; pass ``"memory://"`` to force an in-memory store.
        enabled: Explicit enabled flag. ``None`` derives it from settings and
            the ``TESTING`` environment variable.

    Returns:
        Limiter: Configured slowapi limiter.
    """
    uri = settings.rate_limit_storage_uri if storage_uri is None else storage_uri
    is_enabled = settings.RATE_LIMIT_ENABLED if enabled is None else enabled
    if os.environ.get("TESTING"):
        # The suite enables the limiter only in the tests that assert it.
        is_enabled = bool(enabled) if enabled is not None else False

    return Limiter(
        key_func=get_remote_address,
        storage_uri=uri or "memory://",
        strategy="moving-window",
        headers_enabled=True,
        in_memory_fallback_enabled=True,
        retry_after="delta-seconds",
        enabled=is_enabled,
    )


# Single application-wide limiter. Routers must import this instance instead of
# creating their own so that every limit shares the same backend.
limiter = build_limiter()


def rate_limit(limit_str: str):
    """Return the shared rate-limit decorator for ``limit_str``.

    Unlike the previous router-local helper, the decorator is always applied;
    the limiter itself is disabled while testing unless a test enables it.
    """
    return limiter.limit(limit_str)
