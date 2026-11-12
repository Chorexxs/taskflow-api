"""T-114: the suite must not inherit TLS settings from the production .env.

``DB_SSLMODE=require`` is mandatory in production (T-108), but the disposable
test database is a plain local PostgreSQL container. The fixtures pin the value
from ``TEST_DATABASE_URL``/``TEST_DB_SSLMODE`` before importing the app so the
engine and Alembic agree on how to connect.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from app.config import settings
from app.database import get_engine
from tests.ssl_support import DEFAULT_TEST_SSLMODE, resolve_sslmode


@pytest.mark.parametrize(
    ("database_url", "override", "expected"),
    [
        ("postgresql://u:p@localhost:5432/taskflow_test", None, "prefer"),
        (
            "postgresql://u:p@localhost:5432/taskflow_test?sslmode=require",
            None,
            "require",
        ),
        ("postgresql://host/db?a=1&sslmode=verify-full", None, "verify-full"),
        ("postgresql://host/db?sslmode=REQUIRE", None, "require"),
        (
            "postgresql://u:p@localhost/taskflow_test?sslmode=require",
            "disable",
            "disable",
        ),
        ("postgresql://u:p@localhost/taskflow_test?sslmode=", None, DEFAULT_TEST_SSLMODE),
        ("postgresql://u:p@localhost/taskflow_test", "   ", DEFAULT_TEST_SSLMODE),
    ],
)
def test_resolve_sslmode(database_url: str, override: str | None, expected: str) -> None:
    assert resolve_sslmode(database_url, override) == expected


def test_suite_pins_sslmode_from_the_test_url() -> None:
    if os.environ.get("TEST_USE_SQLITE") == "1":
        pytest.skip("SQLite does not use sslmode")
    assert os.environ["DB_SSLMODE"] == resolve_sslmode(
        os.environ["DATABASE_URL"], os.environ.get("TEST_DB_SSLMODE")
    )


def test_settings_honour_the_suite_sslmode() -> None:
    if os.environ.get("TEST_USE_SQLITE") == "1":
        pytest.skip("SQLite does not use sslmode")
    assert settings.DB_SSLMODE == os.environ["DB_SSLMODE"]


def test_app_engine_connects_with_the_suite_sslmode() -> None:
    if os.environ.get("TEST_USE_SQLITE") == "1":
        pytest.skip("adapter is exercised against PostgreSQL only")
    engine = get_engine()
    assert engine is not None
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
