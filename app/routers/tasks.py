"""
TaskFlow API - Tasks Router

This module handles task-related API endpoints within projects:
- POST /: Create a new task
- GET /: List tasks with filters and pagination
- GET /{task_id_or_title}: Get task details
- PATCH /{task_id_or_title}: Update a task
- DELETE /{task_id_or_title}: Delete a task
- PATCH /{task_id_or_title}/assign: Assign task to a user (admin only)
- GET /{task_id_or_title}/activity: Get task activity logs

Tasks belong to projects and can be assigned to team members.
They have status (todo, in_progress, done), priority (low, medium, high),
and optional due dates.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.dependencies import get_current_team_admin, get_current_team_member

router = APIRouter()


def get_project_from_id_or_name(db: Session, project_id_or_name: str, team_id: int) -> models.Project:
    """
    Resolve a project identifier to a Project object.
    
    Accepts either a numeric project ID or a name.
    
    Args:
        db (Session): SQLAlchemy database session.
        project_id_or_name (str): The project identifier (ID or name).
        team_id (int): ID of the team the project belongs to.
    
    Returns:
        Project: The Project object if found.
    
    Raises:
        HTTPException 404: If project not found or doesn't belong to the team.
    """
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
    """
    Resolve a task identifier to a Task object.
    
    Accepts either a numeric task ID or a title (case-insensitive search).
    
    Args:
        db (Session): SQLAlchemy database session.
        task_id_or_title (str): The task identifier (ID or title).
        project_id (int): ID of the project the task belongs to.
    
    Returns:
        Task: The Task object if found.
    
    Raises:
        HTTPException 404: If task not found or doesn't belong to the project.
    """
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
    """
    Create a new task within a project.
    
    Creates a task with the given details. The task is created with
    status "todo" and can be assigned to a team member.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task (TaskCreate): Schema with task details.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user (becomes task creator).
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        TaskOut: The newly created task with assignee information.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/teams/1/projects/1/tasks/ \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"title":"Fix login bug","priority":"high","assigned_to":2}'
    """
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    new_task = crud.create_task(db, task, project.id, current_user.id)
    crud.log_activity(db, "task", new_task.id, "created", current_user.id, None, new_task.title)
    return new_task


@router.get("/", response_model=schemas.PaginatedTaskResponse)
def list_tasks(
    team_id_or_slug: str,
    project_id_or_name: str,
    status: str = None,
    priority: str = None,
    assigned_to: str = None,
    due_before: datetime = None,
    due_after: datetime = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    List tasks with filters and pagination.
    
    Returns paginated tasks for a project. Supports filtering by:
    - status: todo, in_progress, done
    - priority: low, medium, high
    - assigned_to: user ID
    - due_before, due_after: due date range
    
    Also supports sorting and pagination.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        status (str | None): Filter by task status.
        priority (str | None): Filter by task priority.
        assigned_to (str | None): Filter by assignee user ID (as string).
        due_before (datetime | None): Filter tasks due before this date.
        due_after (datetime | None): Filter tasks due after this date.
        sort_by (str): Field to sort by.
        order (str): Sort order (asc or desc).
        page (int): Page number (1-indexed).
        page_size (int): Items per page (max 100).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        PaginatedTaskResponse: Dictionary with items, total, page info.
    
    Example:
        >>> curl "https://api.taskflow.com/api/v1/teams/1/projects/1/tasks/?status=todo&priority=high" \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    if page_size > 100:
        page_size = 100
    
    # Convert string to int for assigned_to filter
    assigned_to_param = int(assigned_to) if assigned_to and assigned_to.isdigit() else None
    
    return crud.get_tasks_by_project(
        db, project.id, status, priority, assigned_to_param, due_before, due_after, sort_by, order, page, page_size
    )


@router.get("/{task_id_or_title}", response_model=schemas.TaskOut)
def get_task(
    team_id_or_slug: str,
    project_id_or_name: str,
    task_id_or_title: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    Get task details.
    
    Returns detailed information about a specific task,
    including assignee information.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        TaskOut: Task details with assignee information.
    """
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
    """
    Update a task's details.
    
    Only the task creator or a team admin can update tasks.
    Only provided fields are updated.
    Changes are logged to the activity log.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        task_update (TaskUpdate): Schema with fields to update.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        TaskOut: Updated task.
    
    Raises:
        HTTPException 403: If user is not creator or admin.
    """
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    
    # Check permissions: creator or admin can update
    if task.created_by != current_user.id and member.role != "admin":
        raise HTTPException(status_code=403, detail="Only the creator or admin can edit this task")
    
    # Track old values for activity log
    old_values = {}
    if task_update.title is not None and task_update.title != task.title:
        old_values["title"] = task.title
    if task_update.status is not None and task_update.status.value != task.status:
        old_values["status"] = task.status
    if task_update.priority is not None and task_update.priority.value != task.priority:
        old_values["priority"] = task.priority
    
    updated_task = crud.update_task(db, task.id, task_update)
    
    # Log activity for changed fields
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
    """
    Delete a task.
    
    Only the task creator or a team admin can delete tasks.
    This permanently removes the task and associated data.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        None: Returns 204 No Content on success.
    
    Raises:
        HTTPException 403: If user is not creator or admin.
    """
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    
    # Check permissions: creator or admin can delete
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
    """
    Assign or unassign a task.
    
    Only team admins can assign tasks. The assignee must be a member
    of the team. A notification is sent to the assigned user.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        assignment (TaskAssign): Schema with user_id (can be null to unassign).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        admin (TeamMember): Admin check (injected via dependency).
    
    Returns:
        TaskOut: Updated task with new assignee.
    
    Raises:
        HTTPException 400: If assignee is not a team member.
    """
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    
    # Verify assignee is a team member
    if assignment.user_id is not None:
        team_member = crud.get_team_member(db, team.id, assignment.user_id)
        if not team_member:
            raise HTTPException(status_code=400, detail="User is not a member of this team")
    
    old_assignee = task.assigned_to
    updated_task = crud.assign_task(db, task.id, assignment.user_id)
    
    # Log activity and create notification on assignment change
    if old_assignee != assignment.user_id:
        old_val = str(old_assignee) if old_assignee else None
        new_val = str(assignment.user_id) if assignment.user_id else None
        crud.log_activity(db, "task", updated_task.id, "assigned", current_user.id, old_val, new_val)
        
        # Notify the newly assigned user
        if assignment.user_id:
            assignee = crud.get_user_by_id(db, assignment.user_id)
            if assignee:
                crud.create_notification(
                    db,
                    user_id=assignment.user_id,
                    notification_type="assigned",
                    entity_type="task",
                    entity_id=updated_task.id,
                    message=f"You have been assigned to task: {updated_task.title}"
                )
    
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
    """
    Get activity logs for a task.
    
    Returns all activity events related to the task, such as
    creation, updates, and assignments. Ordered by creation date.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        list[ActivityLogOut]: List of activity logs for the task.
    """
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_name(db, project_id_or_name, team.id)
    task = get_task_from_id_or_title(db, task_id_or_title, project.id)
    return crud.get_activity_by_task(db, task.id)
