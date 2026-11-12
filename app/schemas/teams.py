"""Team and membership schemas."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from .common import sanitize_text
from .users import UserOut

__all__ = [
    "TeamRole",
    "TeamCreate",
    "TeamUpdate",
    "TeamOut",
    "TeamSummaryOut",
    "TeamMemberOut",
    "TeamMemberUpdate",
    "TeamMemberAdd",
    "PaginatedTeamResponse",
    "PaginatedTeamMemberResponse",
]


class TeamRole(str, Enum):
    """
    Enum representing team member roles.

    Attributes:
        admin: Can manage team members, projects, and all team resources
        member: Can view and work within team projects
    """

    admin = "admin"
    member = "member"


class TeamCreate(BaseModel):
    """
    Schema for team creation.

    Used in POST /teams endpoint.

    Attributes:
        name (str): Team display name
        slug (str): URL-friendly unique identifier
        description (str | None): Optional team description

    Validators:
        sanitize_input: Removes control characters from text fields
    """

    name: str
    slug: str | None = None
    description: str | None = None

    @field_validator("name", "slug", "description", mode="before")
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class TeamUpdate(BaseModel):
    """Editable team fields. Only admins may change them."""

    name: str | None = None
    description: str | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def sanitize_input(cls, v):
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class TeamOut(BaseModel):
    """
    Schema for team response data.

    Used in team list and detail endpoints.

    Attributes:
        id (int): Team's unique identifier
        name (str): Team display name
        slug (str): URL-friendly identifier
        description (str | None): Team description
        created_by (int): ID of user who created the team
        created_at (datetime): Team creation timestamp

    Config:
        from_attributes: Allows creation from ORM objects
    """

    id: int
    name: str
    slug: str
    description: str | None
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TeamSummaryOut(TeamOut):
    """Team list item with the caller's role and project count (FR-TEAM-02)."""

    role: TeamRole
    project_count: int


class TeamMemberOut(BaseModel):
    """
    Schema for team member response with user details.

    Used when returning member list with full user information.

    Attributes:
        team_id (int): Team identifier
        user_id (int): User identifier
        role (TeamRole): Member's role in the team
        joined_at (datetime): When the user joined
        user (UserOut): Full user object

    Config:
        from_attributes: Allows creation from ORM objects
    """

    team_id: int
    user_id: int
    role: TeamRole
    joined_at: datetime
    user: UserOut

    model_config = ConfigDict(from_attributes=True)


class TeamMemberUpdate(BaseModel):
    """
    Schema for updating team member role.

    Used in PATCH /teams/{id}/members/{user_id} endpoint.

    Attributes:
        role (TeamRole): New role for the member
    """

    role: TeamRole


class TeamMemberAdd(BaseModel):
    """
    Schema for adding a new team member.

    Used in POST /teams/{id}/members endpoint.

    Attributes:
        email (EmailStr): Email of user to invite
        role (TeamRole): Role to assign (default: member)
    """

    email: EmailStr
    role: TeamRole = TeamRole.member


class PaginatedTeamResponse(BaseModel):
    """Paginated list of teams, including the caller's role."""

    items: list[TeamSummaryOut]
    total: int
    page: int
    pages: int
    has_next: bool


class PaginatedTeamMemberResponse(BaseModel):
    """Paginated list of team members."""

    items: list[TeamMemberOut]
    total: int
    page: int
    pages: int
    has_next: bool
