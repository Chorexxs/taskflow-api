"""Attachment upload pipeline.

Keeps the router limited to HTTP concerns (task resolution, idempotency and the
response schema): validation, streaming, malware scanning, storage selection and
bookkeeping live here (T-125, CA-2-03).
"""

from __future__ import annotations

import asyncio
import hashlib
import mimetypes
import os
import re
import uuid
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile, status

from app import crud, models
from app.config import settings
from app.logging_config import get_logger
from app.malware import MalwareDetected, ScannerUnavailable, scan_upload
from app.storage import StorageError, get_storage
from app.uploads import validate_file_signature

logger = get_logger(__name__)

CHUNK_SIZE = 1024 * 1024
HTTP_413_TOO_LARGE = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)

# Only allow a conservative, explicit set of characters in filenames.
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(slots=True)
class UploadedFile:
    """Validated upload ready to be persisted."""

    filename: str
    extension: str
    mime_type: str
    content: bytes
    checksum: str


def sanitize_filename(filename: str | None) -> str:
    """Return a safe, human-readable filename.

    The client-supplied filename is never trusted: path separators are
    stripped, control characters removed and everything outside a small
    allowlist collapsed to underscores.
    """
    candidate = (filename or "").replace("\\", "/")
    candidate = os.path.basename(candidate).replace("\x00", "").strip()
    if candidate in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")

    candidate = _UNSAFE_FILENAME_CHARS.sub("_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("._")
    if not candidate:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if len(candidate) > 255:
        stem, extension = os.path.splitext(candidate)
        candidate = f"{stem[: 255 - len(extension)]}{extension}"

    return candidate


def validate_upload_type(filename: str, content_type: str | None) -> tuple[str, str]:
    """Validate the extension and return ``(extension, mime_type)``.

    The extension allowlist is the primary control; the MIME type is derived
    from the extension when possible and only falls back to the client value
    for generic/unknown types.
    """
    extension = os.path.splitext(filename)[1].lower()
    normalized_extension = extension.lstrip(".")
    if normalized_extension not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{extension or 'unknown'}' is not allowed",
        )

    guessed_type, _ = mimetypes.guess_type(filename)
    mime_type = guessed_type or content_type or "application/octet-stream"
    return extension, mime_type[:100]


def _task_upload_dir(task_id: int) -> str:
    """Resolve and create a task upload directory inside the base directory."""
    base_dir = os.path.realpath(settings.UPLOAD_DIR)
    task_dir = os.path.realpath(os.path.join(base_dir, str(task_id)))
    if os.path.commonpath([base_dir, task_dir]) != base_dir:
        raise HTTPException(status_code=400, detail="Invalid upload path")
    os.makedirs(task_dir, exist_ok=True)
    return task_dir


async def read_upload(file: UploadFile, user_id: int) -> UploadedFile:
    """Read, bound, checksum and scan an upload before persisting it."""
    filename = sanitize_filename(file.filename)
    extension, mime_type = validate_upload_type(filename, file.content_type)

    # An early check avoids obvious oversized uploads, but the streaming loop
    # below is the authoritative limit because file.size can be missing or lie.
    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=HTTP_413_TOO_LARGE,
            detail="File too large. Maximum size is 10MB.",
        )

    contents = bytearray()
    try:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            contents.extend(chunk)
            if len(contents) > settings.MAX_UPLOAD_SIZE:
                raise HTTPException(
                    status_code=HTTP_413_TOO_LARGE,
                    detail="File too large. Maximum size is 10MB.",
                )
    finally:
        await file.close()

    if not contents:
        raise HTTPException(status_code=400, detail="Empty files are not allowed")

    checksum = hashlib.sha256(contents).hexdigest()
    try:
        validate_file_signature(bytes(contents), extension)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc

    try:
        await asyncio.to_thread(scan_upload, bytes(contents))
    except MalwareDetected as exc:
        logger.warning(
            "attachment_malware_rejected",
            user_id=user_id,
            filename=filename,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="File was rejected by the malware scanner",
        ) from exc
    except ScannerUnavailable as exc:
        logger.warning("attachment_scan_unavailable", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Malware scanning is temporarily unavailable",
        ) from exc

    return UploadedFile(
        filename=filename,
        extension=extension,
        mime_type=mime_type,
        content=bytes(contents),
        checksum=checksum,
    )


async def store_upload(
    db,
    task: models.Task,
    user_id: int,
    upload: UploadedFile,
) -> models.Attachment:
    """Persist the bytes and the attachment row, cleaning up on failure."""
    file_path = None
    content = None
    storage_key = None

    if settings.storage_backend == "insforge":
        storage = get_storage()
        if storage is None:  # pragma: no cover - config validation
            raise HTTPException(status_code=503, detail="Object storage is not configured")
        storage_key = storage.build_key(task.id, upload.extension)
        try:
            await asyncio.to_thread(
                storage.put,
                storage_key,
                upload.content,
                upload.mime_type,
                upload.filename,
            )
        except StorageError as exc:
            logger.warning("attachment_storage_failed", error=str(exc))
            raise HTTPException(status_code=503, detail="Object storage is unavailable") from exc
    elif settings.storage_backend == "database":
        # Persistent backend: the bytes live in PostgreSQL and survive
        # ephemeral filesystems such as Render's.
        content = upload.content
    else:
        task_dir = _task_upload_dir(task.id)
        storage_name = f"{uuid.uuid4().hex}{upload.extension}"
        file_path = os.path.join(task_dir, storage_name)
        with open(file_path, "wb") as destination:
            destination.write(upload.content)

    try:
        attachment = crud.create_attachment(
            db,
            task.id,
            user_id,
            upload.filename,
            file_path,
            len(upload.content),
            upload.mime_type,
            content=content,
            checksum=upload.checksum,
            storage_key=storage_key,
        )
    except Exception:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        if storage_key:
            storage = get_storage()
            if storage is not None:
                try:
                    storage.delete(storage_key)
                except StorageError:
                    pass
        raise

    crud.log_activity(
        db,
        "attachment",
        attachment.id,
        "uploaded",
        user_id,
        None,
        upload.filename,
    )
    return attachment
