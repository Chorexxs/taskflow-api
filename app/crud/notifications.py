"""Notification queries."""

from sqlalchemy.orm import Session

from app import models, schemas
from app.events import notification_bus

from .users import get_user_by_id

__all__ = [
    "create_notification",
    "get_notifications_by_user",
    "count_unread_notifications",
    "get_notification_by_id",
    "mark_notification_read",
    "mark_all_notifications_read",
]


def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    entity_type: str,
    entity_id: int,
    message: str,
    dedupe_key: str | None = None,
):
    """
    Create a notification for a user.

    Notifications are created when events occur that the user should
    be aware of, such as being assigned to a task. Muted types are skipped and
    ``dedupe_key`` makes the call idempotent for the same event.

    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): ID of the user to notify.
        notification_type (str): Type of notification ("assigned", "commented", etc.)
        entity_type (str): Type of related entity.
        entity_id (int): ID of the related entity.
        message (str): Human-readable notification message.
        dedupe_key (str | None): Stable key for the event, unique per user/type.

    Returns:
        Notification | None: The created notification, the existing one for a
        repeated dedupe key, or ``None`` when the type is muted.

    Example:
        >>> create_notification(
        ...     db,
        ...     user_id=2,
        ...     notification_type="assigned",
        ...     entity_type="task",
        ...     entity_id=1,
        ...     message="You have been assigned to: Fix bug"
        ... )
    """
    user = get_user_by_id(db, user_id)
    if user is not None:
        muted = {
            value.strip()
            for value in (user.muted_notification_types or "").split(",")
            if value.strip()
        }
        if notification_type in muted:
            return None

    if dedupe_key:
        existing = (
            db.query(models.Notification)
            .filter(models.Notification.dedupe_key == dedupe_key)
            .first()
        )
        if existing is not None:
            return existing

    db_notification = models.Notification(
        user_id=user_id,
        type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        message=message,
        dedupe_key=dedupe_key,
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)

    notification_bus.publish(
        user_id,
        schemas.NotificationOut.model_validate(db_notification).model_dump(mode="json"),
    )
    return db_notification


def get_notifications_by_user(
    db: Session,
    user_id: int,
    is_read: bool | None = None,
    page: int = 1,
    page_size: int = 20,
):
    """
    Get a page of notifications for a user, optionally filtered by read status.

    Returns a pagination envelope compatible with the rest of the API.
    """
    query = db.query(models.Notification).filter(models.Notification.user_id == user_id)
    if is_read is not None:
        query = query.filter(models.Notification.is_read == is_read)

    total = query.count()
    pages = (total + page_size - 1) // page_size if total else 0
    items = (
        query.order_by(models.Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "has_next": page < pages,
    }


def count_unread_notifications(db: Session, user_id: int) -> int:
    """Return the number of unread notifications for a user."""
    return (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == user_id,
            models.Notification.is_read.is_(False),
        )
        .count()
    )


def get_notification_by_id(db: Session, notification_id: int):
    """
    Retrieve a notification by its ID.

    Args:
        db (Session): SQLAlchemy database session.
        notification_id (int): The notification's unique identifier.

    Returns:
        Notification | None: The notification if found, None otherwise.
    """
    return db.query(models.Notification).filter(models.Notification.id == notification_id).first()


def mark_notification_read(db: Session, notification_id: int):
    """
    Mark a single notification as read.

    Args:
        db (Session): SQLAlchemy database session.
        notification_id (int): ID of the notification to mark as read.

    Returns:
        Notification | None: Updated notification, or None if not found.
    """
    db_notification = get_notification_by_id(db, notification_id)
    if db_notification:
        db_notification.is_read = True
        db.commit()
        db.refresh(db_notification)
    return db_notification


def mark_all_notifications_read(db: Session, user_id: int):
    """
    Mark all notifications for a user as read.

    Uses a bulk update operation for efficiency.

    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): ID of the user.

    Returns:
        None: This function doesn't return anything.

    Example:
        >>> mark_all_notifications_read(db, user_id=1)
    """
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id, models.Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
