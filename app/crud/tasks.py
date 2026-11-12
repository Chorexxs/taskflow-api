"""Task queries and Kanban ordering."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app import models, schemas

POSITION_GAP = Decimal("1024")

__all__ = [
    "create_task",
    "get_task_by_id",
    "get_tasks_by_project",
    "update_task",
    "update_task_status",
    "assign_task",
    "delete_task",
]


def _next_task_position(db: Session, project_id: int, status: str) -> Decimal:
    """Return the position that appends a task to the end of a column."""
    current_max = (
        db.query(func.max(models.Task.position))
        .filter(
            models.Task.project_id == project_id,
            models.Task.status == status,
        )
        .scalar()
    )
    if current_max is None:
        return POSITION_GAP
    return Decimal(str(current_max)) + POSITION_GAP


def create_task(db: Session, task: schemas.TaskCreate, project_id: int, user_id: int):
    """
    Create a new task within a project.

    Creates a task with the given title, description, priority, and optional
    due date and assignee. The task is created with status "todo" at the end of
    that Kanban column.

    Args:
        db (Session): SQLAlchemy database session.
        task (TaskCreate): Schema with task details.
        project_id (int): ID of the project to create the task in.
        user_id (int): ID of the user creating the task.

    Returns:
        Task: The newly created task object.

    Example:
        >>> task_data = TaskCreate(
        ...     title="Fix bug",
        ...     description="Login issue",
        ...     priority=TaskPriority.high,
        ...     assigned_to=2
        ... )
        >>> new_task = create_task(db, task_data, project_id=1, user_id=1)
    """
    db_task = models.Task(
        project_id=project_id,
        title=task.title,
        description=task.description,
        priority=task.priority.value,
        due_date=task.due_date,
        position=_next_task_position(db, project_id, "todo"),
        created_by=user_id,
        assigned_to=task.assigned_to,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task_by_id(db: Session, task_id: int):
    """
    Retrieve a task by its ID with assignee loaded.

    Uses joinedload to eagerly load the assignee relationship,
    preventing N+1 queries when accessing task.assignee.

    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): The task's unique identifier.

    Returns:
        Task | None: The task with assignee loaded, or None if not found.

    Example:
        >>> task = get_task_by_id(db, 1)
        >>> print(task.assignee.email)  # No additional query
    """
    return (
        db.query(models.Task)
        .options(joinedload(models.Task.assignee))
        .filter(models.Task.id == task_id)
        .first()
    )


def get_tasks_by_project(
    db: Session,
    project_id: int,
    status: str | None = None,
    priority: str | None = None,
    assigned_to: int | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
):
    """
    Get paginated and filtered tasks for a project.

    This is the main function for listing tasks. Supports:
    - Filtering by status, priority, assignee, due dates
    - Sorting by multiple fields
    - Pagination with configurable page size

    Uses joinedload to prevent N+1 queries on assignee.

    Args:
        db (Session): SQLAlchemy database session.
        project_id (int): ID of the project.
        status (str | None): Filter by status ("todo", "in_progress", "done").
        priority (str | None): Filter by priority ("low", "medium", "high").
        assigned_to (int | None): Filter by assignee user ID.
        due_before (datetime | None): Filter tasks due before this date.
        due_after (datetime | None): Filter tasks due after this date.
        sort_by (str): Field to sort by ("created_at", "title", "priority", "due_date", "status", "position").
        order (str): Sort order ("asc" or "desc").
        page (int): Page number (1-indexed).
        page_size (int): Items per page (max 100).

    Returns:
        dict: Dictionary with items (list of tasks), total count, page info.

    Example:
        >>> result = get_tasks_by_project(
        ...     db, project_id=1,
        ...     status="todo",
        ...     priority="high",
        ...     sort_by="due_date",
        ...     order="asc",
        ...     page=1,
        ...     page_size=10
        ... )
        >>> print(result["total"])  # Total matching tasks
    """
    query = (
        db.query(models.Task)
        .options(joinedload(models.Task.assignee))
        .filter(models.Task.project_id == project_id)
    )

    # Apply filters
    if status:
        query = query.filter(models.Task.status == status)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if assigned_to is not None:
        query = query.filter(models.Task.assigned_to == assigned_to)
    if due_before:
        query = query.filter(models.Task.due_date <= due_before)
    if due_after:
        query = query.filter(models.Task.due_date >= due_after)

    # Determine sort column
    order_col: Any
    if sort_by == "title":
        order_col = models.Task.title
    elif sort_by == "due_date":
        order_col = models.Task.due_date
    elif sort_by == "priority":
        order_col = models.Task.priority
    elif sort_by == "status":
        order_col = models.Task.status
    elif sort_by == "position":
        order_col = models.Task.position
    else:
        order_col = models.Task.created_at

    # Apply sorting. Kanban order needs a deterministic tiebreaker so cards
    # with the same position never jump between requests.
    if order == "asc":
        query = query.order_by(order_col.asc(), models.Task.id.asc())
    else:
        query = query.order_by(order_col.desc(), models.Task.id.desc())

    # Get total count (before pagination)
    total = query.count()

    # Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size,
    }


def update_task(db: Session, task_id: int, task_update: schemas.TaskUpdate):
    """
    Update a task's details.

    Only updates fields that are provided (not None). Supports updating
    title, description, status, priority, and due_date.

    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task to update.
        task_update (TaskUpdate): Schema with fields to update.

    Returns:
        Task | None: Updated task, or None if not found.

    Example:
        >>> update = TaskUpdate(status=TaskStatus.done, priority=TaskPriority.low)
        >>> updated = update_task(db, 1, update)
    """
    db_task = get_task_by_id(db, task_id)
    if not db_task:
        return None
    if task_update.title is not None:
        db_task.title = task_update.title
    if task_update.description is not None:
        db_task.description = task_update.description
    if task_update.status is not None:
        db_task.status = task_update.status.value
    if task_update.priority is not None:
        db_task.priority = task_update.priority.value
    if task_update.due_date is not None:
        db_task.due_date = task_update.due_date
    db.commit()
    db.refresh(db_task)
    return db_task


def update_task_status(
    db: Session,
    task_id: int,
    new_status: schemas.TaskStatus,
    changed_by: int,
    position: float | None = None,
):
    """Change a task's Kanban status and position in one transaction.

    When ``position`` is omitted and the column changes, the task is appended to
    the end of the destination column. When the status does not change the call
    only reorders the task.

    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task to move.
        new_status (TaskStatus): Destination column.
        changed_by (int): User performing the move.
        position (float | None): Explicit fractional position inside the column.

    Returns:
        Task | None: Updated task, or ``None`` if it does not exist.
    """
    db_task = get_task_by_id(db, task_id)
    if not db_task:
        return None
    old_status = db_task.status
    target_status = new_status.value

    if position is not None:
        db_task.position = Decimal(str(position))
    elif target_status != old_status:
        db_task.position = _next_task_position(db, db_task.project_id, target_status)

    db_task.status = target_status

    if target_status != old_status:
        db.add(
            models.ActivityLog(
                entity_type="task",
                entity_id=db_task.id,
                action="updated_status",
                changed_by=changed_by,
                old_value=old_status,
                new_value=target_status,
            )
        )
    db.commit()
    db.refresh(db_task)
    return db_task


def assign_task(db: Session, task_id: int, user_id: int | None):
    """
    Assign or unassign a task.

    Set user_id to a user ID to assign, or None to unassign.

    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task.
        user_id (int | None): User ID to assign, or None to unassign.

    Returns:
        Task | None: Updated task, or None if not found.

    Example:
        >>> # Assign to user
        >>> assign_task(db, task_id=1, user_id=2)
        >>> # Unassign
        >>> assign_task(db, task_id=1, user_id=None)
    """
    db_task = get_task_by_id(db, task_id)
    if db_task:
        db_task.assigned_to = user_id
        db.commit()
        db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int):
    """
    Delete a task.

    Permanently removes the task from the database. This also deletes
    associated comments, attachments, and activity logs due to CASCADE.

    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task to delete.

    Returns:
        Task | None: The deleted task, or None if not found.

    Example:
        >>> delete_task(db, task_id=1)
    """
    db_task = get_task_by_id(db, task_id)
    if db_task:
        db.delete(db_task)
        db.commit()
    return db_task
