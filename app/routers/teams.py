"""
TaskFlow API - Teams Router

This module handles team-related API endpoints:
- POST /: Create a new team
- GET /: List teams for current user
- GET /{team_id_or_slug}: Get team details
- GET /{team_id_or_slug}/search: Search in team
- POST /{team_id_or_slug}/members: Invite a member (admin only)
- GET /{team_id_or_slug}/members: List team members
- DELETE /{team_id_or_slug}/members/{user_id}: Remove member
- PATCH /{team_id_or_slug}/members/{user_id}: Update member role (admin only)

Teams allow users to collaborate on projects. Each team has members
with roles (admin or member) that determine their permissions.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.dependencies import get_current_team_admin, get_current_team_member
from app.rate_limit import rate_limit

router = APIRouter()


def get_team_from_id_or_slug(db: Session, team_id_or_slug: str) -> models.Team:
    """
    Resolve a team identifier to a Team object.

    Accepts either a numeric team ID or a URL-friendly slug.

    Args:
        db (Session): SQLAlchemy database session.
        team_id_or_slug (str): The team identifier (ID or slug).

    Returns:
        Team: The Team object if found.

    Raises:
        HTTPException 404: If team not found.
    """
    if team_id_or_slug.isdigit():
        team = crud.get_team_by_id(db, int(team_id_or_slug))
    else:
        team = crud.get_team_by_slug(db, team_id_or_slug)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.post("/", response_model=schemas.TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    team: schemas.TeamCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Create a new team.
    
    Creates a new team and adds the creator as an admin member.
    The team requires a unique slug that can be used in URLs.
    
    Args:
        team (TeamCreate): Schema with name, slug, and optional description.
        current_user (User): The authenticated user (creator becomes admin).
        db (Session): Database session (injected by FastAPI).
    
    Returns:
        TeamOut: The newly created team.
    
    Raises:
        HTTPException 400: If the team slug already exists.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/teams/ \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"name":"My Team","slug":"my-team","description":"A team"}'
    """
    # Check if slug already exists
    existing_team = crud.get_team_by_slug(db, team.slug)
    if existing_team:
        raise HTTPException(status_code=400, detail="Team slug already exists")

    return crud.create_team(db, team, current_user.id)


@router.get("/", response_model=schemas.PaginatedTeamResponse)
def get_teams(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    List all teams the current user is a member of.
    
    Returns all teams where the current user has membership,
    regardless of their role.
    
    Args:
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
    
    Returns:
        PaginatedTeamResponse: Page of teams the user belongs to.

    Example:
        >>> curl -X GET https://api.taskflow.com/api/v1/teams/?page=1&page_size=20 \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    items, total, pages = crud.get_teams_by_user_paginated(db, current_user.id, page, page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "has_next": page < pages,
    }


