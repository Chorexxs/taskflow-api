"""Teams and membership queries."""

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app import models, schemas

from ._common import paginate_query, slugify

__all__ = [
    "create_team",
    "update_team",
    "get_team_by_id",
    "get_team_by_slug",
    "get_teams_by_user_paginated",
    "add_member",
    "remove_member",
    "get_team_members_paginated",
    "get_team_member",
    "lock_team_for_membership_change",
    "count_team_admins",
    "update_member_role",
]


def create_team(db: Session, team: schemas.TeamCreate, user_id: int):
    """
    Create a new team and add the creator as admin.

    Creates a team with the given name, slug, and description, then
    automatically creates a TeamMember record with admin role for
    the creator. Uses two commits to ensure team exists before
    adding member.

    Args:
        db (Session): SQLAlchemy database session.
        team (TeamCreate): Schema with team details.
        user_id (int): ID of the user creating the team (will be admin).

    Returns:
        Team: The newly created team object.

    Raises:
        sqlalchemy.exc.IntegrityError: If slug already exists (unique constraint).

    Example:
        >>> team_data = TeamCreate(name="My Team", slug="my-team", description="A team")
        >>> new_team = create_team(db, team_data, user_id=1)
    """
    db_team = models.Team(
        name=team.name,
        slug=(team.slug or "").strip() or _unique_team_slug(db, team.name),
        description=team.description,
        created_by=user_id,
    )
    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    # Add creator as admin member
    member = models.TeamMember(
        team_id=db_team.id,
        user_id=user_id,
        role="admin",
    )
    db.add(member)
    db.commit()

    return db_team


def update_team(db: Session, team_id: int, team_update: schemas.TeamUpdate):
    """Update a team's editable fields.

    The slug is intentionally immutable so existing URLs keep working.
    """
    db_team = get_team_by_id(db, team_id)
    if not db_team:
        return None
    if team_update.name is not None:
        db_team.name = team_update.name
    if team_update.description is not None:
        db_team.description = team_update.description
    db.commit()
    db.refresh(db_team)
    return db_team


def get_team_by_id(db: Session, team_id: int):
    """
    Retrieve a team by its numeric ID.

    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): The team's unique identifier.

    Returns:
        Team | None: The team if found, None otherwise.

    Example:
        >>> team = get_team_by_id(db, 1)
    """
    return db.query(models.Team).filter(models.Team.id == team_id).first()


def get_team_by_slug(db: Session, slug: str):
    """
    Retrieve a team by its URL-friendly slug.

    Used for team lookups using the human-readable identifier.

    Args:
        db (Session): SQLAlchemy database session.
        slug (str): The team's unique slug.

    Returns:
        Team | None: The team if found, None otherwise.

    Example:
        >>> team = get_team_by_slug(db, "my-team")
    """
    return db.query(models.Team).filter(models.Team.slug == slug).first()


def get_teams_by_user_paginated(db: Session, user_id: int, page: int, page_size: int):
    """Return a page of teams for a user, with role and project count.

    Both fields are required by FR-TEAM-02. They are computed in the same query
    (correlated subquery) so the list does not issue one count per team.
    """
    project_count = (
        db.query(func.count(models.Project.id))
        .filter(models.Project.team_id == models.Team.id)
        .correlate(models.Team)
        .scalar_subquery()
    )
    query = (
        db.query(
            models.Team,
            models.TeamMember.role,
            project_count.label("project_count"),
        )
        .join(models.TeamMember, models.TeamMember.team_id == models.Team.id)
        .filter(models.TeamMember.user_id == user_id)
        .order_by(models.Team.name, models.Team.id)
    )
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()
    pages = (total + page_size - 1) // page_size
    items = [
        {
            "id": team.id,
            "name": team.name,
            "slug": team.slug,
            "description": team.description,
            "created_by": team.created_by,
            "created_at": team.created_at,
            "role": role,
            "project_count": int(count or 0),
        }
        for team, role, count in rows
    ]
    return items, total, pages


