from enum import Enum
from pydantic import BaseModel, EmailStr
from datetime import datetime


class TeamRole(str, Enum):
    admin = "admin"
    member = "member"


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str | None = None


class TeamCreate(BaseModel):
    name: str
    slug: str
    description: str | None = None


class TeamOut(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    created_by: int
    created_at: datetime

    class Config:
        from_attributes = True


class TeamMemberOut(BaseModel):
    team_id: int
    user_id: int
    role: TeamRole
    joined_at: datetime
    user: UserOut

    class Config:
        from_attributes = True


class TeamMemberUpdate(BaseModel):
    role: TeamRole


class TeamMemberAdd(BaseModel):
    email: EmailStr
    role: TeamRole = TeamRole.member


class ProjectStatus(str, Enum):
    active = "active"
    archived = "archived"


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    status: ProjectStatus | None = None


class ProjectOut(BaseModel):
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
    todo = "todo"
    in_progress = "in_progress"
    done = "done"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: TaskPriority = TaskPriority.medium
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None


class TaskAssign(BaseModel):
    user_id: int | None = None


class TaskOut(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assigned_to: int | None
    due_date: datetime | None
    created_by: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str


class CommentUpdate(BaseModel):
    content: str


class CommentOut(BaseModel):
    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ActivityLogOut(BaseModel):
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
    items: list[TaskOut]
    total: int
    page: int
    pages: int


class SearchResult(BaseModel):
    projects: list[ProjectOut]
    tasks: list[TaskOut]


class AttachmentOut(BaseModel):
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
    is_read: bool
