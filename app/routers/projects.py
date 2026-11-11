"""
TaskFlow API - Projects Router

This module handles project-related API endpoints within teams:
- POST /: Create a new project
- GET /: List all projects in a team
- GET /{project_id_or_slug}: Get project details
- PATCH /{project_id_or_slug}: Update project (admin only)
- DELETE /{project_id_or_slug}: Archive project (admin only)
- GET /{project_id_or_slug}/activity: Get project activity logs

Projects are containers for tasks within a team. They can be archived
when no longer active, but are not permanently deleted.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.dependencies import (
    get_current_team_admin,
    get_current_team_member,
    get_team_from_id_or_slug,
)
from app.idempotency import IdempotencyGuard, get_idempotency_guard
from app.logging_config import get_logger
from app.rate_limit import rate_limit

router = APIRouter()
logger = get_logger(__name__)


def get_project_from_id_or_slug(
    db: Session, project_id_or_slug: str, team_id: int
) -> models.Project:
    """
    Resolve a project identifier to a Project object.

    Accepts a numeric project ID, the team-scoped slug (preferred) or a legacy
    name. Name lookups are deprecated and ambiguous names return 409.

    Args:
        db (Session): SQLAlchemy database session.
        project_id_or_slug (str): The project identifier (ID, slug or name).
        team_id (int): ID of the team the project belongs to.

    Returns:
        Project: The Project object if found.

    Raises:
        HTTPException 404: If project not found or doesn't belong to the team.
        HTTPException 409: If a legacy name matches more than one project.
    """
    if project_id_or_slug.isdigit():
        project = crud.get_project_by_id(db, int(project_id_or_slug))
    else:
        project = crud.get_project_by_slug(db, team_id, project_id_or_slug)
        if project is None:
            matches = (
                db.query(models.Project)
                .filter(
                    models.Project.team_id == team_id,
                    models.Project.name.ilike(project_id_or_slug),
                )
                .all()
            )
            if len(matches) > 1:
                raise HTTPException(
                    status_code=409,
                    detail="Multiple projects match that name; use the project id or slug",
                )
            if matches:
                project = matches[0]
                logger.warning(
                    "deprecated_project_name_lookup",
                    project_id=project.id,
                    team_id=team_id,
                )
    if not project or project.team_id != team_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=schemas.ProjectOut, status_code=status.HTTP_201_CREATED)
@rate_limit("30/minute")
def create_project(
    request: Request,
    response: Response,
    team_id_or_slug: str,
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
    guard: IdempotencyGuard = Depends(get_idempotency_guard),
):
    """
    Create a new project within a team.
    
    Creates a project in the specified team. All team members can
    create projects. The project is created with "active" status.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project (ProjectCreate): Schema with name and optional description.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user (becomes project creator).
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        ProjectOut: The newly created project.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/teams/1/projects/ \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"name":"Website Redesign","description":"Redesign company website"}'
    """
    from app.dependencies import get_team_from_id_or_slug

    if (replay := guard.replay(project)) is not None:
        return replay

    team = get_team_from_id_or_slug(db, team_id_or_slug)
    try:
        new_project = crud.create_project(db, project, team.id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    crud.log_activity(
        db, "project", new_project.id, "created", current_user.id, None, new_project.name
    )
    guard.store(status.HTTP_201_CREATED, schemas.ProjectOut.model_validate(new_project))
    return new_project


@router.get("/", response_model=schemas.PaginatedProjectResponse)
def list_projects(
    team_id_or_slug: str,
    include_archived: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    List all active projects in a team.
    
    Returns all projects with "active" status. Archived projects
    are not included by default.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        PaginatedProjectResponse: Page of active projects in the team.

    Example:
        >>> curl -X GET "https://api.taskflow.com/api/v1/teams/1/projects/?page=1&page_size=20" \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    from app.dependencies import get_team_from_id_or_slug

    team = get_team_from_id_or_slug(db, team_id_or_slug)
    items, total, pages = crud.get_projects_by_team_paginated(
        db, team.id, page, page_size, include_archived=include_archived
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "has_next": page < pages,
    }


@router.get("/{project_id_or_slug}", response_model=schemas.ProjectOut)
def get_project(
    team_id_or_slug: str,
    project_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    Get project details.
    
    Returns detailed information about a specific project.
    The user must be a member of the team to access this endpoint.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_slug (str): The project identifier (ID or name).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        ProjectOut: Project details including name, description, status, and metadata.
    
    Example:
        >>> curl -X GET https://api.taskflow.com/api/v1/teams/1/projects/1 \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    from app.dependencies import get_team_from_id_or_slug

    team = get_team_from_id_or_slug(db, team_id_or_slug)
    return get_project_from_id_or_slug(db, project_id_or_slug, team.id)


@router.patch("/{project_id_or_slug}", response_model=schemas.ProjectOut)
def update_project(
    team_id_or_slug: str,
    project_id_or_slug: str,
    project_update: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    """
    Update a project's details.
    
    Only team admins can update projects. Supports updating name,
    description, and status.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_slug (str): The project identifier (ID or name).
        project_update (ProjectUpdate): Schema with fields to update.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        admin (TeamMember): Admin check (injected via dependency).
    
    Returns:
        ProjectOut: Updated project.
    
    Example:
        >>> curl -X PATCH https://api.taskflow.com/api/v1/teams/1/projects/1 \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"name":"New Name","status":"archived"}'
    """
    from app.dependencies import get_team_from_id_or_slug

    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_slug(db, project_id_or_slug, team.id)
    return crud.update_project(db, project.id, project_update)


@router.delete("/{project_id_or_slug}", status_code=status.HTTP_204_NO_CONTENT)
def archive_project(
    team_id_or_slug: str,
    project_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    """
    Archive a project.
    
    Only team admins can archive projects. Archived projects are
    hidden from default project listings but can be retrieved
    with include_archived=true.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_slug (str): The project identifier (ID or name).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        admin (TeamMember): Admin check (injected via dependency).
    
    Returns:
        None: Returns 204 No Content on success.
    
    Example:
        >>> curl -X DELETE https://api.taskflow.com/api/v1/teams/1/projects/1 \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    from app.dependencies import get_team_from_id_or_slug

    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_slug(db, project_id_or_slug, team.id)
    old_status = project.status
    crud.archive_project(db, project.id)
    crud.log_activity(
        db, "project", project.id, "archived", current_user.id, old_status, "archived"
    )


