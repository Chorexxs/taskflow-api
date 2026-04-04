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
