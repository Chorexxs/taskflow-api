"""Backfill attachment blobs into object storage (T-054).

Moves attachments that still live in the database (``content``) or on local disk
(``file_path``) into the configured InsForge Storage bucket, sets
``attachments.storage_key`` and recomputes the SHA-256 checksum when missing.

The source bytes are kept by default (``--clear-source`` removes them after a
successful upload) so the operation can be rolled back by clearing
``storage_key`` and switching ``STORAGE_BACKEND`` back to ``database``/``local``.

Example:
    STORAGE_BACKEND=insforge INSFORGE_URL=... INSFORGE_API_KEY=... \
    DATABASE_URL=... python scripts/backfill_attachments_object_storage.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import models  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import get_session_local  # noqa: E402
from app.storage import StorageError, attachment_extension, get_storage  # noqa: E402


def _load_bytes(attachment: models.Attachment) -> bytes | None:
    if attachment.content is not None:
        content = attachment.content
        return content.tobytes() if isinstance(content, memoryview) else content
    if attachment.file_path and os.path.exists(attachment.file_path):
        return Path(attachment.file_path).read_bytes()
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill attachments to object storage")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=0, help="0 means all")
    parser.add_argument(
        "--clear-source",
        action="store_true",
        help="Null content/file_path after a verified upload (frees database space)",
    )
    args = parser.parse_args()

    storage = get_storage()
    if storage is None or settings.storage_backend != "insforge":
        print("STORAGE_BACKEND must be 'insforge'", file=sys.stderr)
        return 2
    factory = get_session_local()
    if factory is None:
        print("DATABASE_URL is not configured", file=sys.stderr)
        return 2

    migrated = skipped = failed = 0
    with factory() as db:
        query = db.query(models.Attachment).filter(models.Attachment.storage_key.is_(None))
        if args.limit:
            query = query.limit(args.limit)
        attachments = query.order_by(models.Attachment.id).all()
        print(f"attachments pending: {len(attachments)}")

        for attachment in attachments:
            data = _load_bytes(attachment)
            if data is None:
                skipped += 1
                print(f"skip {attachment.id}: no bytes")
                continue
            checksum = attachment.checksum or hashlib.sha256(data).hexdigest()
            key = storage.build_key(
                attachment.task_id,
                attachment_extension(attachment.filename),
                attachment.filename,
            )
            if args.dry_run:
                print(f"would migrate {attachment.id} -> {key} ({len(data)} bytes)")
                migrated += 1
                continue
            try:
                storage.put(key, data, attachment.mime_type, attachment.filename)
                stored = storage.get(key)
                if hashlib.sha256(stored).hexdigest() != checksum:
                    raise StorageError("checksum mismatch after upload")
                attachment.storage_key = key
                attachment.checksum = checksum
                if args.clear_source:
                    attachment.content = None
                    attachment.file_path = None
                db.commit()
                migrated += 1
                print(f"migrated {attachment.id} -> {key}")
            except StorageError as exc:
                db.rollback()
                failed += 1
                print(f"failed {attachment.id}: {exc}", file=sys.stderr)

    print(f"\nmigrated={migrated} skipped={skipped} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
