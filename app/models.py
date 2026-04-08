"""
TaskFlow API - Database Models

This module defines all SQLAlchemy ORM models for the application.
Each model represents a database table with its columns and relationships.

Models:
- User: Registered users in the system
- Team: Teams that users can create and join
- TeamMember: Many-to-many relationship between users and teams
- Project: Projects within teams
- Task: Tasks within projects
- Comment: Comments on tasks
- Attachment: File attachments on tasks
- ActivityLog: Audit trail for entity changes
- Notification: User notifications
- RevokedToken: Tokens that have been invalidated

Relationships:
- User 1:N Team (via created_by)
- Team 1:N TeamMember (N:N via TeamMember)
- Team 1:N Project
- Project 1:N Task
- Task 1:N Comment
- Task 1:N Attachment
- Task 1:N ActivityLog
- User 1:N Notification
- User 1:N RevokedToken
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    """
    User model representing a registered user in the system.
    
    Attributes:
        id (Integer): Primary key, auto-generated
        email (String): Unique email address, used for login
        hashed_password (String): Bcrypt-hashed password
        is_active (Boolean): Whether the account is active
        is_blocked (Boolean): Whether the account is blocked (failed login attempts)
        failed_login_attempts (Integer): Count of consecutive failed logins
        locked_until (DateTime): If blocked, when the lock expires
        created_at (DateTime): Account creation timestamp
    
    Relationships:
        - created_teams: Teams created by this user
        - team_memberships: TeamMember records for teams this user belongs to
    
    Table: users
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_blocked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Team(Base):
    """
    Team model representing a group of users working together.
    
    A team has members with different roles (admin, member) and contains
    projects. Teams are identified by a unique slug for URLs.
    
    Attributes:
        id (Integer): Primary key, auto-generated
        name (String): Team display name
        slug (String): Unique URL-friendly identifier
        description (String): Optional team description
        created_by (Integer): Foreign key to User who created the team
        created_at (DateTime): Team creation timestamp
    
    Relationships:
        - members: TeamMember records for all team members
        - creator: User who created the team
        - projects: All projects in this team
    
    Table: teams
    Indexes:
        - slug: Unique index for slug lookups
    """
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(String(500), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    creator = relationship("User")


class TeamMember(Base):
    """
    TeamMember model representing the many-to-many relationship between users and teams.
    
    This is a junction table that connects users to teams with a specific role.
    Uses composite primary key (team_id, user_id) to ensure uniqueness.
    
    Attributes:
        team_id (Integer): Foreign key to Team
        user_id (Integer): Foreign key to User
        role (String): User's role in the team ("admin" or "member")
        joined_at (DateTime): When the user joined the team
    
    Relationships:
        - team: The Team this member belongs to
        - user: The User who is a member
    
    Table: team_members
    Indexes:
        - role: Index for role-based queries
    """
    __tablename__ = "team_members"

    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(20), default="member", index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team", back_populates="members")
    user = relationship("User")


class Project(Base):
    """
    Project model representing a project within a team.
    
    Projects organize tasks and can be archived when no longer active.
    
    Attributes:
        id (Integer): Primary key, auto-generated
        team_id (Integer): Foreign key to the team this project belongs to
        name (String): Project name
        description (String): Optional project description
        status (String): Project status ("active" or "archived")
        created_by (Integer): Foreign key to User who created the project
        created_at (DateTime): Project creation timestamp
    
    Relationships:
        - team: The Team this project belongs to
        - creator: User who created the project
        - tasks: All tasks in this project
    
    Table: projects
    Indexes:
        - ix_projects_team_status: Composite index for filtering by team and status
    """
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_team_status", "team_id", "status"),
    )

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    status = Column(String(20), default="active", index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    team = relationship("Team")
    creator = relationship("User")


class Task(Base):
    """
    Task model representing a task within a project.
    
    Tasks have status (todo, in_progress, done), priority (low, medium, high),
    can be assigned to team members, and have due dates.
    
    Attributes:
        id (Integer): Primary key, auto-generated
        project_id (Integer): Foreign key to the project this task belongs to
        title (String): Task title (required)
        description (String): Task description (optional)
        status (String): Task status ("todo", "in_progress", "done")
        priority (String): Task priority ("low", "medium", "high")
        assigned_to (Integer): Foreign key to User assigned to this task (optional)
        due_date (DateTime): Optional due date
        created_by (Integer): Foreign key to User who created the task
        created_at (DateTime): Task creation timestamp
        updated_at (DateTime): Last update timestamp
    
    Relationships:
        - project: The Project this task belongs to
        - creator: User who created the task
        - assignee: User assigned to this task
    
    Table: tasks
    Indexes:
        - ix_tasks_project_status: Composite index for filtering by project and status
        - ix_tasks_project_priority: Composite index for filtering by project and priority
        - ix_tasks_assigned_to: Index for filtering by assignee
        - ix_tasks_due_date: Index for filtering by due date
        - ix_tasks_created_at: Index for sorting by creation date
    """
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_project_status", "project_id", "status"),
        Index("ix_tasks_project_priority", "project_id", "priority"),
        Index("ix_tasks_assigned_to", "assigned_to"),
        Index("ix_tasks_due_date", "due_date"),
        Index("ix_tasks_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    status = Column(String(20), default="todo")
    priority = Column(String(20), default="medium")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project")
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])


