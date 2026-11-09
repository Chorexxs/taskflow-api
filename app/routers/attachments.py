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

import mimetypes
import os
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.dependencies import get_current_team_member

router = APIRouter()

# Upload limits and storage location come from central configuration.
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE
UPLOAD_DIR = settings.UPLOAD_DIR
CHUNK_SIZE = 1024 * 1024
HTTP_413_TOO_LARGE = getattr(status, "HTTP_413_CONTENT_TOO_LARGE", 413)

# Only allow a conservative, explicit set of characters in filenames.
_UNSAFE_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: str | None) -> str:
    """Return a safe, human-readable filename.

    The client-supplied filename is never trusted: path separators are
    stripped, control characters removed and everything outside a small
    allowlist collapsed to underscores.
    """
    candidate = (filename or "").replace("\\", "/")
    candidate = os.path.basename(candidate).replace("\x00", "").strip()
    if candidate in {"", ".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")

    candidate = _UNSAFE_FILENAME_CHARS.sub("_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("._")
    if not candidate:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if len(candidate) > 255:
        stem, extension = os.path.splitext(candidate)
        candidate = f"{stem[: 255 - len(extension)]}{extension}"

    return candidate


def validate_upload_type(filename: str, content_type: str | None) -> tuple[str, str]:
    """Validate the extension and return ``(extension, mime_type)``.

    The extension allowlist is the primary control; the MIME type is derived
    from the extension when possible and only falls back to the client value
    for generic/unknown types.
    """
    extension = os.path.splitext(filename)[1].lower()
    normalized_extension = extension.lstrip(".")
    if normalized_extension not in settings.allowed_upload_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{extension or 'unknown'}' is not allowed",
        )

    guessed_type, _ = mimetypes.guess_type(filename)
    mime_type = guessed_type or content_type or "application/octet-stream"
    return extension, mime_type[:100]


def _task_upload_dir(task_id: int) -> str:
    """Resolve and create a task upload directory inside the base directory."""
    base_dir = os.path.realpath(UPLOAD_DIR)
    task_dir = os.path.realpath(os.path.join(base_dir, str(task_id)))
    if os.path.commonpath([base_dir, task_dir]) != base_dir:
        raise HTTPException(status_code=400, detail="Invalid upload path")
    os.makedirs(task_dir, exist_ok=True)
    return task_dir


def get_task_from_params(db: Session, team_id_or_slug: str, project_id_or_name: str, task_id_or_title: str):
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
async def upload_attachment(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
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
    original_filename = sanitize_filename(file.filename)
    extension, mime_type = validate_upload_type(original_filename, file.content_type)

    # An early check avoids obvious oversized uploads, but the streaming loop
    # below is the authoritative limit because file.size can be missing or lie.
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=HTTP_413_TOO_LARGE,
            detail="File too large. Maximum size is 10MB.",
        )

    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    task_dir = _task_upload_dir(task.id)

    # Never use the client filename on disk: generate an opaque, unique key.
    storage_name = f"{uuid.uuid4().hex}{extension}"
    file_path = os.path.join(task_dir, storage_name)

    written = 0
    try:
        with open(file_path, "wb") as destination:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if written > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=HTTP_413_TOO_LARGE,
                        detail="File too large. Maximum size is 10MB.",
                    )
                destination.write(chunk)

        if written == 0:
            raise HTTPException(status_code=400, detail="Empty files are not allowed")

        attachment = crud.create_attachment(
            db,
            task.id,
            current_user.id,
            original_filename,
            file_path,
            written,
            mime_type,
        )
    except Exception:
        # Remove partial files on validation or database failures.
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    finally:
        await file.close()

    crud.log_activity(
        db,
        "attachment",
        attachment.id,
        "uploaded",
        current_user.id,
        None,
        original_filename,
    )

    return attachment


@router.get("/", response_model=list[schemas.AttachmentOut])
def list_attachments(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
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
        list[AttachmentOut]: List of attachments for the task.
    """
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    return crud.get_attachments_by_task(db, task.id)


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
        raise HTTPException(status_code=403, detail="Only the uploader or team admin can delete this attachment")
    
    # Remove file from disk
    if os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)
    
    # Log and delete
    crud.log_activity(db, "attachment", attachment.id, "deleted", current_user.id, attachment.filename, None)
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
    
    if not os.path.exists(attachment.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=attachment.file_path,
        filename=attachment.filename,
        media_type=attachment.mime_type
    )
