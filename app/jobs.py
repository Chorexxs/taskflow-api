"""Retention housekeeping (Q-08, T-098).

Notifications and activity logs grow without bound in an active team. Q-08
fixes the window at 90 days for notifications and one year for activity; this
module applies it idempotently so it can run at startup and from a scheduled
job.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import models
from app.config import settings


def purge_expired_data(
    db: Session,
    *,
    now: datetime | None = None,
    notification_days: int | None = None,
    activity_days: int | None = None,
) -> dict[str, int]:
    """Delete notifications and activity older than their retention window.

    Args:
        db (Session): Database session.
        now (datetime | None): Reference instant; defaults to UTC now.
        notification_days (int | None): Override ``NOTIFICATION_RETENTION_DAYS``.
        activity_days (int | None): Override ``ACTIVITY_RETENTION_DAYS``.

    Returns:
        dict[str, int]: ``{"notifications": n, "activity": m}`` deleted rows.
        Running the function twice is safe: the second call returns zeros.
    """
    reference = now or datetime.now(timezone.utc)
    notification_window = notification_days or settings.NOTIFICATION_RETENTION_DAYS
    activity_window = activity_days or settings.ACTIVITY_RETENTION_DAYS

    notification_cutoff = reference - timedelta(days=notification_window)
    activity_cutoff = reference - timedelta(days=activity_window)

    notifications_deleted = (
        db.query(models.Notification)
        .filter(models.Notification.created_at < notification_cutoff)
        .delete(synchronize_session=False)
    )
    activity_deleted = (
        db.query(models.ActivityLog)
        .filter(models.ActivityLog.created_at < activity_cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()

    return {"notifications": notifications_deleted, "activity": activity_deleted}
