"""Activity schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from .users import UserMini

__all__ = [
    "ActivityLogOut",
    "PaginatedActivityResponse",
]


class ActivityLogOut(BaseModel):
    """
    Schema for activity log response.

    Used in activity endpoints for tasks and projects.

    Attributes:
        id (int): Log entry ID
        entity_type (str): Type of entity (task, project, etc.)
        entity_id (int): ID of the entity
        action (str): Action performed
        changed_by (int): User who performed the action
        old_value (str | None): Previous value
        new_value (str | None): New value
        created_at (datetime): When the action occurred

    Config:
        from_attributes: Allows creation from ORM objects
    """

    id: int
    entity_type: str
    entity_id: int
    action: str
    changed_by: int
    actor: UserMini | None = None
    old_value: str | None
    new_value: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedActivityResponse(BaseModel):
    """Paginated list of activity entries."""

    items: list[ActivityLogOut]
    total: int
    page: int
    pages: int
    has_next: bool