@router.get("/{team_id_or_slug}/search", response_model=schemas.SearchResult)
@rate_limit("60/minute")
def search_in_team(
    team_id_or_slug: str,
    q: str,
    request: Request,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    Search for projects and tasks in a team.
    
    Performs a case-insensitive search across project names and task titles
    within the specified team.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        q (str): Search query string.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        member (TeamMember): Team membership check (injected via dependency).
    
    Returns:
        dict: Dictionary with "projects" and "tasks" lists.
    
    Example:
        >>> curl "https://api.taskflow.com/api/v1/teams/1/search?q=website" \\
        ...   -H "Authorization: Bearer eyJhbGc..."
        
        Response:
        {
            "projects": [...],
            "tasks": [...]
        }
    """
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(
            status_code=422,
            detail="Search query must be at least 2 characters",
        )

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    return crud.search_in_team(db, team.id, q, page, page_size)


@router.get("/{team_id_or_slug}", response_model=schemas.TeamOut)
def get_team(
    team_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Get team details.
    
    Returns detailed information about a specific team.
    The user must be a member of the team to access this endpoint.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
    
    Returns:
        TeamOut: Team details including name, slug, description, and metadata.
    
    Raises:
        HTTPException 403: If user is not a member of the team.
        HTTPException 404: If team not found.
    
    Example:
        >>> curl -X GET https://api.taskflow.com/api/v1/teams/my-team \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    # Verify membership
    get_current_team_member(team_id_or_slug, db, current_user)
    return team


@router.patch("/{team_id_or_slug}", response_model=schemas.TeamOut)
def update_team(
    team_id_or_slug: str,
    team_update: schemas.TeamUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    """Update a team's name or description. Only team admins may do this."""
    if team_update.name is not None and not team_update.name.strip():
        raise HTTPException(status_code=400, detail="Team name cannot be empty")

    team = get_team_from_id_or_slug(db, team_id_or_slug)
    old_name = team.name
    updated = crud.update_team(db, team.id, team_update)
    crud.log_activity(
        db,
        "team",
        team.id,
        "updated",
        current_user.id,
        old_name,
        updated.name if updated else None,
    )
    return updated


@router.post(
    "/{team_id_or_slug}/members",
    response_model=schemas.TeamMemberOut,
    status_code=status.HTTP_201_CREATED,
)
def invite_member(
    team_id_or_slug: str,
    member_data: schemas.TeamMemberAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    """
    Invite a user to join the team.
    
    Adds an existing user to the team with the specified role.
    Only team admins can invite new members.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        member_data (TeamMemberAdd): Schema with email and role.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        admin (TeamMember): Admin check (injected via dependency).
    
    Returns:
        TeamMemberOut: The newly created member record with user details.
    
    Raises:
        HTTPException 404: If user with the given email doesn't exist.
        HTTPException 400: If user is already a member.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/teams/1/members \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"email":"newuser@example.com","role":"member"}'
    """
    team = get_team_from_id_or_slug(db, team_id_or_slug)

    # Find the user by email
    user = crud.get_user_by_email(db, member_data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if user is already a member
    existing_member = crud.get_team_member(db, team.id, user.id)
    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a member")

    return crud.add_member(db, team.id, user.id, member_data.role.value)


@router.get(
    "/{team_id_or_slug}/members",
    response_model=schemas.PaginatedTeamMemberResponse,
)
def list_members(
    team_id_or_slug: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    List all members of a team.
    
    Returns all members with their roles and user information.
    The user must be a member of the team to access this endpoint.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
    
    Returns:
        PaginatedTeamMemberResponse: Page of members with user details.

    Example:
        >>> curl -X GET "https://api.taskflow.com/api/v1/teams/1/members?page=1&page_size=20" \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    get_current_team_member(team_id_or_slug, db, current_user)
    items, total, pages = crud.get_team_members_paginated(db, team.id, page, page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": pages,
        "has_next": page < pages,
    }


@router.delete("/{team_id_or_slug}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    team_id_or_slug: str,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Remove a member from a team.
    
    Allows removing members. Members can remove themselves, while
    admins can remove any member. A user cannot remove themselves
    if they are the only admin.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        user_id (int): ID of the user to remove.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
    
    Returns:
        None: Returns 204 No Content on success.

    Raises:
        HTTPException 404: If member not found.
        HTTPException 403: If not authorized to remove.

    Example:
        >>> curl -X DELETE https://api.taskflow.com/api/v1/teams/1/members/2 \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    member = crud.get_team_member(db, team.id, user_id)

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    current_member = crud.get_team_member(db, team.id, current_user.id)
    if not current_member:
        raise HTTPException(status_code=403, detail="Not a member of this team")

    is_self = member.user_id == current_user.id

    # A member may leave, but only an admin may remove someone else.
    if not is_self and current_member.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only team admins can remove other members",
        )

    # Never leave a team without an administrator.
    if member.role == "admin" and crud.count_team_admins(db, team.id) <= 1:
        raise HTTPException(
            status_code=409,
            detail="Cannot remove the last admin of the team",
        )

    crud.remove_member(db, team.id, user_id, changed_by=current_user.id)


@router.patch("/{team_id_or_slug}/members/{user_id}", response_model=schemas.TeamMemberOut)
def update_member_role(
    team_id_or_slug: str,
    user_id: int,
    role_update: schemas.TeamMemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    """
    Update a member's role in a team.
    
    Only team admins can change member roles. An admin cannot
    demote themselves to member if they are the only admin.
    
    Args:
        team_id_or_slug (str): The team identifier (ID or slug).
        user_id (int): ID of the user to update.
        role_update (TeamMemberUpdate): Schema with new role.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        admin (TeamMember): Admin check (injected via dependency).
    
    Returns:
        TeamMemberOut: Updated member record.
    
    Raises:
        HTTPException 404: If member not found.
        HTTPException 400: If admin tries to demote themselves.
    
    Example:
        >>> curl -X PATCH https://api.taskflow.com/api/v1/teams/1/members/2 \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"role":"admin"}'
    """
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    member = crud.get_team_member(db, team.id, user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Prevent admin from demoting themselves
    if member.user_id == admin.user_id and role_update.role.value == "member":
        raise HTTPException(status_code=400, detail="Cannot change own admin role")

    # Never leave a team without an administrator.
    if (
        member.role == "admin"
        and role_update.role.value != "admin"
        and crud.count_team_admins(db, team.id) <= 1
    ):
        raise HTTPException(
            status_code=409,
            detail="Cannot demote the last admin of the team",
        )

    old_role = member.role
    updated_member = crud.update_member_role(db, team.id, user_id, role_update.role.value)
    crud.log_activity(
        db,
        "team_member",
        user_id,
        "role_changed",
        current_user.id,
        old_role,
        role_update.role.value,
    )
    return updated_member
