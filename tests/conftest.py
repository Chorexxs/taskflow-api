"""Test fixtures.

Integration tests run against PostgreSQL (ADR-008). Set ``TEST_DATABASE_URL``
to a disposable database; the schema is created with Alembic once per session
and every test starts from empty tables.

``TEST_USE_SQLITE=1`` is a documented escape hatch for quick, unit-only runs
when no PostgreSQL is available. It must not be used to validate a release.
"""

import os
import subprocess
import sys
from pathlib import Path

from tests.ssl_support import resolve_sslmode

os.environ["TESTING"] = "1"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

ROOT = Path(__file__).resolve().parents[1]


def _resolve_database_url() -> str:
    """Return the disposable database used by the suite."""
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if url:
        # Managed providers still emit the legacy scheme.
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    if os.environ.get("TEST_USE_SQLITE") == "1":
        return "sqlite:///:memory:"
    raise RuntimeError(
        "T-077: integration tests require PostgreSQL.\n"
        "Set TEST_DATABASE_URL to a disposable database, e.g.\n"
        "  docker compose up -d postgres\n"
        "  TEST_DATABASE_URL=postgresql://taskflow:taskflow@localhost:5432/taskflow_test\n"
        "Use TEST_USE_SQLITE=1 only for quick, unit-only runs."
    )


TEST_DATABASE_URL = _resolve_database_url()
IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")
SKIP_MIGRATIONS = os.environ.get("TEST_SKIP_MIGRATIONS") == "1"

# Keep any app code that resolves the database at import time away from the
# development/production database.
if not IS_SQLITE:
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL

    # T-114: a developer .env targeting production sets DB_SSLMODE=require, and
    # pydantic-settings would apply it to the local test container, which does
    # not support TLS. Environment variables win over .env, so pin the value
    # from TEST_DATABASE_URL/TEST_DB_SSLMODE before importing the app.
    os.environ["DB_SSLMODE"] = resolve_sslmode(TEST_DATABASE_URL, os.environ.get("TEST_DB_SSLMODE"))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, inspect, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import main  # noqa: E402
from app.database import Base, get_db  # noqa: E402

if IS_SQLITE:
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def _apply_schema() -> None:
    """Create the schema once per session.

    PostgreSQL uses the real migrations so the suite validates the same schema
    as production. SQLite (escape hatch) falls back to ``create_all``.
    """
    if IS_SQLITE:
        Base.metadata.create_all(bind=test_engine)
        return
    if SKIP_MIGRATIONS:
        return

    env = {
        **os.environ,
        "DATABASE_URL": TEST_DATABASE_URL,
        "ENVIRONMENT": "test",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "alembic upgrade head failed against the test database:\n"
            f"{result.stdout}\n{result.stderr}"
        )


def _truncate_tables() -> None:
    """Empty every table between tests, keeping the schema and migrations."""
    existing = set(inspect(test_engine).get_table_names())
    names = [
        table.name
        for table in Base.metadata.sorted_tables
        if table.name in existing and table.name != "alembic_version"
    ]
    if not names:
        return
    quoted = ", ".join(f'"{name}"' for name in names)
    with test_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


def _drop_and_create() -> None:
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def database_schema():
    """Create or migrate the disposable test database once per session."""
    _apply_schema()
    yield
    test_engine.dispose()


@pytest.fixture(scope="session")
def database_engine():
    """Expose the engine so tests can assert the dialect in use."""
    return test_engine


@pytest.fixture(scope="function", autouse=True)
def setup_database(database_schema):
    """Give every test a clean database, independent from the others."""
    if IS_SQLITE:
        _drop_and_create()
    else:
        _truncate_tables()
    yield
    main.app.state.limiter.enabled = False
    main.app.state.limiter.reset()


@pytest.fixture(scope="function")
def db_session():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    main.app.dependency_overrides[get_db] = override_get_db
    with TestClient(main.app) as test_client:
        yield test_client
    main.app.dependency_overrides.clear()
