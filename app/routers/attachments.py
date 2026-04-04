import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.dependencies import get_current_team_admin, get_current_team_member

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024

UPLOAD_DIR = "uploads"


def get_task_from_params(db: Session, team_id_or_slug: str, project_id_or_name: str, task_id_or_title: str):
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
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
    
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    task_dir = os.path.join(UPLOAD_DIR, str(task.id))
    os.makedirs(task_dir, exist_ok=True)
    
    file_path = os.path.join(task_dir, file.filename)
    
    contents = await file.read()
    await file.close()
    
    with open(file_path, "wb") as f:
        f.write(contents)
    
    mime_type = file.content_type or "application/octet-stream"
    
    attachment = crud.create_attachment(
        db, task.id, current_user.id, file.filename, file_path, len(contents), mime_type
    )
    
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
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    attachment = crud.get_attachment_by_id(db, attachment_id)
    
    if not attachment or attachment.task_id != task.id:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    if attachment.uploaded_by != current_user.id and member.role != "admin":
        raise HTTPException(status_code=403, detail="Only the uploader or admin can delete this attachment")
    
    if os.path.exists(attachment.file_path):
        os.remove(attachment.file_path)
    
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
