"""Notification schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict

__all__ = [
    "NotificationType",
    "NotificationPreferences",
    "NotificationOut",
    "NotificationUpdate",
    "PaginatedNotificationResponse",
]


class NotificationType(str, Enum):
    """Notification types a user can mute."""

    assigned = "assigned"
    commented = "commented"
    mentioned = "mentioned"


class NotificationPreferences(BaseModel):
    """Per-user notification preferences.

    Only the listed types are muted; an empty list enables everything.
    """

    muted_types: list[NotificationType] = []


class NotificationOut(BaseModel):
    """
    Schema for notification response data.

    Used in notification list and update endpoints.

    Attributes:
        id (int): Notification's unique identifier
        user_id (int): User who receives the notification
        type (str): Notification type
        entity_type (str): Related entity type
        entity_id (int): Related entity ID
        message (str): Human-readable message
        is_read (bool): Whether notification has been read
        created_at (datetime): Notification creation timestamp

    Config:
        from_attributes: Allows creation from ORM objects
    """

    id: int
    user_id: int
    type: str
    entity_type: str
    entity_id: int
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationUpdate(BaseModel):
    """
    Schema for updating notification read status.

    Used in PATCH /notifications/{id} endpoint.

    Attributes:
        is_read (bool): New read status
    """

    is_read: bool


class PaginatedNotificationResponse(BaseModel):
    """Paginated list of notifications."""

    items: list[NotificationOut]
    total: int
    page: int
    pages: int
    has_next: bool
