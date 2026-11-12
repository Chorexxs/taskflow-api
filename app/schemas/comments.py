"""Comment schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from .common import sanitize_text
from .users import UserMini

__all__ = [
    "CommentCreate",
    "CommentUpdate",
    "CommentOut",
    "PaginatedCommentResponse",
]


class CommentCreate(BaseModel):
    """
    Schema for creating a comment.

    Used in POST /tasks/{id}/comments endpoint.

    Attributes:
        content (str): Comment text (required)

    Validators:
        sanitize_input: Removes control characters from text
    """

    content: str

    @field_validator("content", mode="before")
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class CommentUpdate(BaseModel):
    """
    Schema for updating a comment.

    Used in PATCH /tasks/{id}/comments/{id} endpoint.

    Attributes:
        content (str): New comment text

    Validators:
        sanitize_input: Removes control characters from text
    """

    content: str

    @field_validator("content", mode="before")
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class CommentOut(BaseModel):
    """
    Schema for comment response data.

    Used in comment list and detail endpoints.

    Attributes:
        id (int): Comment's unique identifier
        task_id (int): Task the comment belongs to
        author_id (int): User who wrote the comment
        author (UserMini | None): Author user details
        content (str): Comment text
        created_at (datetime): Comment creation timestamp
        updated_at (datetime): Last update timestamp

    Config:
        from_attributes: Allows creation from ORM objects
    """

    id: int
    task_id: int
    author_id: int
    author: UserMini | None = None
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedCommentResponse(BaseModel):
    """Paginated list of comments."""

    items: list[CommentOut]
    total: int
    page: int
    pages: int
    has_next: bool
