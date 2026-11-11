"""Restore verification used by the backup drill (T-102)."""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app.backup import RestoreMismatch, compare_databases


def _engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _seed(engine, *, users: int = 2, revision: str = "abc123") -> None:
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32))"))
        for index in range(users):
            conn.execute(text("INSERT INTO users (id) VALUES (:id)"), {"id": index + 1})
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
            {"rev": revision},
        )


def test_identical_databases_match():
    source = _engine()
    target = _engine()
    _seed(source)
    _seed(target)

    report = compare_databases(source, target)

    assert report.revision == "abc123"
    assert {item.table: item.source for item in report.tables} == {
        "alembic_version": 1,
        "users": 2,
    }
    assert report.total_rows == 3


def test_row_count_mismatch_is_reported():
    source = _engine()
    target = _engine()
    _seed(source, users=3)
    _seed(target, users=1)

    with pytest.raises(RestoreMismatch, match="Row count mismatch"):
        compare_databases(source, target)


def test_missing_table_is_reported():
    source = _engine()
    target = _engine()
    _seed(source)
    with target.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))

    with pytest.raises(RestoreMismatch, match="Table mismatch"):
        compare_databases(source, target)


def test_revision_mismatch_is_reported():
    source = _engine()
    target = _engine()
    _seed(source, revision="head-new")
    _seed(target, revision="head-old")

    with pytest.raises(RestoreMismatch, match="Alembic revision mismatch"):
        compare_databases(source, target)
