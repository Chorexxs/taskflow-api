"""
TaskFlow API - Pydantic Schemas

This module defines all Pydantic schemas used for request/response validation.
Schemas are used for:
- Request body validation
- Response serialization
- API documentation generation

Enums:
- TeamRole: "admin", "member"
- ProjectStatus: "active", "archived"
- TaskStatus: "todo", "in_progress", "done"
- TaskPriority: "low", "medium", "high"

Schemas (Create):
- UserCreate: Email and password for registration
- TeamCreate: Name, slug, description
- ProjectCreate: Name, description
- TaskCreate: Title, description, priority, due_date, assigned_to
- TaskUpdate: Optional fields for updates
- TaskAssign: User assignment
- CommentCreate, CommentUpdate: Comment content
- TeamMemberAdd: Email and role for inviting members
- TeamMemberUpdate: Role update
- NotificationUpdate: Read status

Schemas (Response):
- UserOut: User data returned to clients
- UserMini: Minimal user info (id, email)
- Token: Access and refresh tokens
- TokenData: Token payload data
- TeamOut: Full team data with metadata
- TeamMemberOut: Team member with user details
- ProjectOut: Project data with status
- TaskOut: Full task data with assignee
- CommentOut: Comment with metadata
- ActivityLogOut: Activity log entry
- AttachmentOut: Attachment metadata
- NotificationOut: Notification with read status
- PaginatedTaskResponse: Paginated task list

Utility:
- sanitize_text: Remove control characters from input
"""

import re
from enum import Enum
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime

# Pattern to match control characters that should be removed from input
CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x1f\x7f-\x9f]')


def sanitize_text(text: str) -> str:
    """
    Remove control characters from text input for security.
    
    Prevents XSS and injection attacks by stripping control characters
    (ASCII 0-31 and 127-159) that could be used maliciously.
    
    Args:
        text (str): The input text to sanitize.
    
    Returns:
        str: The sanitized text with control characters removed.
    
    Example:
        >>> sanitize_text("Hello\x00World")
        'HelloWorld'
        >>> sanitize_text("Test\r\n")
        'Test'
    """
    return CONTROL_CHARS_PATTERN.sub('', text).strip()


class TeamRole(str, Enum):
    """
    Enum representing team member roles.
    
    Attributes:
        admin: Can manage team members, projects, and all team resources
        member: Can view and work within team projects
    """
    admin = "admin"
    member = "member"


class UserBase(BaseModel):
    """
    Base schema for user-related schemas.
    
    Contains the email field that is common to all user schemas.
    """
    email: EmailStr


class UserMini(BaseModel):
    """
    Minimal user schema for nested responses.
    
    Used when embedding user information in other responses,
    such as task assignee information.
    
    Attributes:
        id (int): User's unique identifier
        email (EmailStr): User's email address
    
    Config:
        from_attributes: Allows creation from ORM objects
    """
    id: int
    email: EmailStr
    
    class Config:
        from_attributes = True


class UserCreate(UserBase):
    """
    Schema for user registration.
    
    Used in POST /auth/register endpoint.
    
    Attributes:
        email (EmailStr): Valid email address (validated by Pydantic)
        password (str): Plain text password (hashed before storage)
    """
    password: str


class UserOut(UserBase):
    """
    Schema for user data returned to clients.
    
    Used in responses that need to expose user information.
    Does NOT include password or sensitive data.
    
    Attributes:
        id (int): User's unique identifier
        email (EmailStr): User's email address
        is_active (bool): Whether the account is active
        created_at (datetime): Account creation timestamp
    
    Config:
        from_attributes: Allows creation from ORM objects
    """
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """
    Schema for authentication token response.
    
    Returned on successful login and token refresh.
    
    Attributes:
        access_token (str): JWT access token for API authentication
        refresh_token (str | None): JWT refresh token for session extension
        token_type (str): Token type ("bearer")
    """
    access_token: str
    refresh_token: str | None = None
    token_type: str