@router.post("/{project_id_or_slug}/archive", response_model=schemas.ProjectOut)
def archive_project_endpoint(
    team_id_or_slug: str,
    project_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    """Explicitly archive a project. Only team admins may do this."""
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_slug(db, project_id_or_slug, team.id)
    old_status = project.status
    if old_status != "archived":
        project = crud.archive_project(db, project.id)
        crud.log_activity(
            db, "project", project.id, "archived", current_user.id, old_status, "archived"
        )
    return project


@router.post("/{project_id_or_slug}/restore", response_model=schemas.ProjectOut)
def restore_project_endpoint(
    team_id_or_slug: str,
    project_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    """Restore an archived project to active status. Only team admins may do this."""
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_slug(db, project_id_or_slug, team.id)
    old_status = project.status
    if old_status != "active":
        project = crud.restore_project(db, project.id)
        crud.log_activity(
            db, "project", project.id, "restored", current_user.id, old_status, "active"
        )
    return project


@router.get("/{project_id_or_slug}/activity", response_model=schemas.PaginatedActivityResponse)
def get_project_activity(
    team_id_or_slug: str,
    project_id_or_slug: str,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    Get activity logs for a project.
    
    Returns all activity events related to the project, such as
    creation and archival. Ordered by creation date (newest first).
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        project_id_or_slug (str): The project identifier (ID or name).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        PaginatedActivityResponse: Page of activity logs plus metadata.
    
    Example:
        >>> curl -X GET https://api.taskflow.com/api/v1/teams/1/projects/1/activity \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    from app.dependencies import get_team_from_id_or_slug

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_slug(db, project_id_or_slug, team.id)
    return crud.get_activity_by_project(db, project.id, page, page_size)
