"""Attachment metadata queries."""

from sqlalchemy.orm import Session

from app import models

from ._common import paginate_query

__all__ = [
    "create_attachment",
    "get_attachment_by_id",
    "get_attachments_by_task",
    "get_attachments_by_task_paginated",
    "delete_attachment",
]


def create_attachment(
    db: Session,
    task_id: int,
    user_id: int,
    filename: str,
    file_path: str | None,
    file_size: int,
    mime_type: str,
    content: bytes | None = None,
    checksum: str | None = None,
    storage_key: str | None = None,
):
    """
    Create an attachment record for an uploaded file.

    Note: This only creates the database record. The actual file
    should be saved to disk separately.

    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task to attach the file to.
        user_id (int): ID of the user uploading the file.
        filename (str): Original filename.
        file_path (str): Path where the file is stored.
        file_size (int): Size of the file in bytes.
        mime_type (str): MIME type of the file.

    Returns:
        Attachment: The newly created attachment record.

    Example:
        >>> create_attachment(
        ...     db, task_id=1, user_id=1,
        ...     filename="document.pdf",
        ...     file_path="/uploads/123_document.pdf",
        ...     file_size=1024000,
        ...     mime_type="application/pdf"
        ... )
    """
    db_attachment = models.Attachment(
        task_id=task_id,
        uploaded_by=user_id,
        filename=filename,
        file_path=file_path,
        storage_key=storage_key,
        content=content,
        checksum=checksum,
        file_size=file_size,
        mime_type=mime_type,
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment


def get_attachment_by_id(db: Session, attachment_id: int):
    """
    Retrieve an attachment by its ID.

    Args:
        db (Session): SQLAlchemy database session.
        attachment_id (int): The attachment's unique identifier.

    Returns:
        Attachment | None: The attachment if found, None otherwise.
    """
    return db.query(models.Attachment).filter(models.Attachment.id == attachment_id).first()


def get_attachments_by_task(db: Session, task_id: int):
    """
    Get all attachments for a task.

    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task.

    Returns:
        list[Attachment]: List of attachments for the task.
    """
    return db.query(models.Attachment).filter(models.Attachment.task_id == task_id).all()


def get_attachments_by_task_paginated(db: Session, task_id: int, page: int, page_size: int):
    """Return a page of attachments, ordered by upload time."""
    query = (
        db.query(models.Attachment)
        .filter(models.Attachment.task_id == task_id)
        .order_by(models.Attachment.id)
    )
    return paginate_query(query, page, page_size)


def delete_attachment(db: Session, attachment_id: int):
    """
    Delete an attachment record.

    Note: This only deletes the database record. The actual file
    should be deleted from disk separately.

    Args:
        db (Session): SQLAlchemy database session.
        attachment_id (int): ID of the attachment to delete.

    Returns:
        Attachment | None: The deleted attachment, or None if not found.
    """
    db_attachment = get_attachment_by_id(db, attachment_id)
    if db_attachment:
        db.delete(db_attachment)
        db.commit()
    return db_attachment
