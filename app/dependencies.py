"""
TaskFlow API - Route Dependencies

This module provides FastAPI dependencies for route authorization and validation.
These dependencies are used with Depends() to protect routes and ensure
proper access control.

Dependencies provided:
- get_team_from_id_or_slug: Resolve team ID or slug to Team object
- get_current_team_member: Ensure user is a member of the team
- get_current_team_admin: Ensure user is an admin of the team

These dependencies automatically:
- Validate the team exists
- Check user membership
- Verify role-based permissions
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, models
from app.auth import get_current_user
from app.database import get_db


def get_team_from_id_or_slug(db: Session, team_id_or_slug: str) -> models.Team:
    """
    Resolve a team identifier to a Team object.

    Accepts either a numeric team ID or a URL-friendly slug and returns
    the corresponding Team object. This allows routes to accept both
    identification methods.

    Args:
        db (Session): SQLAlchemy database session.
        team_id_or_slug (str): The team identifier (either numeric ID or slug string).

    Returns:
        Team: The Team object if found.

    Raises:
        HTTPException 404: If no team exists with the given ID or slug.

    Example:
        # Both of these resolve to the same team:
        # /api/v1/teams/123
        # /api/v1/teams/my-team-slug
        @router.get("/{team_id_or_slug}")
        def get_team(team = Depends(get_team_from_id_or_slug)):
            return team
    """
    if team_id_or_slug.isdigit():
        team = crud.get_team_by_id(db, int(team_id_or_slug))
    else:
        team = crud.get_team_by_slug(db, team_id_or_slug)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


def get_current_team_member(
    team_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Dependency to ensure the current user is a member of the specified team.

    Resolves the team and the membership in a single query and returns the
    TeamMember with ``member.team`` already loaded, so handlers do not need to
    look the team up again.

    Args:
        team_id_or_slug (str): The team identifier from the URL path.
        db (Session): SQLAlchemy database session (injected).
        current_user (User): The authenticated user (injected via get_current_user).

    Returns:
        TeamMember: The TeamMember object containing the user's role in the team.

    Raises:
        HTTPException 403: If the user is not a member of the team.
        HTTPException 404: If the team doesn't exist.

    Example:
        @router.get("/{team_id_or_slug}/projects")
        def list_projects(
            team_id_or_slug: str,
            member: TeamMember = Depends(get_current_team_member),
        ):
            # member.role contains "admin" or "member"
            ...
    """
    member = crud.get_membership_with_team(db, team_id_or_slug, current_user.id)
    if member is not None:
        return member

    # Distinguish "team does not exist" (404) from "not a member" (403). The
    # extra lookup only happens on the error path.
    get_team_from_id_or_slug(db, team_id_or_slug)
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not a member of this team",
    )


def get_current_team_admin(
    member: models.TeamMember = Depends(get_current_team_member),
):
    """
    Dependency to ensure the current user is an admin of the specified team.

    Reuses ``get_current_team_member`` (cached by FastAPI for the request), so
    the team and membership are only queried once.

    Raises:
        HTTPException 403: If the user is not a member or not an admin.
        HTTPException 404: If the team doesn't exist.
    """
    if member.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return member
