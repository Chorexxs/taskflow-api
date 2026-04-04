from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.dependencies import get_current_team_admin, get_current_team_member

router = APIRouter()


def get_project_from_id_or_name(db: Session, project_id_or_name: str, team_id: int) -> models.Project:
    if project_id_or_name.isdigit():
        project = crud.get_project_by_id(db, int(project_id_or_name))
    else:
        project = db.query(models.Project).filter(
            models.Project.team_id == team_id,
            models.Project.name.ilike(project_id_or_name)
        ).first()
    if not project or project.team_id != team_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_task_from_id_or_title(db: Session, task_id_or_title: str, project_id: int) -> models.Task:
    if task_id_or_title.isdigit():
        task = crud.get_task_by_id(db, int(task_id_or_title))
    else:
        task = db.query(models.Task).filter(
            models.Task.project_id == project_id,
            models.Task.title.ilike(task_id_or_title)
        ).first()
    if not task or task.project_id != project_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.post("/", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    team_id_or_slug: str,
    project_id_or_name: str,
    task: schemas.TaskCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    new_task = crud.create_task(db, task, project.id, current_user.id)
    crud.log_activity(db, "task", new_task.id, "created", current_user.id, None, new_task.title)
    return new_task


@router.get("/", response_model=list[schemas.TaskOut])
def list_tasks(
    team_id_or_slug: str,
    project_id_or_name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    return crud.get_tasks_by_project(db, project.id)


@router.get("/{task_id_or_title}", response_model=schemas.TaskOut)
def get_task(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    return get_task_from_id_or_title(db, task_id_or_title, project.id)


@router.patch("/{task_id_or_title}", response_model=schemas.TaskOut)
def update_task(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    task_update: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    
    old_values = {}
    if task_update.title is not None and task_update.title != task.title:
        old_values["title"] = task.title
    if task_update.status is not None and task_update.status.value != task.status:
        old_values["status"] = task.status
    if task_update.priority is not None and task_update.priority.value != task.priority:
        old_values["priority"] = task.priority
    
    updated_task = crud.update_task(db, task.id, task_update)
    
    for field, old_val in old_values.items():
        new_val = getattr(updated_task, field)
        crud.log_activity(db, "task", updated_task.id, f"updated_{field}", current_user.id, old_val, new_val)
    
    return updated_task


@router.delete("/{task_id_or_title}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    
    if task.created_by != current_user.id and member.role != "admin":
        raise HTTPException(status_code=403, detail="Only the creator or admin can delete this task")
    
    crud.delete_task(db, task.id)


@router.patch("/{task_id_or_title}/assign", response_model=schemas.TaskOut)
def assign_task(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    assignment: schemas.TaskAssign,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    
    if assignment.user_id is not None:
        team_member = crud.get_team_member(db, team.id, assignment.user_id)
        if not team_member:
            raise HTTPException(status_code=400, detail="User is not a member of this team")
    
    old_assignee = task.assigned_to
    updated_task = crud.assign_task(db, task.id, assignment.user_id)
    
    if old_assignee != assignment.user_id:
        old_val = str(old_assignee) if old_assignee else None
        new_val = str(assignment.user_id) if assignment.user_id else None
        crud.log_activity(db, "task", updated_task.id, "assigned", current_user.id, old_val, new_val)
    
    return updated_task


@router.get("/{task_id_or_title}/activity", response_model=list[schemas.ActivityLogOut])
def get_task_activity(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    return crud.get_activity_by_task(db, task.id)
