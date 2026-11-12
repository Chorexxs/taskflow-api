"""Project queries and lifecycle."""

from sqlalchemy.orm import Session

from app import models, schemas

from ._common import paginate_query, slugify

__all__ = [
    "create_project",
    "get_project_by_id",
    "get_project_by_slug",
    "get_projects_by_team",
    "get_projects_by_team_paginated",
    "update_project",
    "archive_project",
    "restore_project",
]


def create_project(db: Session, project: schemas.ProjectCreate, team_id: int, user_id: int):
    """
    Create a new project within a team.

    Creates a project with the given name and description. The project
    is automatically set to "active" status. When ``slug`` is provided it must
    be unique within the team; otherwise it is derived from the name and
    suffixed deterministically on collisions.

    Args:
        db (Session): SQLAlchemy database session.
        project (ProjectCreate): Schema with project details.
        team_id (int): ID of the team to create the project in.
        user_id (int): ID of the user creating the project.

    Returns:
        Project: The newly created project object.

    Raises:
        ValueError: If an explicit slug is already used in the team.

    Example:
        >>> project_data = ProjectCreate(name="Website Redesign", description="...")
        >>> new_project = create_project(db, project_data, team_id=1, user_id=1)
    """
    if project.slug:
        existing = (
            db.query(models.Project)
            .filter(
                models.Project.team_id == team_id,
                models.Project.slug == project.slug,
            )
            .first()
        )
        if existing:
            raise ValueError("Project slug already exists in this team")
        slug = project.slug
    else:
        slug = _unique_project_slug(db, team_id, project.name)

    db_project = models.Project(
        team_id=team_id,
        name=project.name,
        slug=slug,
        description=project.description,
        created_by=user_id,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


def get_project_by_id(db: Session, project_id: int):
    """
    Retrieve a project by its ID.

    Args:
        db (Session): SQLAlchemy database session.
        project_id (int): The project's unique identifier.

    Returns:
        Project | None: The project if found, None otherwise.

    Example:
        >>> project = get_project_by_id(db, 1)
    """
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_project_by_slug(db: Session, team_id: int, slug: str):
    """Retrieve a project by its team-scoped slug."""
    return (
        db.query(models.Project)
        .filter(
            models.Project.team_id == team_id,
            models.Project.slug == slug,
        )
        .first()
    )


def get_projects_by_team(db: Session, team_id: int, include_archived: bool = False):
    """
    Get all projects in a team.

    By default, only returns active projects. Set include_archived=True
    to also return archived projects.

    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): ID of the team.
        include_archived (bool): If True, include archived projects. Default False.

    Returns:
        list[Project]: List of projects in the team.

    Example:
        >>> active = get_projects_by_team(db, team_id=1)
        >>> all = get_projects_by_team(db, team_id=1, include_archived=True)
    """
    query = db.query(models.Project).filter(models.Project.team_id == team_id)
    if not include_archived:
        query = query.filter(models.Project.status == "active")
    return query.all()


def get_projects_by_team_paginated(
    db: Session, team_id: int, page: int, page_size: int, include_archived: bool = False
):
    """Return a page of projects, ordered by name."""
    query = db.query(models.Project).filter(models.Project.team_id == team_id)
    if not include_archived:
        query = query.filter(models.Project.status == "active")
    query = query.order_by(models.Project.name, models.Project.id)
    return paginate_query(query, page, page_size)


def update_project(db: Session, project_id: int, project_update: schemas.ProjectUpdate):
    """
    Update a project's details.

    Only updates fields that are provided (not None). Name, description,
    and status can all be updated.

    Args:
        db (Session): SQLAlchemy database session.
        project_id (int): ID of the project to update.
        project_update (ProjectUpdate): Schema with fields to update.

    Returns:
        Project | None: Updated project, or None if not found.

    Example:
        >>> update = ProjectUpdate(name="New Name", status=ProjectStatus.archived)
        >>> updated = update_project(db, 1, update)
    """
    db_project = get_project_by_id(db, project_id)
    if not db_project:
        return None
    if project_update.name is not None:
        db_project.name = project_update.name
    if project_update.description is not None:
        db_project.description = project_update.description
    if project_update.status is not None:
        db_project.status = project_update.status.value
    db.commit()
    db.refresh(db_project)
    return db_project


def archive_project(db: Session, project_id: int):
    """
    Archive a project.

    Sets the project status to "archived". Archived projects are hidden
    by default but can be retrieved with include_archived=True.

    Args:
        db (Session): SQLAlchemy database session.
        project_id (int): ID of the project to archive.

    Returns:
        Project | None: Updated project, or None if not found.

    Example:
        >>> archive_project(db, project_id=1)
    """
    db_project = get_project_by_id(db, project_id)
    if db_project:
        db_project.status = "archived"
        db.commit()
        db.refresh(db_project)
    return db_project


def restore_project(db: Session, project_id: int):
    """Restore an archived project to active status."""
    db_project = get_project_by_id(db, project_id)
    if db_project:
        db_project.status = "active"
        db.commit()
        db.refresh(db_project)
    return db_project


def _unique_project_slug(
    db: Session,
    team_id: int,
    base_slug: str,
    exclude_project_id: int | None = None,
) -> str:
    """Return a slug that is not used by another project in the same team."""
    base = slugify(base_slug)
    candidate = base
    suffix = 2
    while True:
        query = db.query(models.Project).filter(
            models.Project.team_id == team_id,
            models.Project.slug == candidate,
        )
        if exclude_project_id is not None:
            query = query.filter(models.Project.id != exclude_project_id)
        if query.first() is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1
