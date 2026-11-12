"""TLS settings for the integration suite (T-114).

The suite must not inherit ``DB_SSLMODE`` from a developer ``.env`` that points
at production: InsForge requires TLS, while the disposable test database is
usually a local PostgreSQL container that does not speak TLS. Before T-114 the
app engine reused ``DB_SSLMODE=require`` and five tests failed with
``server does not support SSL, but SSL was required``.

Precedence:

1. ``TEST_DB_SSLMODE``, an explicit override for remote CI databases.
2. The ``sslmode`` query parameter of ``TEST_DATABASE_URL``.
3. ``prefer``, which negotiates TLS but still connects to a plain local server.
"""

from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

DEFAULT_TEST_SSLMODE = "prefer"


def resolve_sslmode(database_url: str, override: str | None = None) -> str:
    """Return the ``sslmode`` the suite should use for ``database_url``."""
    if override is not None:
        candidate = override.strip().lower()
        if candidate:
            return candidate

    values = parse_qs(urlsplit(database_url).query).get("sslmode")
    if values:
        candidate = values[0].strip().lower()
        if candidate:
            return candidate

    return DEFAULT_TEST_SSLMODE
