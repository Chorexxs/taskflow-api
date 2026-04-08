"""
TaskFlow API - Database Operations (CRUD)

This module contains all database operations (Create, Read, Update, Delete)
for the application. Each function maps to specific API endpoints and
handles database interactions with proper error handling.

The module is organized by entity type:
- Users: User authentication and management
- Teams: Team CRUD and membership
- Projects: Project management within teams
- Tasks: Task management within projects
- Comments: Comment handling for tasks
- Attachments: File attachment management
- Activity: Audit log recording and retrieval
- Notifications: User notification management

Key patterns used:
- joinedload: Eager loading of relationships to prevent N+1 queries
- Soft deletes: Using status fields instead of actual deletes where appropriate
- Cache invalidation: Clearing cached data when entities are modified
"""

from datetime import datetime
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import get_password_hash, verify_password, get_current_user
from app.database import get_db
from fastapi import Depends


def get_current_user_from_token(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    """
    FastAPI dependency wrapper for getting current user in routes.
    
    This is a simple wrapper around get_current_user that can be used
    as a FastAPI dependency when you need the User object in a route.
    
    Args:
        current_user (User): The authenticated user from JWT token (injected by get_current_user).
    
    Returns:
        User: The authenticated user object.
    
    Example:
        @router.get("/profile")
        def get_profile(user: User = Depends(get_current_user_from_token)):
            return user
    """
    return current_user


def get_user_by_email(db: Session, email: str):
    """
    Retrieve a user by their email address.
    
    Used for authentication and user lookup. Email lookups are
    case-sensitive in most databases, but could be adapted for
    case-insensitive matching.
    
    Args:
        db (Session): SQLAlchemy database session.
        email (str): The user's email address to search for.
    
    Returns:
        User | None: The user if found, None otherwise.
    
    Example:
        >>> user = get_user_by_email(db, "user@example.com")
        >>> if user:
        ...     print(f"Found: {user.email}")
    """
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    """
    Retrieve a user by their ID.
    
    Used when you have a user ID and need to fetch the full user object.
    
    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): The user's unique identifier.
    
    Returns:
        User | None: The user if found, None otherwise.
    
    Example:
        >>> user = get_user_by_id(db, 123)
    """
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate):
    """
    Create a new user in the database.
    
    Hashes the password using bcrypt before storing. The user is created
    with default values: is_active=True, is_blocked=False, failed_login_attempts=0.
    
    Args:
        db (Session): SQLAlchemy database session.
        user (UserCreate): Schema containing email and password.
    
    Returns:
        User: The newly created user object with ID and timestamps.
    
    Raises:
        sqlalchemy.exc.IntegrityError: If email already exists (unique constraint).
    
    Example:
        >>> user_data = UserCreate(email="new@example.com", password="secure123")
        >>> new_user = create_user(db, user_data)
    """
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: schemas.UserCreate):
    """
    Update an existing user's email or password.
    
    Only updates fields that are provided (not None). If password is provided,
    it gets rehashed. Email updates are rare and should be validated.
    
    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): ID of the user to update.
        user_update (UserCreate): Schema with new email and/or password.
    
    Returns:
        User | None: Updated user object, or None if user not found.
    
    Example:
        >>> update = UserCreate(email="new@example.com", password="newpass")
        >>> updated = update_user(db, 123, update)
    """
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    if user_update.password:
        db_user.hashed_password = get_password_hash(user_update.password)
    if user_update.email:
        db_user.email = user_update.email
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    """
    Authenticate a user with email and password.
    
    This is a convenience function that checks both email existence
    and password validity. Used in the login endpoint.
    
    Args:
        db (Session): SQLAlchemy database session.
        email (str): User's email address.
        password (str): Plain text password to verify.
    
    Returns:
        User | bool: User object if authentication succeeds, False otherwise.
    
    Example:
        >>> result = authenticate_user(db, "user@example.com", "password123")
        >>> if result:
        ...     print("Authenticated!")
    """
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


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
        slug=team.slug,
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


