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
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.dependencies import get_current_team_admin, get_current_team_member

router = APIRouter()

# Maximum file size: 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024

# Directory for uploaded files
UPLOAD_DIR = "uploads"


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
    # Check file size
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
    
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    
    # Create task-specific upload directory
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    task_dir = os.path.join(UPLOAD_DIR, str(task.id))
    os.makedirs(task_dir, exist_ok=True)
    
    # Save file to disk
    file_path = os.path.join(task_dir, file.filename)
    contents = await file.read()
    await file.close()
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Determine MIME type
    mime_type = file.content_type or "application/octet-stream"
    
    # Create attachment record in database
    attachment = crud.create_attachment(
        db, task.id, current_user.id, file.filename, file_path, len(contents), mime_type
    )
    
    # Log activity
    crud.log_activity(db, "attachment", attachment.id, "uploaded", current_user.id, None, file.filename)
    
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
    
    if not attachment or attachment.task_id != task.id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Check permissions: uploader or admin can delete
    if attachment.uploaded_by != current_user.id and member.role != "admin":
        raise HTTPException(status_code=403, detail="Only the uploader or admin can delete this attachment")
    
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
