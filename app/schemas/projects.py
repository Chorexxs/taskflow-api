"""Project schemas."""

import re
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator

from .common import sanitize_text

__all__ = [
    "ProjectStatus",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectOut",
    "PaginatedProjectResponse",
]


class ProjectStatus(str, Enum):
    """
    Enum representing project status.

    Attributes:
        active: Project is active and visible
        archived: Project is archived and hidden by default
    """

    active = "active"
    archived = "archived"


class ProjectCreate(BaseModel):
    """
    Schema for project creation.

    Used in POST /teams/{id}/projects endpoint.

    Attributes:
        name (str): Project name
        slug (str | None): Optional URL-friendly identifier; derived from the
            name when omitted
        description (str | None): Optional project description

    Validators:
        sanitize_input: Removes control characters from text fields
    """

    name: str
    slug: str | None = None
    description: str | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v

    @field_validator("slug", mode="before")
    @classmethod
    def normalize_slug(cls, v):
        """Normalize an explicit project slug or reject an empty one."""
        if v is None:
            return v
        value = re.sub(r"[^a-z0-9]+", "-", str(v).strip().lower()).strip("-")
        if not value:
            raise ValueError("slug must contain letters or numbers")
        return value[:255]


class ProjectUpdate(BaseModel):
    """
    Schema for project updates.

    Used in PATCH /teams/{id}/projects/{id} endpoint.
    All fields are optional - only included fields are updated.

    Attributes:
        name (str | None): New project name
        description (str | None): New project description
        status (ProjectStatus | None): New project status

    Validators:
        sanitize_input: Removes control characters from text fields
    """

    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None

    @field_validator("name", "description", mode="before")
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class ProjectOut(BaseModel):
    """
    Schema for project response data.

    Used in project list and detail endpoints.

    Attributes:
        id (int): Project's unique identifier
        team_id (int): Team the project belongs to
        name (str): Project name
        slug (str): URL-friendly identifier, unique within the team
        description (str | None): Project description
        status (ProjectStatus): Project status
        created_by (int): ID of user who created the project
        created_at (datetime): Project creation timestamp

    Config:
        from_attributes: Allows creation from ORM objects
    """

    id: int
    team_id: int
    name: str
    slug: str
    description: str | None
    status: ProjectStatus
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedProjectResponse(BaseModel):
    """Paginated list of projects."""

    items: list[ProjectOut]
    total: int
    page: int
    pages: int
    has_next: bool
