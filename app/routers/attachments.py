"""
TaskFlow API - Attachments Router

This module handles file attachment endpoints for tasks:
- POST /: Upload a file attachment
- GET /: List all attachments for a task
- DELETE /{attachment_id}: Delete an attachment
- GET /{attachment_id}/download: Download an attachment

File uploads are limited to 10MB. Files are stored on disk with
metadata in the database.
"""

import os

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.dependencies import get_current_team_member
from app.idempotency import IdempotencyGuard, get_idempotency_guard
from app.logging_config import get_logger
from app.rate_limit import rate_limit
from app.services import attachments as attachments_service
from app.storage import StorageError, get_storage

router = APIRouter()
logger = get_logger(__name__)


def get_task_from_params(
    db: Session, team_id_or_slug: str, project_id_or_name: str, task_id_or_title: str
):
    """
    Resolve task from URL parameters.

    Helper function that combines team, project, and task resolution.

    Args:
        db (Session): SQLAlchemy database session.
        team_id_or_slug (str): The team identifier.
        project_id_or_name (str): The project identifier.
        task_id_or_title (str): The task identifier.

    Returns:
        Task: The resolved Task object.
    """
    from app.dependencies import get_team_from_id_or_slug
    from app.routers.tasks import get_project_from_id_or_name, get_task_from_id_or_title

    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    return task


@router.post("/", response_model=schemas.AttachmentOut, status_code=status.HTTP_201_CREATED)
@rate_limit("20/minute")
async def upload_attachment(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
    guard: IdempotencyGuard = Depends(get_idempotency_guard),
):
    """
    Upload a file attachment to a task.
    
    Accepts file uploads up to 10MB. Files are stored in the
    uploads directory with task-specific subdirectories.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        file (UploadFile): The file to upload.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user (uploader).
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        AttachmentOut: The created attachment metadata.
    
    Raises:
        HTTPException 413: If file exceeds 10MB limit.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/teams/1/projects/1/tasks/1/attachments/ \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -F "file=@document.pdf"
    """
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    upload = await attachments_service.read_upload(file, current_user.id)

    # The file hash is part of the fingerprint: retrying the same upload returns
    # the original attachment instead of storing the bytes again.
    if (
        replay := guard.replay({"filename": upload.filename, "checksum": upload.checksum})
    ) is not None:
        return replay

    attachment = await attachments_service.store_upload(db, task, current_user.id, upload)

    guard.store(status.HTTP_201_CREATED, schemas.AttachmentOut.model_validate(attachment))
    return attachment


@router.get("/", response_model=schemas.PaginatedAttachmentResponse)
def list_attachments(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    List all attachments for a task.

    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).

    Returns:
        PaginatedAttachmentResponse: Page of attachments for the task.
    """
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    items, total, pages = crud.get_attachments_by_task_paginated(db, task.id, page, page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "has_next": page < pages,
    }


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: int,
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    Delete an attachment.

    Only the uploader or a team admin can delete attachments.
    This removes both the database record and the file from disk.

    Args:
        attachment_id (int): ID of the attachment to delete.
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).

    Returns:
        None: Returns 204 No Content on success.

    Raises:
        HTTPException 404: If attachment not found or doesn't belong to task.
        HTTPException 403: If user is not uploader or admin.
    """
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    attachment = crud.get_attachment_by_id(db, attachment_id)

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if attachment.task_id != task.id:
        raise HTTPException(status_code=404, detail="Attachment does not belong to this task")

    # Check permissions: uploader or admin can delete
    if attachment.uploaded_by != current_user.id and member.role != "admin":
        raise HTTPException(
            status_code=403, detail="Only the uploader or team admin can delete this attachment"
        )

    # Remove the local file or object when this attachment uses external storage.
    if attachment.storage_key:
        storage = get_storage()
        if storage is not None:
            try:
                storage.delete(attachment.storage_key)
            except StorageError as exc:
                # The database row is still deleted; the orphan is reported.
                logger.warning("attachment_delete_failed", error=str(exc))
        else:
            logger.warning("attachment_storage_not_configured", attachment_id=attachment.id)
    elif attachment.file_path and os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)

    # Log and delete
    crud.log_activity(
        db, "attachment", attachment.id, "deleted", current_user.id, attachment.filename, None
    )
    crud.delete_attachment(db, attachment.id)


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    Download an attachment.

    Returns the file as a downloadable response with proper
    content-disposition header.

    Args:
        attachment_id (int): ID of the attachment to download.
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).

    Returns:
        FileResponse: The file for download.

    Raises:
        HTTPException 404: If attachment not found or file doesn't exist.
    """
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    attachment = crud.get_attachment_by_id(db, attachment_id)

    if not attachment or attachment.task_id != task.id:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if attachment.storage_key:
        storage = get_storage()
        if storage is not None:
            try:
                data = storage.get(attachment.storage_key)
            except StorageError as exc:
                # Fall back to the retained database/local copy during rollout
                # or if object storage is temporarily unavailable.
                logger.warning("attachment_download_failed", error=str(exc))
            else:
                safe_name = attachment.filename.replace('"', "")
                return Response(
                    content=data,
                    media_type=attachment.mime_type,
                    headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
                )
        else:
            logger.warning("attachment_storage_not_configured", attachment_id=attachment.id)

    if attachment.content is not None:
        safe_name = attachment.filename.replace('"', "")
        return Response(
            content=attachment.content,
            media_type=attachment.mime_type,
            headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
        )

    if not attachment.file_path or not os.path.exists(attachment.file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=attachment.file_path, filename=attachment.filename, media_type=attachment.mime_type
    )
