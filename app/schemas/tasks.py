"""Task schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import sanitize_text
from .users import UserMini

__all__ = [
    "TaskStatus",
    "TaskPriority",
    "TaskCreate",
    "TaskUpdate",
    "TaskAssign",
    "TaskStatusUpdate",
    "TaskOut",
    "PaginatedTaskResponse",
]


class TaskStatus(str, Enum):
    """
    Enum representing task status.

    Attributes:
        todo: Task needs to be done
        in_progress: Task is being worked on
        done: Task is completed
    """

    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(str, Enum):
    """
    Enum representing task priority.

    Attributes:
        low: Low priority task
        medium: Medium priority task
        high: High priority task
    """

    low = "low"
    medium = "medium"
    high = "high"


class TaskCreate(BaseModel):
    """
    Schema for task creation.

    Used in POST /teams/{id}/projects/{id}/tasks endpoint.

    Attributes:
        title (str): Task title (required)
        description (str | None): Task description
        priority (TaskPriority): Task priority (default: medium)
        due_date (datetime | None): Optional due date
        assigned_to (int | None): User ID to assign the task to

    Validators:
        sanitize_input: Removes control characters from text fields

    Example:
        >>> task = TaskCreate(
        ...     title="Fix login bug",
        ...     description="Users cannot login with special characters",
        ...     priority=TaskPriority.high,
        ...     assigned_to=123
        ... )
    """

    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.medium
    due_date: datetime | None = None
    assigned_to: int | None = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class TaskUpdate(BaseModel):
    """
    Schema for task updates.

    Used in PATCH /teams/{id}/projects/{id}/tasks/{id} endpoint.
    All fields are optional - only included fields are updated.

    Attributes:
        title (str | None): New task title
        description (str | None): New task description
        status (TaskStatus | None): New task status
        priority (TaskPriority | None): New task priority
        due_date (datetime | None): New due date

    Validators:
        sanitize_input: Removes control characters from text fields
    """

    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None

    @field_validator("title", "description", mode="before")
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class TaskAssign(BaseModel):
    """
    Schema for assigning a task to a user.

    Used in PATCH /teams/{id}/projects/{id}/tasks/{id}/assign endpoint.

    Attributes:
        user_id (int | None): User ID to assign. None to unassign.

    Example:
        >>> # Assign to user
        >>> TaskAssign(user_id=123)
        >>> # Unassign
        >>> TaskAssign(user_id=None)
    """

    user_id: int | None = None


class TaskStatusUpdate(BaseModel):
    """Payload for the dedicated Kanban status endpoint.

    Only ``status`` and the optional ``position`` are accepted, so a member
    cannot smuggle other task edits through the status-only permission. Used in
    ``PATCH .../tasks/{id}/status``.

    ``position`` is a fractional index: clients send the midpoint between the
    neighbours where the card was dropped. When omitted, the task is appended
    to the end of the destination column.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    status: TaskStatus
    position: float | None = Field(default=None, ge=-1_000_000_000, le=1_000_000_000)


class TaskOut(BaseModel):
    """
    Schema for task response data.

    Used in task list, detail, and creation endpoints.
    Includes assignee information for displaying task ownership.

    Attributes:
        id (int): Task's unique identifier
        project_id (int): Project the task belongs to
        title (str): Task title
        description (str | None): Task description
        status (TaskStatus): Task status
        priority (TaskPriority): Task priority
        assigned_to (int | None): User ID of assignee
        assignee (UserMini | None): Full assignee user object
        due_date (datetime | None): Task due date
        position (float): Stable order inside the Kanban column
        created_by (int): ID of user who created the task
        created_at (datetime): Task creation timestamp
        updated_at (datetime): Last update timestamp

    Config:
        from_attributes: Allows creation from ORM objects
    """

    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assigned_to: int | None
    assignee: UserMini | None
    due_date: datetime | None
    position: float
    created_by: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedTaskResponse(BaseModel):
    """
    Schema for paginated task list response.

    Used in GET /tasks endpoint for paginated results.

    Attributes:
        items (list[TaskOut]): List of tasks for the current page
        total (int): Total number of tasks matching the query
        page (int): Current page number
        pages (int): Total number of pages
        has_next (bool | None): Whether there's a next page
        next_cursor (str | None): Cursor for next page (if using cursor pagination)
    """

    items: list[TaskOut]
    total: int
    page: int
    pages: int
    has_next: bool | None = None
    next_cursor: str | None = None