def add_member(db: Session, team_id: int, user_id: int, role: str):
    """
    Add a user to a team with a specific role.

    Creates a new TeamMember record. The role can be "admin" or "member".

    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): ID of the team to add the member to.
        user_id (int): ID of the user to add.
        role (str): Role to assign ("admin" or "member").

    Returns:
        TeamMember: The newly created member record.

    Raises:
        sqlalchemy.exc.IntegrityError: If user is already a member.

    Example:
        >>> add_member(db, team_id=1, user_id=2, role="member")
    """
    member = models.TeamMember(
        team_id=team_id,
        user_id=user_id,
        role=role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_member(
    db: Session,
    team_id: int,
    user_id: int,
    changed_by: int | None = None,
    commit: bool = True,
):
    """
    Remove a user from a team.

    Deletes the TeamMember record and unassigns every task the user had in the
    team's projects, so a former member never keeps work assigned.

    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): ID of the team.
        user_id (int): ID of the user to remove.
        changed_by (int | None): Admin performing the removal, for audit logs.
        commit (bool): Commit the transaction. Pass ``False`` when the caller
            already holds the team lock and needs to commit atomically.

    Returns:
        TeamMember | None: The deleted member record, or None if not found.

    Example:
        >>> remove_member(db, team_id=1, user_id=2)
    """
    member = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user_id,
        )
        .first()
    )
    if member:
        assigned_tasks = (
            db.query(models.Task)
            .join(models.Project, models.Task.project_id == models.Project.id)
            .filter(
                models.Project.team_id == team_id,
                models.Task.assigned_to == user_id,
            )
            .all()
        )
        for task in assigned_tasks:
            task.assigned_to = None  # type: ignore[assignment]
            if changed_by is not None:
                db.add(
                    models.ActivityLog(
                        entity_type="task",
                        entity_id=task.id,
                        action="unassigned",
                        changed_by=changed_by,
                        old_value=str(user_id),
                        new_value=None,
                    )
                )
        db.delete(member)
        if commit:
            db.commit()
        else:
            db.flush()
    return member


def get_team_members_paginated(db: Session, team_id: int, page: int, page_size: int):
    """Return a page of team members, ordered by join order.

    ``joinedload`` keeps ``TeamMemberOut.user`` from triggering one extra
    SELECT per member (T-117).
    """
    query = (
        db.query(models.TeamMember)
        .options(joinedload(models.TeamMember.user))
        .filter(models.TeamMember.team_id == team_id)
        .order_by(models.TeamMember.user_id)
    )
    return paginate_query(query, page, page_size)


def get_team_member(db: Session, team_id: int, user_id: int):
    """
    Get a specific member of a team.

    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): ID of the team.
        user_id (int): ID of the user.

    Returns:
        TeamMember | None: The member record if found, None otherwise.

    Example:
        >>> member = get_team_member(db, team_id=1, user_id=2)
    """
    return (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user_id,
        )
        .first()
    )


def lock_team_for_membership_change(db: Session, team_id: int) -> None:
    """Serialize membership changes that can remove an administrator.

    ``SELECT ... FOR UPDATE`` on the team row makes concurrent removals or
    demotions wait for each other, so two requests cannot both observe "two
    admins" and leave the team without one. SQLite ignores the clause, but the
    production database is PostgreSQL and the invariant test runs there.
    """
    db.query(models.Team).filter(models.Team.id == team_id).with_for_update().one()


def count_team_admins(db: Session, team_id: int) -> int:
    """Return the number of admins in a team.

    Used to enforce the invariant that a team always keeps at least one
    administrator before removing or demoting a member.
    """
    return (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.role == "admin",
        )
        .count()
    )


def update_member_role(db: Session, team_id: int, user_id: int, role: str, commit: bool = True):
    """
    Update a member's role in a team.

    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): ID of the team.
        user_id (int): ID of the user.
        role (str): New role to assign ("admin" or "member").
        commit (bool): Commit the transaction. Pass ``False`` when the caller
            already holds the team lock and needs to commit atomically.

    Returns:
        TeamMember | None: Updated member record, or None if not found.

    Example:
        >>> update_member_role(db, team_id=1, user_id=2, role="admin")
    """
    member = get_team_member(db, team_id, user_id)
    if member:
        member.role = role
        if commit:
            db.commit()
            db.refresh(member)
        else:
            db.flush()
    return member


def _unique_team_slug(db: Session, base_slug: str) -> str:
    """Return a team slug that is not used by any other team (FR-TEAM-01)."""
    base = slugify(base_slug, fallback="team")
    candidate = base
    suffix = 2
    while db.query(models.Team).filter(models.Team.slug == candidate).first() is not None:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate
