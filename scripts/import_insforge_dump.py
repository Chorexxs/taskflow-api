"""Import a plain-SQL InsForge dump into a clean TaskFlow database (T-131).

InsForge hands out ``pg_dump`` plain-format archives (``.sql`` / ``.sql.gz``)
that contain both the ``public`` schema and InsForge's own schemas (``auth``,
``storage``, ``cron``, ``schedules``, ...), plus cluster roles and managed
extensions. Loading that whole file into another PostgreSQL fails, so this
script:

1. Scans the dump for ``COPY`` blocks and ``setval`` calls of one schema
   (``public`` by default) and skips everything else.
2. Loads those rows into a target that already has the schema, normally created
   with ``alembic upgrade head``.
3. Compares the row count of every table against the dump and exits 1 on any
   mismatch, so a partial import can never pass silently.

Example (dump restored into a disposable local PostgreSQL):

    python scripts/import_insforge_dump.py \\
        --dump backups/insforge-20261126.sql.gz \\
        --target-url postgresql://postgres:postgres@127.0.0.1:5432/taskflow_restore \\
        --truncate

Tables are loaded in foreign-key dependency order (computed from the target
catalog, not from the dump), so no constraint needs to be disabled and the
import also works on providers that do not grant superuser.

The target URL is never printed with credentials.
"""

from __future__ import annotations

import argparse
import gzip
import io
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import psycopg2

COPY_RE = re.compile(
    r"^COPY (?P<table>(?P<schema>\w+)\.(?P<name>\w+))(?: \((?P<columns>[^)]*)\))?"
    r" FROM stdin;\n(?P<rows>.*?)^\\\.$",
    re.M | re.S,
)
SETVAL_RE = re.compile(
    r"^SELECT pg_catalog\.setval\('(?P<sequence>\w+\.\w+)', (?P<value>-?\d+),"
    r" (?P<is_called>true|false)\);$",
    re.M,
)


@dataclass
class CopyBlock:
    """One ``COPY ... FROM stdin`` block of the dump."""

    table: str
    columns: str | None
    rows: str

    @property
    def row_count(self) -> int:
        return self.rows.count("\n")


@dataclass
class DumpContents:
    """Data extracted from a dump for a single schema."""

    schema: str
    blocks: list[CopyBlock] = field(default_factory=list)
    sequences: list[tuple[str, int, bool]] = field(default_factory=list)
    skipped_tables: list[str] = field(default_factory=list)


def redact_url(url: str) -> str:
    """Return host/database without user or password."""
    parts = urlsplit(url)
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{parts.hostname or 'localhost'}{port}/{parts.path.lstrip('/')}"


def read_dump(path: Path) -> str:
    """Read a ``.sql`` or ``.sql.gz`` dump as text."""
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    return path.read_text(encoding="utf-8", errors="replace")


def parse_dump(sql: str, schema: str = "public") -> DumpContents:
    """Extract ``COPY`` blocks and sequence values for one schema."""
    contents = DumpContents(schema=schema)

    for match in COPY_RE.finditer(sql):
        if match.group("schema") != schema:
            contents.skipped_tables.append(match.group("table"))
            continue
        contents.blocks.append(
            CopyBlock(
                table=match.group("table"),
                columns=match.group("columns"),
                rows=match.group("rows"),
            )
        )

    # InsForge dumps also carry other schemas with the same table names, so
    # only keep sequences that belong to the requested schema.
    for match in SETVAL_RE.finditer(sql):
        sequence = match.group("sequence")
        if not sequence.startswith(f"{schema}."):
            continue
        contents.sequences.append(
            (
                sequence,
                int(match.group("value")),
                match.group("is_called") == "true",
            )
        )

    return contents


def existing_row_counts(cursor, tables: list[str]) -> dict[str, int]:
    """Return the current row count of every table that exists in the target."""
    counts: dict[str, int] = {}
    for table in tables:
        cursor.execute("SELECT to_regclass(%s)", (table,))
        if cursor.fetchone()[0] is None:
            continue
        cursor.execute(f"SELECT count(*) FROM {table}")
        counts[table] = cursor.fetchone()[0]
    return counts


def target_tables(cursor) -> set[str]:
    cursor.execute(
        "SELECT schemaname || '.' || tablename FROM pg_tables WHERE schemaname = 'public'"
    )
    return {row[0] for row in cursor.fetchall()}


def order_tables_by_fk(cursor, tables: list[str]) -> list[str]:
    """Sort tables so every referenced table is loaded before its dependants.

    Self-references are ignored: ``pg_dump`` groups each table's rows together,
    so a self-referencing row order is not something the importer can fix.
    """
    cursor.execute(
        """
        SELECT child.relname, parent.relname
        FROM pg_constraint c
        JOIN pg_class child ON child.oid = c.conrelid
        JOIN pg_class parent ON parent.oid = c.confrelid
        JOIN pg_namespace n ON n.oid = child.relnamespace
        WHERE c.contype = 'f' AND n.nspname = 'public'
        """
    )
    dependencies: dict[str, set[str]] = {table.split(".", 1)[1]: set() for table in tables}
    for child, parent in cursor.fetchall():
        if child in dependencies and parent in dependencies and child != parent:
            dependencies[child].add(parent)

    ordered: list[str] = []
    pending = dict(dependencies)
    while pending:
        ready = sorted(name for name, parents in pending.items() if parents <= set(ordered))
        if not ready:
            # Cyclic foreign keys: fall back to alphabetical for the rest.
            ordered.extend(sorted(pending))
            break
        for name in ready:
            ordered.append(name)
            pending.pop(name)
    return [f"public.{name}" for name in ordered]