def get_teams_by_user(db: Session, user_id: int):
    """
    Get all teams a user is a member of.
    
    Performs a JOIN between teams and team_members tables to find
    all teams where the user has membership.
    
    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): The user's ID.
    
    Returns:
        list[Team]: List of teams the user belongs to.
    
    Example:
        >>> teams = get_teams_by_user(db, user_id=1)
        >>> for team in teams:
        ...     print(team.name)
    """
    return (
        db.query(models.Team)
        .join(models.TeamMember)
        .filter(models.TeamMember.user_id == user_id)
        .all()
    )


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


def remove_member(db: Session, team_id: int, user_id: int):
    """
    Remove a user from a team.
    
    Deletes the TeamMember record. Also invalidates cached team data.
    
    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): ID of the team.
        user_id (int): ID of the user to remove.
    
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
        db.delete(member)
        db.commit()
        from app.cache import cache_service
        cache_service.invalidate_team(team_id)
    return member


def get_team_members(db: Session, team_id: int):
    """
    Get all members of a team.
    
    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): ID of the team.
    
    Returns:
        list[TeamMember]: List of all team members.
    
    Example:
        >>> members = get_team_members(db, team_id=1)
        >>> for m in members:
        ...     print(f"{m.user.email}: {m.role}")
    """
    return db.query(models.TeamMember).filter(models.TeamMember.team_id == team_id).all()


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


def update_member_role(db: Session, team_id: int, user_id: int, role: str):
    """
    Update a member's role in a team.
    
    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): ID of the team.
        user_id (int): ID of the user.
        role (str): New role to assign ("admin" or "member").
    
    Returns:
        TeamMember | None: Updated member record, or None if not found.
    
    Example:
        >>> update_member_role(db, team_id=1, user_id=2, role="admin")
    """
    member = get_team_member(db, team_id, user_id)
    if member:
        member.role = role
        db.commit()
        db.refresh(member)
    return member


def create_project(db: Session, project: schemas.ProjectCreate, team_id: int, user_id: int):
    """
    Create a new project within a team.
    
    Creates a project with the given name and description. The project
    is automatically set to "active" status.
    
    Args:
        db (Session): SQLAlchemy database session.
        project (ProjectCreate): Schema with project details.
        team_id (int): ID of the team to create the project in.
        user_id (int): ID of the user creating the project.
    
    Returns:
        Project: The newly created project object.
    
    Example:
        >>> project_data = ProjectCreate(name="Website Redesign", description="...")
        >>> new_project = create_project(db, project_data, team_id=1, user_id=1)
    """
    db_project = models.Project(
        team_id=team_id,
        name=project.name,
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
    from app.cache import cache_service
    cache_service.invalidate_project(project_id)
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
        from app.cache import cache_service
        cache_service.invalidate_project(project_id)
    return db_project


def create_task(db: Session, task: schemas.TaskCreate, project_id: int, user_id: int):
    """
    Create a new task within a project.
    
    Creates a task with the given title, description, priority, and optional
    due date and assignee. The task is created with status "todo".
    
    Args:
        db (Session): SQLAlchemy database session.
        task (TaskCreate): Schema with task details.
        project_id (int): ID of the project to create the task in.
        user_id (int): ID of the user creating the task.
    
    Returns:
        Task: The newly created task object.
    
    Example:
        >>> task_data = TaskCreate(
        ...     title="Fix bug",
        ...     description="Login issue",
        ...     priority=TaskPriority.high,
        ...     assigned_to=2
        ... )
        >>> new_task = create_task(db, task_data, project_id=1, user_id=1)
    """
    db_task = models.Task(
        project_id=project_id,
        title=task.title,
        description=task.description,
        priority=task.priority.value,
        due_date=task.due_date,
        created_by=user_id,
        assigned_to=task.assigned_to,
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task


def get_task_by_id(db: Session, task_id: int):
    """
    Retrieve a task by its ID with assignee loaded.
    
    Uses joinedload to eagerly load the assignee relationship,
    preventing N+1 queries when accessing task.assignee.
    
    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): The task's unique identifier.
    
    Returns:
        Task | None: The task with assignee loaded, or None if not found.
    
    Example:
        >>> task = get_task_by_id(db, 1)
        >>> print(task.assignee.email)  # No additional query
    """
    return db.query(models.Task).options(joinedload(models.Task.assignee)).filter(models.Task.id == task_id).first()


def get_tasks_by_project(
    db: Session,
    project_id: int,
    status: str = None,
    priority: str = None,
    assigned_to: int = None,
    due_before: datetime = None,
    due_after: datetime = None,
    sort_by: str = "created_at",
    order: str = "desc",
    page: int = 1,
    page_size: int = 20,
):
    """
    Get paginated and filtered tasks for a project.
    
    This is the main function for listing tasks. Supports:
    - Filtering by status, priority, assignee, due dates
    - Sorting by multiple fields
    - Pagination with configurable page size
    
    Uses joinedload to prevent N+1 queries on assignee.
    
    Args:
        db (Session): SQLAlchemy database session.
        project_id (int): ID of the project.
        status (str | None): Filter by status ("todo", "in_progress", "done").
        priority (str | None): Filter by priority ("low", "medium", "high").
        assigned_to (int | None): Filter by assignee user ID.
        due_before (datetime | None): Filter tasks due before this date.
        due_after (datetime | None): Filter tasks due after this date.
        sort_by (str): Field to sort by ("created_at", "title", "priority", "due_date", "status").
        order (str): Sort order ("asc" or "desc").
        page (int): Page number (1-indexed).
        page_size (int): Items per page (max 100).
    
    Returns:
        dict: Dictionary with items (list of tasks), total count, page info.
    
    Example:
        >>> result = get_tasks_by_project(
        ...     db, project_id=1,
        ...     status="todo",
        ...     priority="high",
        ...     sort_by="due_date",
        ...     order="asc",
        ...     page=1,
        ...     page_size=10
        ... )
        >>> print(result["total"])  # Total matching tasks
    """
    query = db.query(models.Task).options(joinedload(models.Task.assignee)).filter(models.Task.project_id == project_id)
    
    # Apply filters
    if status:
        query = query.filter(models.Task.status == status)
    if priority:
        query = query.filter(models.Task.priority == priority)
    if assigned_to is not None:
        query = query.filter(models.Task.assigned_to == assigned_to)
    if due_before:
        query = query.filter(models.Task.due_date <= due_before)
    if due_after:
        query = query.filter(models.Task.due_date >= due_after)
    
    # Determine sort column
    if sort_by == "title":
        order_col = models.Task.title
    elif sort_by == "due_date":
        order_col = models.Task.due_date
    elif sort_by == "priority":
        order_col = models.Task.priority
    elif sort_by == "status":
        order_col = models.Task.status
    else:
        order_col = models.Task.created_at
    
    # Apply sorting
    if order == "asc":
        query = query.order_by(order_col.asc())
    else:
        query = query.order_by(order_col.desc())
    
    # Get total count (before pagination)
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * page_size
    items = query.offset(offset).limit(page_size).all()
    
    return {"items": items, "total": total, "page": page, "pages": (total + page_size - 1) // page_size}


def update_task(db: Session, task_id: int, task_update: schemas.TaskUpdate):
    """
    Update a task's details.
    
    Only updates fields that are provided (not None). Supports updating
    title, description, status, priority, and due_date.
    
    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task to update.
        task_update (TaskUpdate): Schema with fields to update.
    
    Returns:
        Task | None: Updated task, or None if not found.
    
    Example:
        >>> update = TaskUpdate(status=TaskStatus.done, priority=TaskPriority.low)
        >>> updated = update_task(db, 1, update)
    """
    db_task = get_task_by_id(db, task_id)
    if not db_task:
        return None
    if task_update.title is not None:
        db_task.title = task_update.title
    if task_update.description is not None:
        db_task.description = task_update.description
    if task_update.status is not None:
        db_task.status = task_update.status.value
    if task_update.priority is not None:
        db_task.priority = task_update.priority.value
    if task_update.due_date is not None:
        db_task.due_date = task_update.due_date
    db.commit()
    db.refresh(db_task)
    return db_task


def assign_task(db: Session, task_id: int, user_id: int | None):
    """
    Assign or unassign a task.
    
    Set user_id to a user ID to assign, or None to unassign.
    
    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task.
        user_id (int | None): User ID to assign, or None to unassign.
    
    Returns:
        Task | None: Updated task, or None if not found.
    
    Example:
        >>> # Assign to user
        >>> assign_task(db, task_id=1, user_id=2)
        >>> # Unassign
        >>> assign_task(db, task_id=1, user_id=None)
    """
    db_task = get_task_by_id(db, task_id)
    if db_task:
        db_task.assigned_to = user_id
        db.commit()
        db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int):
    """
    Delete a task.
    
    Permanently removes the task from the database. This also deletes
    associated comments, attachments, and activity logs due to CASCADE.
    
    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task to delete.
    
    Returns:
        Task | None: The deleted task, or None if not found.
    
    Example:
        >>> delete_task(db, task_id=1)
    """
    db_task = get_task_by_id(db, task_id)
    if db_task:
        db.delete(db_task)
        db.commit()
    return db_task


def create_comment(db: Session, comment: schemas.CommentCreate, task_id: int, user_id: int):
    """
    Create a comment on a task.
    
    Args:
        db (Session): SQLAlchemy database session.
        comment (CommentCreate): Schema with comment content.
        task_id (int): ID of the task to comment on.
        user_id (int): ID of the user creating the comment.
    
    Returns:
        Comment: The newly created comment.
    
    Example:
        >>> comment_data = CommentCreate(content="This looks great!")
        >>> new_comment = create_comment(db, comment_data, task_id=1, user_id=1)
    """
    db_comment = models.Comment(
        task_id=task_id,
        author_id=user_id,
        content=comment.content,
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


def get_comment_by_id(db: Session, comment_id: int):
    """
    Retrieve a comment by its ID.
    
    Args:
        db (Session): SQLAlchemy database session.
        comment_id (int): The comment's unique identifier.
    
    Returns:
        Comment | None: The comment if found, None otherwise.
    """
    return db.query(models.Comment).filter(models.Comment.id == comment_id).first()


def get_comments_by_task(db: Session, task_id: int):
    """
    Get all comments for a task, ordered by creation (newest first).
    
    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task.
    
    Returns:
        list[Comment]: List of comments for the task.
    
    Example:
        >>> comments = get_comments_by_task(db, task_id=1)
    """
    return db.query(models.Comment).filter(models.Comment.task_id == task_id).order_by(models.Comment.created_at.desc()).all()


def update_comment(db: Session, comment_id: int, content: str):
    """
    Update a comment's content.
    
    Args:
        db (Session): SQLAlchemy database session.
        comment_id (int): ID of the comment to update.
        content (str): New comment content.
    
    Returns:
        Comment | None: Updated comment, or None if not found.
    
    Example:
        >>> update_comment(db, comment_id=1, content="Updated content")
    """
    db_comment = get_comment_by_id(db, comment_id)
    if db_comment:
        db_comment.content = content
        db.commit()
        db.refresh(db_comment)
    return db_comment


def delete_comment(db: Session, comment_id: int):
    """
    Delete a comment.
    
    Args:
        db (Session): SQLAlchemy database session.
        comment_id (int): ID of the comment to delete.
    
    Returns:
        Comment | None: The deleted comment, or None if not found.
    """
    db_comment = get_comment_by_id(db, comment_id)
    if db_comment:
        db.delete(db_comment)
        db.commit()
    return db_comment


def log_activity(db: Session, entity_type: str, entity_id: int, action: str, user_id: int, old_value: str = None, new_value: str = None):
    """
    Create an activity log entry for audit purposes.
    
    Records actions performed on entities like tasks, projects, and teams.
    The old_value and new_value fields store string representations
    of the changes (e.g., JSON for complex values).
    
    Args:
        db (Session): SQLAlchemy database session.
        entity_type (str): Type of entity ("task", "project", "team", etc.)
        entity_id (int): ID of the entity that was changed.
        action (str): Action performed ("created", "updated", "assigned", etc.)
        user_id (int): ID of the user who performed the action.
        old_value (str | None): Previous value as string.
        new_value (str | None): New value as string.
    
    Returns:
        ActivityLog: The newly created activity log entry.
    
    Example:
        >>> log_activity(
        ...     db,
        ...     entity_type="task",
        ...     entity_id=1,
        ...     action="assigned",
        ...     user_id=1,
        ...     old_value=None,
        ...     new_value="user@example.com"
        ... )
    """
    db_activity = models.ActivityLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        changed_by=user_id,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(db_activity)
    db.commit()
    db.refresh(db_activity)
    return db_activity


def get_activity_by_task(db: Session, task_id: int):
    """
    Get all activity logs for a task, ordered by creation (newest first).
    
    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task.
    
    Returns:
        list[ActivityLog]: List of activity logs for the task.
    
    Example:
        >>> logs = get_activity_by_task(db, task_id=1)
    """
    return db.query(models.ActivityLog).filter(
        models.ActivityLog.entity_type == "task",
        models.ActivityLog.entity_id == task_id
    ).order_by(models.ActivityLog.created_at.desc()).all()


def get_activity_by_project(db: Session, project_id: int):
    """
    Get all activity logs for a project, ordered by creation (newest first).
    
    Args:
        db (Session): SQLAlchemy database session.
        project_id (int): ID of the project.
    
    Returns:
        list[ActivityLog]: List of activity logs for the project.
    
    Example:
        >>> logs = get_activity_by_project(db, project_id=1)
    """
    return db.query(models.ActivityLog).filter(
        models.ActivityLog.entity_type == "project",
        models.ActivityLog.entity_id == project_id
    ).order_by(models.ActivityLog.created_at.desc()).all()


def search_in_team(db: Session, team_id: int, query: str):
    """
    Search for projects and tasks in a team by name/title.
    
    Performs case-insensitive search using LIKE. Searches project names
    first, then finds tasks in those projects.
    
    Args:
        db (Session): SQLAlchemy database session.
        team_id (int): ID of the team to search in.
        query (str): Search term.
    
    Returns:
        dict: Dictionary with "projects" and "tasks" lists.
    
    Example:
        >>> results = search_in_team(db, team_id=1, query="website")
        >>> print(f"Found {len(results['projects'])} projects")
        >>> print(f"Found {len(results['tasks'])} tasks")
    """
    # Search projects
    projects = db.query(models.Project).filter(
        models.Project.team_id == team_id,
        models.Project.status == "active",
        models.Project.name.ilike(f"%{query}%")
    ).all()
    
    # Get project IDs for task search
    project_ids = [p.id for p in projects]
    
    # Search tasks in found projects
    tasks = []
    if project_ids:
        tasks = db.query(models.Task).filter(
            models.Task.project_id.in_(project_ids),
            models.Task.title.ilike(f"%{query}%")
        ).all()
    
    return {"projects": projects, "tasks": tasks}


def create_attachment(db: Session, task_id: int, user_id: int, filename: str, file_path: str, file_size: int, mime_type: str):
    """
    Create an attachment record for an uploaded file.
    
    Note: This only creates the database record. The actual file
    should be saved to disk separately.
    
    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task to attach the file to.
        user_id (int): ID of the user uploading the file.
        filename (str): Original filename.
        file_path (str): Path where the file is stored.
        file_size (int): Size of the file in bytes.
        mime_type (str): MIME type of the file.
    
    Returns:
        Attachment: The newly created attachment record.
    
    Example:
        >>> create_attachment(
        ...     db, task_id=1, user_id=1,
        ...     filename="document.pdf",
        ...     file_path="/uploads/123_document.pdf",
        ...     file_size=1024000,
        ...     mime_type="application/pdf"
        ... )
    """
    db_attachment = models.Attachment(
        task_id=task_id,
        uploaded_by=user_id,
        filename=filename,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
    )
    db.add(db_attachment)
    db.commit()
    db.refresh(db_attachment)
    return db_attachment


def get_attachment_by_id(db: Session, attachment_id: int):
    """
    Retrieve an attachment by its ID.
    
    Args:
        db (Session): SQLAlchemy database session.
        attachment_id (int): The attachment's unique identifier.
    
    Returns:
        Attachment | None: The attachment if found, None otherwise.
    """
    return db.query(models.Attachment).filter(models.Attachment.id == attachment_id).first()


def get_attachments_by_task(db: Session, task_id: int):
    """
    Get all attachments for a task.
    
    Args:
        db (Session): SQLAlchemy database session.
        task_id (int): ID of the task.
    
    Returns:
        list[Attachment]: List of attachments for the task.
    """
    return db.query(models.Attachment).filter(models.Attachment.task_id == task_id).all()


def delete_attachment(db: Session, attachment_id: int):
    """
    Delete an attachment record.
    
    Note: This only deletes the database record. The actual file
    should be deleted from disk separately.
    
    Args:
        db (Session): SQLAlchemy database session.
        attachment_id (int): ID of the attachment to delete.
    
    Returns:
        Attachment | None: The deleted attachment, or None if not found.
    """
    db_attachment = get_attachment_by_id(db, attachment_id)
    if db_attachment:
        db.delete(db_attachment)
        db.commit()
    return db_attachment


def create_notification(db: Session, user_id: int, notification_type: str, entity_type: str, entity_id: int, message: str):
    """
    Create a notification for a user.
    
    Notifications are created when events occur that the user should
    be aware of, such as being assigned to a task.
    
    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): ID of the user to notify.
        notification_type (str): Type of notification ("assigned", "commented", etc.)
        entity_type (str): Type of related entity.
        entity_id (int): ID of the related entity.
        message (str): Human-readable notification message.
    
    Returns:
        Notification: The newly created notification.
    
    Example:
        >>> create_notification(
        ...     db,
        ...     user_id=2,
        ...     notification_type="assigned",
        ...     entity_type="task",
        ...     entity_id=1,
        ...     message="You have been assigned to: Fix bug"
        ... )
    """
    db_notification = models.Notification(
        user_id=user_id,
        type=notification_type,
        entity_type=entity_type,
        entity_id=entity_id,
        message=message,
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


def get_notifications_by_user(db: Session, user_id: int, is_read: bool = None):
    """
    Get notifications for a user, optionally filtered by read status.
    
    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): ID of the user.
        is_read (bool | None): Filter by read status. None = all, True = read, False = unread.
    
    Returns:
        list[Notification]: List of notifications ordered by creation (newest first).
    
    Example:
        >>> all = get_notifications_by_user(db, user_id=1)
        >>> unread = get_notifications_by_user(db, user_id=1, is_read=False)
    """
    query = db.query(models.Notification).filter(models.Notification.user_id == user_id)
    if is_read is not None:
        query = query.filter(models.Notification.is_read == is_read)
    return query.order_by(models.Notification.created_at.desc()).all()


def get_notification_by_id(db: Session, notification_id: int):
    """
    Retrieve a notification by its ID.
    
    Args:
        db (Session): SQLAlchemy database session.
        notification_id (int): The notification's unique identifier.
    
    Returns:
        Notification | None: The notification if found, None otherwise.
    """
    return db.query(models.Notification).filter(models.Notification.id == notification_id).first()


def mark_notification_read(db: Session, notification_id: int):
    """
    Mark a single notification as read.
    
    Args:
        db (Session): SQLAlchemy database session.
        notification_id (int): ID of the notification to mark as read.
    
    Returns:
        Notification | None: Updated notification, or None if not found.
    """
    db_notification = get_notification_by_id(db, notification_id)
    if db_notification:
        db_notification.is_read = True
        db.commit()
        db.refresh(db_notification)
    return db_notification


def mark_all_notifications_read(db: Session, user_id: int):
    """
    Mark all notifications for a user as read.
    
    Uses a bulk update operation for efficiency.
    
    Args:
        db (Session): SQLAlchemy database session.
        user_id (int): ID of the user.
    
    Returns:
        None: This function doesn't return anything.
    
    Example:
        >>> mark_all_notifications_read(db, user_id=1)
    """
    db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
