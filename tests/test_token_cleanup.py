"""Expired revoked tokens must be pruned without touching live ones."""

from datetime import datetime, timedelta, timezone

from app.auth import clean_expired_tokens
from app.models import RevokedToken


def test_clean_expired_tokens_removes_only_expired_rows(db_session):
    now = datetime.now(timezone.utc)
    expired = RevokedToken(
        token="expired-token",
        token_type="access",
        expires_at=now - timedelta(minutes=1),
    )
    live = RevokedToken(
        token="live-token",
        token_type="access",
        expires_at=now + timedelta(minutes=10),
    )
    db_session.add_all([expired, live])
    db_session.commit()

    clean_expired_tokens(db_session)

    remaining = {row.token for row in db_session.query(RevokedToken).all()}
    assert remaining == {"live-token"}
