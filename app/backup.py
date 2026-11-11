"""Backup restore verification (T-102).

Compares a source database with the database restored from a dump: same
managed tables, same row counts and the same Alembic revision. Used by
``scripts/backup_restore_drill.py`` and by the test suite.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, inspect, text


class RestoreMismatch(RuntimeError):
    """Raised when a restored database differs from its source."""


@dataclass(frozen=True)
class TableCount:
    """Row count for one table in both databases."""

    table: str
    source: int
    target: int


@dataclass(frozen=True)
class RestoreReport:
    """Result of comparing a source database with a restored copy."""

    revision: str | None
    tables: tuple[TableCount, ...]

    @property
    def total_rows(self) -> int:
        return sum(item.source for item in self.tables)


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _row_count(engine: Engine, table: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar_one())


def _alembic_revision(engine: Engine, tables: set[str]) -> str | None:
    if "alembic_version" not in tables:
        return None
    with engine.connect() as conn:
        revision = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    return None if revision is None else str(revision)


def compare_databases(source: Engine, target: Engine) -> RestoreReport:
    """Verify that ``target`` is a faithful restore of ``source``.

    Checks every table (row counts) and the Alembic revision. Raises
    :class:`RestoreMismatch` with a readable diff on any difference.

    Args:
        source: Engine pointing at the original database.
        target: Engine pointing at the restored database.

    Returns:
        RestoreReport: Revision and per-table counts when they match.
    """
    source_tables = _table_names(source)
    target_tables = _table_names(target)

    missing = sorted(source_tables - target_tables)
    extra = sorted(target_tables - source_tables)
    if missing or extra:
        raise RestoreMismatch(
            f"Table mismatch: missing in target={missing}, extra in target={extra}"
        )

    counts = tuple(
        TableCount(
            table=table,
            source=_row_count(source, table),
            target=_row_count(target, table),
        )
        for table in sorted(source_tables)
    )
    mismatched = [item for item in counts if item.source != item.target]
    if mismatched:
        detail = ", ".join(
            f"{item.table}: source={item.source} target={item.target}" for item in mismatched
        )
        raise RestoreMismatch(f"Row count mismatch: {detail}")

    source_revision = _alembic_revision(source, source_tables)
    target_revision = _alembic_revision(target, target_tables)
    if source_revision != target_revision:
        raise RestoreMismatch(
            f"Alembic revision mismatch: source={source_revision} target={target_revision}"
        )

    return RestoreReport(revision=source_revision, tables=counts)