class TokenData(BaseModel):
    """
    Schema for JWT token payload data.
    
    Used internally for decoding and validating tokens.
    
    Attributes:
        email (str | None): User email from token "sub" claim
    """
    email: str | None = None


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
    slug: str
    description: str | None = None

    @field_validator('name', 'slug', 'description', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
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

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


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
        description (str | None): Optional project description
    
    Validators:
        sanitize_input: Removes control characters from text fields
    """
    name: str
    description: str | None = None

    @field_validator('name', 'description', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


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

    @field_validator('name', 'description', mode='before')
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
    description: str | None
    status: ProjectStatus
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class TaskStatus(str, Enum):
    """
    Enum representing task status.
    
    Attributes:
        todo: Task needs to be done
        in_progress: Task is being worked on
        done: Task is completed
    """
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(str, Enum):
    """
    Enum representing task priority.
    
    Attributes:
        low: Low priority task
        medium: Medium priority task
        high: High priority task
    """
    low = "low"
    medium = "medium"
    high = "high"


class TaskCreate(BaseModel):
    """
    Schema for task creation.
    
    Used in POST /teams/{id}/projects/{id}/tasks endpoint.
    
    Attributes:
        title (str): Task title (required)
        description (str | None): Task description
        priority (TaskPriority): Task priority (default: medium)
        due_date (datetime | None): Optional due date
        assigned_to (int | None): User ID to assign the task to
    
    Validators:
        sanitize_input: Removes control characters from text fields
    
    Example:
        >>> task = TaskCreate(
        ...     title="Fix login bug",
        ...     description="Users cannot login with special characters",
        ...     priority=TaskPriority.high,
        ...     assigned_to=123
        ... )
    """
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.medium
    due_date: datetime | None = None
    assigned_to: int | None = None

    @field_validator('title', 'description', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class TaskUpdate(BaseModel):
    """
    Schema for task updates.
    
    Used in PATCH /teams/{id}/projects/{id}/tasks/{id} endpoint.
    All fields are optional - only included fields are updated.
    
    Attributes:
        title (str | None): New task title
        description (str | None): New task description
        status (TaskStatus | None): New task status
        priority (TaskPriority | None): New task priority
        due_date (datetime | None): New due date
    
    Validators:
        sanitize_input: Removes control characters from text fields
    """
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None

    @field_validator('title', 'description', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class TaskAssign(BaseModel):
    """
    Schema for assigning a task to a user.
    
    Used in PATCH /teams/{id}/projects/{id}/tasks/{id}/assign endpoint.
    
    Attributes:
        user_id (int | None): User ID to assign. None to unassign.
    
    Example:
        >>> # Assign to user
        >>> TaskAssign(user_id=123)
        >>> # Unassign
        >>> TaskAssign(user_id=None)
    """
    user_id: int | None = None


class TaskOut(BaseModel):
    """
    Schema for task response data.
    
    Used in task list, detail, and creation endpoints.
    Includes assignee information for displaying task ownership.
    
    Attributes:
        id (int): Task's unique identifier
        project_id (int): Project the task belongs to
        title (str): Task title
        description (str | None): Task description
        status (TaskStatus): Task status
        priority (TaskPriority): Task priority
        assigned_to (int | None): User ID of assignee
        assignee (UserMini | None): Full assignee user object
        due_date (datetime | None): Task due date
        created_by (int): ID of user who created the task
        created_at (datetime): Task creation timestamp
        updated_at (datetime): Last update timestamp
    
    Config:
        from_attributes: Allows creation from ORM objects
    """
    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assigned_to: int | None
    assignee: UserMini | None
    due_date: datetime | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    """
    Schema for creating a comment.
    
    Used in POST /tasks/{id}/comments endpoint.
    
    Attributes:
        content (str): Comment text (required)
    
    Validators:
        sanitize_input: Removes control characters from text
    """
    content: str

    @field_validator('content', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class CommentUpdate(BaseModel):
    """
    Schema for updating a comment.
    
    Used in PATCH /tasks/{id}/comments/{id} endpoint.
    
    Attributes:
        content (str): New comment text
    
    Validators:
        sanitize_input: Removes control characters from text
    """
    content: str

    @field_validator('content', mode='before')
    @classmethod
    def sanitize_input(cls, v):
        """Remove control characters from input."""
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class CommentOut(BaseModel):
    """
    Schema for comment response data.
    
    Used in comment list and detail endpoints.
    
    Attributes:
        id (int): Comment's unique identifier
        task_id (int): Task the comment belongs to
        author_id (int): User who wrote the comment
        content (str): Comment text
        created_at (datetime): Comment creation timestamp
        updated_at (datetime): Last update timestamp
    
    Config:
        from_attributes: Allows creation from ORM objects
    """
    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActivityLogOut(BaseModel):
    """
    Schema for activity log response.
    
    Used in activity endpoints for tasks and projects.
    
    Attributes:
        id (int): Log entry ID
        entity_type (str): Type of entity (task, project, etc.)
        entity_id (int): ID of the entity
        action (str): Action performed
        changed_by (int): User who performed the action
        old_value (str | None): Previous value
        new_value (str | None): New value
        created_at (datetime): When the action occurred
    
    Config:
        from_attributes: Allows creation from ORM objects
    """
    id: int
    entity_type: str
    entity_id: int
    action: str
    changed_by: int
    old_value: str | None
    new_value: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedTaskResponse(BaseModel):
    """
    Schema for paginated task list response.
    
    Used in GET /tasks endpoint for paginated results.
    
    Attributes:
        items (list[TaskOut]): List of tasks for the current page
        total (int): Total number of tasks matching the query
        page (int): Current page number
        pages (int): Total number of pages
        has_next (bool | None): Whether there's a next page
        next_cursor (str | None): Cursor for next page (if using cursor pagination)
    """
    items: list[TaskOut]
    total: int
    page: int
    pages: int
    has_next: bool | None = None
    next_cursor: str | None = None


class CursorPaginatedResponse(BaseModel):
    """
    Schema for cursor-based pagination.
    
    Alternative pagination strategy for large datasets.
    
    Attributes:
        items (list): List of items for the current page
        next_cursor (str | None): Cursor for next page
        has_more (bool): Whether there are more items
    """
    items: list
    next_cursor: str | None = None
    has_more: bool = False


class SearchResult(BaseModel):
    """
    Schema for search results.
    
    Used in team search endpoint.
    
    Attributes:
        projects (list[ProjectOut]): Matching projects
        tasks (list[TaskOut]): Matching tasks
    """
    projects: list[ProjectOut]
    tasks: list[TaskOut]


class AttachmentOut(BaseModel):
    """
    Schema for attachment response data.
    
    Used in attachment list and upload endpoints.
    
    Attributes:
        id (int): Attachment's unique identifier
        task_id (int): Task the attachment belongs to
        uploaded_by (int): User who uploaded the file
        filename (str): Original filename
        file_path (str): Path to file on disk
        file_size (int): File size in bytes
        mime_type (str): MIME type of the file
        created_at (datetime): Upload timestamp
    
    Config:
        from_attributes: Allows creation from ORM objects
    """
    id: int
    task_id: int
    uploaded_by: int
    filename: str
    file_path: str
    file_size: int
    mime_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    """
    Schema for notification response data.
    
    Used in notification list and update endpoints.
    
    Attributes:
        id (int): Notification's unique identifier
        user_id (int): User who receives the notification
        type (str): Notification type
        entity_type (str): Related entity type
        entity_id (int): Related entity ID
        message (str): Human-readable message
        is_read (bool): Whether notification has been read
        created_at (datetime): Notification creation timestamp
    
    Config:
        from_attributes: Allows creation from ORM objects
    """
    id: int
    user_id: int
    type: str
    entity_type: str
    entity_id: int
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationUpdate(BaseModel):
    """
    Schema for updating notification read status.
    
    Used in PATCH /notifications/{id} endpoint.
    
    Attributes:
        is_read (bool): New read status
    """
    is_read: bool
