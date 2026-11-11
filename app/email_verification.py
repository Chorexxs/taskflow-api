"""Single-use email verification tokens (T-113)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models
from app.config import settings


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def issue_token(db: Session, user: models.User) -> str:
    """Invalidate previous tokens and return a new raw verification token."""
    now = datetime.now(timezone.utc)
    (
        db.query(models.EmailVerificationToken)
        .filter(
            models.EmailVerificationToken.user_id == user.id,
            models.EmailVerificationToken.used_at.is_(None),
        )
        .delete(synchronize_session=False)
    )
    raw = secrets.token_urlsafe(32)
    db.add(
        models.EmailVerificationToken(
            user_id=user.id,
            token_hash=_hash(raw),
            expires_at=now + timedelta(hours=settings.EMAIL_VERIFICATION_TTL_HOURS),
        )
    )
    db.commit()
    return raw


def consume_token(db: Session, raw: str) -> models.User | None:
    """Mark a token as used and verify the user; returns None if invalid."""
    if not raw:
        return None
    record = (
        db.query(models.EmailVerificationToken)
        .filter(
            models.EmailVerificationToken.token_hash == _hash(raw),
            models.EmailVerificationToken.used_at.is_(None),
        )
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if record is None or _as_utc(record.expires_at) < now:
        return None

    user = db.query(models.User).filter(models.User.id == record.user_id).one_or_none()
    if user is None:
        return None
    record.used_at = now  # type: ignore[assignment]
    user.email_verified = True  # type: ignore[assignment]
    db.commit()
    return user