class Comment(Base):
    """
    Comment model representing a comment on a task.
    
    Comments allow team members to discuss task details.
    
    Attributes:
        id (Integer): Primary key, auto-generated
        task_id (Integer): Foreign key to the task this comment belongs to
        author_id (Integer): Foreign key to User who wrote the comment
        content (String): Comment text (max 2000 chars)
        created_at (DateTime): Comment creation timestamp
        updated_at (DateTime): Last update timestamp
    
    Relationships:
        - task: The Task this comment belongs to
        - author: User who wrote the comment
    
    Table: comments
    """
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(String(2000), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    task = relationship("Task")
    author = relationship("User")


class Attachment(Base):
    """
    Attachment model representing a file attached to a task.
    
    Stores metadata about uploaded files. The actual file content
    is stored on disk, not in the database.
    
    Attributes:
        id (Integer): Primary key, auto-generated
        task_id (Integer): Foreign key to the task this attachment belongs to
        uploaded_by (Integer): Foreign key to User who uploaded the file
        filename (String): Original filename
        file_path (String): Path to the file on disk
        file_size (Integer): File size in bytes
        mime_type (String): MIME type of the file
        created_at (DateTime): Upload timestamp
    
    Relationships:
        - task: The Task this attachment belongs to
        - uploader: User who uploaded the file
    
    Table: attachments
    """
    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    uploaded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    task = relationship("Task")
    uploader = relationship("User")


class ActivityLog(Base):
    """
    ActivityLog model representing an audit entry for entity changes.
    
    Tracks all changes to tasks, projects, and team memberships for audit purposes.
    
    Attributes:
        id (Integer): Primary key, auto-generated
        entity_type (String): Type of entity ("task", "project", "team", etc.)
        entity_id (Integer): ID of the entity that was changed
        action (String): Action performed ("created", "updated", "deleted", "assigned", etc.)
        changed_by (Integer): Foreign key to User who made the change
        old_value (String): Previous value (JSON string for complex values)
        new_value (String): New value (JSON string for complex values)
        created_at (DateTime): When the change occurred
    
    Relationships:
        - user: User who made the change
    
    Table: activity_logs
    
    Example:
        >>> # Task assignment logged
        >>> ActivityLog(
        ...     entity_type="task",
        ...     entity_id=123,
        ...     action="assigned",
        ...     changed_by=456,
        ...     old_value=None,
        ...     new_value="user@example.com"
        ... )
    """
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    action = Column(String(50), nullable=False)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    old_value = Column(String(1000), nullable=True)
    new_value = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class Notification(Base):
    """
    Notification model representing a user notification.
    
    Notifications are created when something happens that the user
    should be aware of (e.g., task assignment, comment mention).
    
    Attributes:
        id (Integer): Primary key, auto-generated
        user_id (Integer): Foreign key to User who receives the notification
        type (String): Notification type ("assigned", "commented", "updated", etc.)
        entity_type (String): Type of entity related to the notification
        entity_id (Integer): ID of the related entity
        message (String): Human-readable notification message
        is_read (Boolean): Whether the user has read the notification
        created_at (DateTime): When the notification was created
    
    Relationships:
        - user: User who receives the notification
    
    Table: notifications
    """
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=False)
    message = Column(String(500), nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")


class RevokedToken(Base):
    """
    RevokedToken model representing a token that has been invalidated.
    
    Stores tokens that have been revoked (logged out, refreshed, etc.)
    to prevent their reuse. Expired tokens are periodically cleaned up.
    
    Attributes:
        id (Integer): Primary key, auto-generated
        token (String): The actual JWT token string
        token_type (String): Type of token ("access" or "refresh")
        revoked_at (DateTime): When the token was revoked
        expires_at (DateTime): When the token expires (for cleanup)
    
    Table: revoked_tokens
    Indexes:
        - token: Unique index for quick lookups
    """
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(500), unique=True, index=True, nullable=False)
    token_type = Column(String(20), default="access")
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
