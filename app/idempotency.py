"""Idempotency support for critical POST endpoints (T-100).

Clients may send an ``Idempotency-Key`` header when creating a team, project,
task or comment. The first response is stored and replayed on retries with the
same key, so a timeout in the network never duplicates business objects.

Design notes:

- Keys are scoped per user and the request fingerprint includes method, path and
  JSON body. Reusing a key for a different request returns 422.
- A reservation row is committed before the handler runs. A concurrent retry
  gets 409 while the first request is still in flight; stale reservations
  (crashed process) are taken over after ``IN_FLIGHT_TIMEOUT_SECONDS``.
- Only successful responses are stored. If the handler raises, the reservation
  is deleted so the client can retry with the same key and a different body.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.auth import get_current_user
from app.config import settings
from app.database import get_db

IDEMPOTENCY_HEADER = "Idempotency-Key"
REPLAY_HEADER = "Idempotent-Replayed"
IN_FLIGHT_TIMEOUT_SECONDS = 60
_KEY_PATTERN = re.compile(r"[\x21-\x7e]{1,255}")


def _as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes even for timezone-aware columns."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _serialize(payload: Any) -> Any:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(mode="json")
    return payload


def request_fingerprint(method: str, path: str, payload: Any) -> str:
    """Hash the request so a key cannot be reused for another operation."""
    canonical = json.dumps(
        {"method": method, "path": path, "body": _serialize(payload)},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyGuard:
    """Lifecycle helper injected into idempotent endpoints."""

    def __init__(
        self,
        *,
        db: Session,
        user_id: int,
        key: str | None,
        method: str,
        path: str,
    ) -> None:
        self.db = db
        self.user_id = user_id
        self.key = key
        self.method = method
        self.path = path
        self.request_hash: str | None = None
        self.record: models.IdempotencyKey | None = None

    # ------------------------------------------------------------------ public
    def replay(self, payload: Any) -> Response | None:
        """Return the stored response, reserve the key, or raise on misuse."""
        if self.key is None:
            return None
        if not _KEY_PATTERN.fullmatch(self.key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Idempotency-Key must be 1-255 visible ASCII characters",
            )
        self.request_hash = request_fingerprint(self.method, self.path, payload)

        record = self._find()
        if record is not None:
            return self._handle_existing(record)
        return self._reserve()

    def store(self, status_code: int, body: Any) -> None:
        """Persist a successful response for later replays."""
        if self.record is None:
            return
        payload = _serialize(body)
        record: Any = self.record
        record.status_code = status_code
        record.response_body = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
        record.completed_at = datetime.now(timezone.utc)
        self.db.commit()

    def release(self) -> None:
        """Drop the reservation so a failed request can be retried."""
        if self.record is None:
            return
        try:
            self.db.delete(self.record)
            self.db.commit()
        except Exception:  # pragma: no cover - defensive cleanup
            self.db.rollback()
        finally:
            self.record = None

    # ----------------------------------------------------------------- private
    def _find(self) -> models.IdempotencyKey | None:
        record = (
            self.db.query(models.IdempotencyKey)
            .filter(
                models.IdempotencyKey.user_id == self.user_id,
                models.IdempotencyKey.key == self.key,
            )
            .one_or_none()
        )
        if record is None:
            return None
        if self._expired(record):
            self.db.delete(record)
            self.db.commit()
            return None
        return record

    def _expired(self, record: models.IdempotencyKey) -> bool:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.IDEMPOTENCY_KEY_TTL_HOURS)
        return _as_utc(record.created_at) < cutoff

    def _is_stale(self, record: models.IdempotencyKey) -> bool:
        stale_after = datetime.now(timezone.utc) - timedelta(seconds=IN_FLIGHT_TIMEOUT_SECONDS)
        return _as_utc(record.created_at) < stale_after

    def _handle_existing(self, record: models.IdempotencyKey) -> Response | None:
        if record.request_hash != self.request_hash:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=("Idempotency-Key was already used with a different request"),
            )
        if record.status_code is not None:
            body = json.loads(record.response_body or "null")
            return JSONResponse(
                status_code=record.status_code,
                content=body,
                headers={REPLAY_HEADER: "true"},
            )
        if self._is_stale(record):
            # The previous request died before storing a response.
            self.db.delete(record)
            self.db.commit()
            return self._reserve()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A request with this Idempotency-Key is still in progress",
        )

    def _reserve(self) -> Response | None:
        record = models.IdempotencyKey(
            user_id=self.user_id,
            key=self.key,
            method=self.method,
            path=self.path,
            request_hash=self.request_hash,
        )
        self.db.add(record)
        try:
            self.db.commit()
        except IntegrityError:
            # Another request reserved the same key between our lookup and insert.
            self.db.rollback()
            existing = self._find()
            if existing is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Idempotency-Key conflict; retry the request",
                ) from None
            return self._handle_existing(existing)
        self.record = record
        return None


def get_idempotency_guard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    idempotency_key: Annotated[str | None, Header(alias=IDEMPOTENCY_HEADER)] = None,
) -> Iterator[IdempotencyGuard]:
    """FastAPI dependency that releases failed reservations automatically."""
    guard = IdempotencyGuard(
        db=db,
        user_id=current_user.id,
        key=idempotency_key,
        method=request.method,
        path=request.url.path,
    )
    try:
        yield guard
    except Exception:
        guard.release()
        raise
