"""Backup and restore drill (T-102).

Dumps a PostgreSQL database with ``pg_dump``, restores it into a target
database with ``pg_restore`` and verifies that both have the same tables, row
counts and Alembic revision.

Example (production dump restored into a disposable local PostgreSQL):

    python scripts/backup_restore_drill.py \\
        --source-url "$DATABASE_URL" \\
        --target-url postgresql://postgres@127.0.0.1:5432/taskflow_restore \\
        --pg-bin "C:/Program Files/PostgreSQL/16/bin" \\
        --schema public

InsForge dumps include managed extensions (`pg_cron`, `vector`, `http`, …)
that a clean PostgreSQL does not have, so restore the `public` schema only.
`--skip-restore` produces the backup artifact without restoring it.

The source URL is never printed with credentials. Exit code is 1 on any
mismatch so the drill can run as a scheduled check.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine  # noqa: E402

from app.backup import RestoreMismatch, compare_databases  # noqa: E402


def redact_url(url: str) -> str:
    """Return host/database without user or password."""
    parts = urlsplit(url)
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{parts.hostname or 'localhost'}{port}/{parts.path.lstrip('/')}"


def find_tool(name: str, pg_bin: str | None) -> str:
    if pg_bin:
        candidate = shutil.which(name, path=pg_bin)
    else:
        candidate = shutil.which(name)
    if not candidate:
        raise SystemExit(
            f"{name} not found. Install PostgreSQL client tools or pass --pg-bin."
        )
    return candidate


def run(command: list[str], secrets: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return
    stderr = result.stderr
    for secret in secrets:
        if secret:
            stderr = stderr.replace(secret, redact_url(secret))
    raise SystemExit(f"Command failed ({command[0]}):\n{stderr.strip()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TaskFlow backup/restore drill")
    parser.add_argument("--source-url", required=True, help="Database to dump")
    parser.add_argument("--target-url", required=True, help="Database to restore into")
    parser.add_argument(
        "--backup-file",
        default=str(Path(tempfile.gettempdir()) / "taskflow-backup.dump"),
        help="Path for the compressed dump (custom format)",
    )
    parser.add_argument("--pg-bin", default=None, help="Directory with pg_dump/pg_restore")
    parser.add_argument(
        "--schema",
        default=None,
        help="Restore only this schema (e.g. public) instead of the whole dump",
    )
    parser.add_argument(
        "--skip-restore",
        action="store_true",
        help="Only dump (useful to produce a backup artifact)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    backup_file = Path(args.backup_file)
    backup_file.parent.mkdir(parents=True, exist_ok=True)
    pg_dump = find_tool("pg_dump", args.pg_bin)
    pg_restore = find_tool("pg_restore", args.pg_bin)
    secrets = [args.source_url, args.target_url]

    print(f"source={redact_url(args.source_url)}")
    print(f"target={redact_url(args.target_url)}")
    print(f"backup={backup_file}")

    started = time.monotonic()
    run(
        [
            pg_dump,
            "--format=custom",
            "--no-owner",
            "--no-privileges",
            f"--file={backup_file}",
            args.source_url,
        ],
        secrets,
    )
    print(f"dump_ok size_kb={backup_file.stat().st_size // 1024}")

    if args.skip_restore:
        print("restore_skipped")
        return 0

    restore_command = [
        pg_restore,
        "--clean",
        "--if-exists",
        "--no-owner",
        "--no-privileges",
        "--exit-on-error",
        f"--dbname={args.target_url}",
    ]
    if args.schema:
        restore_command.append(f"--schema={args.schema}")
    restore_command.append(str(backup_file))
    run(restore_command, secrets)
    print("restore_ok")

    source_engine = create_engine(args.source_url)
    target_engine = create_engine(args.target_url)
    try:
        report = compare_databases(source_engine, target_engine)
    except RestoreMismatch as exc:
        print(f"restore_verification_failed: {exc}", file=sys.stderr)
        return 1
    finally:
        source_engine.dispose()
        target_engine.dispose()

    print(f"revision={report.revision}")
    print(f"tables={len(report.tables)} rows={report.total_rows}")
    for item in report.tables:
        print(f"  {item.table}: {item.source}")
    elapsed = time.monotonic() - started
    print(f"restore_verified elapsed_s={elapsed:.1f}")
    print(f"checked_at={datetime.now(timezone.utc).isoformat()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
