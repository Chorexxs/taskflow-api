"""
TaskFlow API - Comments Router

This module handles comment-related API endpoints for tasks:
- POST /: Create a comment on a task
- GET /: List all comments for a task
- PATCH /{comment_id}: Update a comment
- DELETE /{comment_id}: Delete a comment

Comments allow team members to discuss task details. Authors can
edit and delete their own comments, while team admins can delete
any comment.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.dependencies import get_current_team_admin, get_current_team_member

router = APIRouter()


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
    
    Raises:
        HTTPException 404: If any entity is not found.
    """
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
    """
    Create a comment on a task.
    
    All team members can comment on tasks. The task's assignee
    receives a notification about the new comment.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        comment (CommentCreate): Schema with comment content.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user (comment author).
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        CommentOut: The newly created comment.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/teams/1/projects/1/tasks/1/comments/ \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"content":"This looks great!"}'
    """
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    new_comment = crud.create_comment(db, comment, task.id, current_user.id)
    
    # Notify assignee if different from comment author
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
    """
    List all comments for a task.
    
    Returns all comments on a task, ordered by creation date
    (newest first).
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        list[CommentOut]: List of comments for the task.
    
    Example:
        >>> curl -X GET https://api.taskflow.com/api/v1/teams/1/projects/1/tasks/1/comments/ \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    return crud.get_comments_by_task(db, task.id)


@router.patch("/{comment_id}", response_model=schemas.CommentOut)
def update_comment(
    comment_id: int,
    comment_update: schemas.CommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Update a comment's content.
    
    Only the comment author can edit their own comments.
    
    Args:
        comment_id (int): ID of the comment to update.
        comment_update (CommentUpdate): Schema with new content.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
    
    Returns:
        CommentOut: Updated comment.
    
    Raises:
        HTTPException 404: If comment not found.
        HTTPException 403: If user is not the comment author.
    
    Example:
        >>> curl -X PATCH https://api.taskflow.com/api/v1/teams/1/projects/1/tasks/1/comments/1 \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"content":"Updated content"}'
    """
    comment = crud.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check if user is the author
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
    """
    Delete a comment.
    
    The comment author or a team admin can delete comments.
    
    Args:
        comment_id (int): ID of the comment to delete.
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_name (str): The project identifier (ID or name).
        task_id_or_title (str): The task identifier (ID or title).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        None: Returns 204 No Content on success.
    
    Raises:
        HTTPException 404: If comment not found or doesn't belong to task.
        HTTPException 403: If user is not author or admin.
    
    Example:
        >>> curl -X DELETE https://api.taskflow.com/api/v1/teams/1/projects/1/tasks/1/comments/1 \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    comment = crud.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Verify comment belongs to the task
    task = get_task_from_params(db, team_id_or_slug, project_id_or_name, task_id_or_title)
    if comment.task_id != task.id:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    # Check permissions: author or admin can delete
    if comment.author_id != current_user.id and member.role != "admin":
        raise HTTPException(status_code=403, detail="Only the author or admin can delete this comment")
    
    crud.delete_comment(db, comment.id)