def import_dump(
    contents: DumpContents,
    target_url: str,
    *,
    truncate: bool,
    strict: bool,
) -> int:
    """Load the parsed blocks and verify the result. Returns a process exit code."""
    connection = psycopg2.connect(target_url)
    try:
        connection.autocommit = False
        with connection.cursor() as cursor:
            cursor.execute("SET client_encoding TO 'UTF8'")
            available = target_tables(cursor)
            tables = [block.table for block in contents.blocks]

            missing = [table for table in tables if table not in available]
            if missing and strict:
                print(f"ERROR: tables missing in target: {', '.join(missing)}", file=sys.stderr)
                print("Run 'alembic upgrade head' against the target first.", file=sys.stderr)
                return 1
            if missing:
                for table in missing:
                    print(f"WARNING: {table} does not exist in target; skipped")

            loadable = [block for block in contents.blocks if block.table in available]
            if not loadable:
                print("ERROR: nothing to import: no dump table exists in target", file=sys.stderr)
                return 1

            blocks_by_table = {block.table: block for block in loadable}
            loadable = [
                blocks_by_table[table]
                for table in order_tables_by_fk(cursor, list(blocks_by_table))
            ]

            counts = existing_row_counts(cursor, [block.table for block in loadable])
            occupied = {table: count for table, count in counts.items() if count}
            if occupied and not truncate:
                detail = ", ".join(f"{table}={count}" for table, count in sorted(occupied.items()))
                print(f"ERROR: target already has rows ({detail})", file=sys.stderr)
                print("Re-run with --truncate to replace them.", file=sys.stderr)
                return 1

            if truncate:
                cursor.execute(
                    "TRUNCATE " + ", ".join(block.table for block in loadable) + " CASCADE"
                )

            for block in loadable:
                statement = f"COPY {block.table}"
                if block.columns:
                    statement += f" ({block.columns})"
                statement += " FROM stdin"
                cursor.copy_expert(statement, io.StringIO(block.rows))
                print(f"  {block.table}: {block.row_count} rows")

            for sequence, value, is_called in contents.sequences:
                cursor.execute("SELECT to_regclass(%s)", (sequence,))
                if cursor.fetchone()[0] is None:
                    print(f"WARNING: sequence {sequence} does not exist in target; skipped")
                    continue
                cursor.execute("SELECT setval(%s, %s, %s)", (sequence, value, is_called))

            # The dump carries its own alembic_version row, so the target ends
            # up on the revision production was running.
            cursor.execute("SELECT version_num FROM alembic_version")
            row = cursor.fetchone()
            revision = row[0] if row else None

            actual = existing_row_counts(cursor, [block.table for block in loadable])

        connection.commit()

        mismatches = [
            (block.table, block.row_count, actual.get(block.table))
            for block in loadable
            if actual.get(block.table) != block.row_count
        ]
        total = sum(actual.values())
        print(f"Imported {len(loadable)} tables, {total} rows into {redact_url(target_url)}")
        print(f"Alembic revision in target: {revision}")
        if mismatches:
            for table, expected, found in mismatches:
                print(f"ERROR: {table}: dump has {expected}, target has {found}", file=sys.stderr)
            return 1
        print("Row counts match the dump.")
        return 0
    finally:
        connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import an InsForge SQL dump")
    parser.add_argument(
        "--dump",
        default=os.environ.get("INSFORGE_DUMP_PATH", ""),
        help="Path to the .sql or .sql.gz dump (or INSFORGE_DUMP_PATH)",
    )
    parser.add_argument(
        "--target-url",
        default=os.environ.get("IMPORT_TARGET_URL", ""),
        help="Target database URL (or IMPORT_TARGET_URL)",
    )
    parser.add_argument("--schema", default="public", help="Schema to import (default: public)")
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Empty the target tables before loading (destructive)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse the dump and report what would be imported",
    )
    parser.add_argument(
        "--lenient",
        action="store_true",
        help="Skip dump tables that do not exist in the target instead of failing",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.dump:
        raise SystemExit("--dump is required (or set INSFORGE_DUMP_PATH)")

    dump_path = Path(args.dump)
    if not dump_path.is_file():
        raise SystemExit(f"Dump not found: {dump_path}")

    contents = parse_dump(read_dump(dump_path), args.schema)
    if not contents.blocks:
        raise SystemExit(f"No '{args.schema}' tables found in {dump_path}")

    tables = len(contents.blocks)
    rows = sum(block.row_count for block in contents.blocks)
    print(f"Dump: {dump_path.name} -> {tables} tables, {rows} rows in '{args.schema}'")
    if contents.skipped_tables:
        print(
            f"Skipped {len(contents.skipped_tables)} table(s) from other schemas "
            "(InsForge internals)"
        )

    if args.dry_run:
        for block in contents.blocks:
            print(f"  {block.table}: {block.row_count} rows")
        return 0

    if not args.target_url:
        raise SystemExit("--target-url is required (or set IMPORT_TARGET_URL)")

    return import_dump(
        contents,
        args.target_url,
        truncate=args.truncate,
        strict=not args.lenient,
    )


if __name__ == "__main__":
    sys.exit(main())
