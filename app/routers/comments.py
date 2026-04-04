from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.dependencies import get_current_team_admin, get_current_team_member

router = APIRouter()


def get_task_from_params(db: Session, team_id_or_slug: str, project_id_or_name: str, task_id_or_title: str):
    from app.dependencies import get_team_from_id_or_slug
    from app.routers.tasks import get_project_from_id_or_name, get_task_from_id_or_title
    
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    return task


@router.post("/", response_model=schemas.CommentOut, status_code=status.HTTP_201_CREATED)
def create_comment(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    new_comment = crud.create_comment(db, comment, task.id, current_user.id)
    
    if task.assigned_to and task.assigned_to != current_user.id:
        crud.create_notification(
            db,
            user_id=task.assigned_to,
            notification_type="commented",
            entity_type="task",
            entity_id=task.id,
            message=f"New comment on task: {task.title}"
        )
    
    return new_comment


@router.get("/", response_model=list[schemas.CommentOut])
def list_comments(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    return crud.get_comments_by_task(db, task.id)


@router.patch("/{comment_id}", response_model=schemas.CommentOut)
def update_comment(
    comment_id: int,
    comment_update: schemas.CommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    comment = crud.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only edit your own comments")
    
    return crud.update_comment(db, comment.id, comment_update.content)


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    comment = crud.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    if comment.task_id != task.id:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    if comment.author_id != current_user.id and member.role != "admin":
        raise HTTPException(status_code=403, detail="Only the author or admin can delete this comment")
    
    crud.delete_comment(db, comment.id)
