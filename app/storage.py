"""Object storage for attachment blobs (T-053/T-054).

The default deployment keeps bytes in PostgreSQL (``STORAGE_BACKEND=database``)
and development can use the filesystem (``local``). Production can offload
blobs to InsForge Storage (``insforge``), which exposes a bucket-based,
S3-compatible object API and keeps the API servers stateless.

Only the ``insforge`` backend is implemented here; the router keeps handling
the database/local bytes directly because they live in the database row or on
disk. ``get_storage()`` returns ``None`` for those backends.
"""

from __future__ import annotations

import os
import uuid
from typing import Any
from urllib.parse import quote

import httpx

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

CONNECT_TIMEOUT = 10.0
READ_TIMEOUT = 60.0


def _absolute(base_url: str, url: str) -> str:
    return url if url.startswith(("http://", "https://")) else f"{base_url}{url}"


class StorageError(RuntimeError):
    """Raised when the object storage operation fails."""


class StorageService:
    """InsForge Storage (bucket) backend for attachment objects."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        bucket: str | None = None,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = (base_url or settings.INSFORGE_URL).rstrip("/")
        self.api_key = api_key or settings.INSFORGE_API_KEY
        self.bucket = bucket or settings.INSFORGE_STORAGE_BUCKET
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=httpx.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT),
            follow_redirects=True,
        )
        if not self.base_url or not self.api_key or not self.bucket:
            raise StorageError(
                "INSFORGE_URL, INSFORGE_API_KEY and INSFORGE_STORAGE_BUCKET "
                "are required for the insforge storage backend"
            )

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _object_path(self, key: str) -> str:
        return quote(key.lstrip("/"), safe="/")

    def build_key(self, task_id: int, extension: str, filename: str | None = None) -> str:
        """Return a unique object key for a task attachment."""
        suffix = extension if extension.startswith(".") else f".{extension}" if extension else ""
        return f"attachments/{task_id}/{uuid.uuid4().hex}{suffix}"

    def put(self, key: str, data: bytes, content_type: str, filename: str | None = None) -> None:
        """Upload ``data`` to the bucket, handling both direct and presigned modes."""
        object_key = key.lstrip("/")
        try:
            strategy = self._client.post(
                f"{self.base_url}/api/storage/buckets/{self.bucket}/upload-strategy",
                headers=self._headers,
                json={
                    "filename": object_key,
                    "contentType": content_type,
                    "size": len(data),
                },
            )
            strategy.raise_for_status()
            plan: dict[str, Any] = strategy.json()
            method = plan.get("method")
            upload_url = _absolute(self.base_url, plan["uploadUrl"])

            if method == "direct":
                response = self._client.put(
                    upload_url,
                    headers=self._headers,
                    files={"file": (filename or object_key, data, content_type)},
                )
            else:
                # S3 presigned POST: every policy field first, file last.
                files = [
                    (name, (None, str(value))) for name, value in (plan.get("fields") or {}).items()
                ]
                files.append(("file", (filename or object_key, data, content_type)))
                response = self._client.post(upload_url, files=files)
            response.raise_for_status()

            if plan.get("confirmRequired") and plan.get("confirmUrl"):
                confirm = self._client.post(
                    _absolute(self.base_url, plan["confirmUrl"]),
                    headers=self._headers,
                    json={"size": len(data)},
                )
                confirm.raise_for_status()
        except (httpx.HTTPError, KeyError, TypeError) as exc:
            raise StorageError(f"Could not store object {object_key}") from exc

    def get(self, key: str) -> bytes:
        """Download an object's bytes."""
        object_key = self._object_path(key)
        try:
            strategy = self._client.get(
                f"{self.base_url}/api/storage/buckets/{self.bucket}"
                f"/download-strategy/objects/{object_key}",
                headers=self._headers,
            )
            strategy.raise_for_status()
            url = _absolute(self.base_url, strategy.json()["url"])
            # A presigned S3 URL must not receive the InsForge Authorization
            # header: it would invalidate the signature.
            headers = self._headers if url.startswith(self.base_url) else {}
            response = self._client.get(url, headers=headers)
            response.raise_for_status()
            return response.content
        except (httpx.HTTPError, KeyError, TypeError) as exc:
            raise StorageError(f"Could not read object {key}") from exc

    def delete(self, key: str) -> None:
        """Delete an object; a missing object is treated as success."""
        object_key = self._object_path(key)
        try:
            response = self._client.delete(
                f"{self.base_url}/api/storage/buckets/{self.bucket}/objects/{object_key}",
                headers=self._headers,
            )
            if response.status_code not in (200, 204, 404):
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise StorageError(f"Could not delete object {key}") from exc

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


_service: StorageService | None = None


def get_storage() -> StorageService | None:
    """Return the object storage service when InsForge is configured.

    It is also returned when the active backend is ``database``/``local`` so
    attachments already migrated to object storage remain downloadable after a
    rollback. Callers decide whether to write to it based on
    ``settings.storage_backend``.
    """
    global _service
    configured = bool(
        settings.INSFORGE_URL.strip()
        and settings.INSFORGE_API_KEY.strip()
        and settings.INSFORGE_STORAGE_BUCKET.strip()
    )
    if _service is None and configured:
        _service = StorageService()
    return _service


def reset_storage() -> None:
    """Drop the cached service (used by tests after changing settings)."""
    global _service
    if _service is not None:
        _service.close()
    _service = None


def attachment_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()
