"""Attachment schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

__all__ = [
    "AttachmentOut",
    "PaginatedAttachmentResponse",
]


class AttachmentOut(BaseModel):
    """
    Schema for attachment response data.

    Used in attachment list and upload endpoints.

    Attributes:
        id (int): Attachment's unique identifier
        task_id (int): Task the attachment belongs to
        uploaded_by (int): User who uploaded the file
        filename (str): Original filename
        file_size (int): File size in bytes
        mime_type (str): MIME type of the file
        created_at (datetime): Upload timestamp

    Config:
        from_attributes: Allows creation from ORM objects
    """

    id: int
    task_id: int
    uploaded_by: int
    filename: str
    file_size: int
    mime_type: str
    checksum: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAttachmentResponse(BaseModel):
    """Paginated list of task attachments."""

    items: list[AttachmentOut]
    total: int
    page: int
    pages: int
    has_next: bool
