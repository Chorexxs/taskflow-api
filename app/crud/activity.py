"""Activity log queries."""

from sqlalchemy.orm import Session, selectinload

from app import models

__all__ = [
    "log_activity",
    "get_activity_by_task",
    "get_activity_by_project",
]


def log_activity(
    db: Session,
    entity_type: str,
    entity_id: int,
    action: str,
    user_id: int,
    old_value: str | None = None,
    new_value: str | None = None,
):
    """
    Create an activity log entry for audit purposes.

    Records actions performed on entities like tasks, projects, and teams.
    The old_value and new_value fields store string representations
    of the changes (e.g., JSON for complex values).

    Args:
        db (Session): SQLAlchemy database session.
        entity_type (str): Type of entity ("task", "project", "team", etc.)
        entity_id (int): ID of the entity that was changed.
        action (str): Action performed ("created", "updated", "assigned", etc.)
        user_id (int): ID of the user who performed the action.
        old_value (str | None): Previous value as string.
        new_value (str | None): New value as string.

    Returns:
        ActivityLog: The newly created activity log entry.

    Example:
        >>> log_activity(
        ...     db,
        ...     entity_type="task",
        ...     entity_id=1,
        ...     action="assigned",
        ...     user_id=1,
        ...     old_value=None,
        ...     new_value="user@example.com"
        ... )
    """
    db_activity = models.ActivityLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changed_by=user_id,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(db_activity)
    db.commit()
    return db_activity


def _paginate_activity(query, page: int, page_size: int):
    total = query.count()
    pages = (total + page_size - 1) // page_size if total else 0
    items = (
        query.order_by(models.ActivityLog.created_at.desc())
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


def get_activity_by_task(db: Session, task_id: int, page: int = 1, page_size: int = 20):
    """Get a page of activity logs for a task, newest first."""

    query = (
        db.query(models.ActivityLog)
        .options(selectinload(models.ActivityLog.user))
        .filter(
            models.ActivityLog.entity_type == "task",
            models.ActivityLog.entity_id == task_id,
        )
    )
    return _paginate_activity(query, page, page_size)


def get_activity_by_project(db: Session, project_id: int, page: int = 1, page_size: int = 20):
    """Get a page of activity logs for a project, newest first."""

    query = (
        db.query(models.ActivityLog)
        .options(selectinload(models.ActivityLog.user))
        .filter(
            models.ActivityLog.entity_type == "project",
            models.ActivityLog.entity_id == project_id,
        )
    )
    return _paginate_activity(query, page, page_size)
