"""User request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from .common import validate_password

__all__ = [
    "UserBase",
    "UserMini",
    "UserCreate",
    "UserUpdate",
    "UserOut",
    "RegisterResponse",
]


class UserBase(BaseModel):
    """
    Base schema for user-related schemas.

    Contains the email field that is common to all user schemas.
    """

    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        """Store emails in lowercase so uniqueness is predictable."""
        return str(value).strip().lower()


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

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """
    Schema for user registration.

    Used in POST /auth/register endpoint.

    Attributes:
        email (EmailStr): Valid email address (validated by Pydantic)
        password (str): Plain text password (hashed before storage)
    """

    password: str

    @field_validator("password", mode="before")
    @classmethod
    def check_password_strength(cls, value):
        if isinstance(value, str):
            return validate_password(value)
        return value


class UserUpdate(BaseModel):
    """
    Schema for updating user profile.

    Used in PUT /users/me endpoint.
    Both email and password are optional - only provided fields are updated.
    Changing either requires the current password.

    Attributes:
        email (Optional[EmailStr]): New email address
        password (Optional[str]): New password (will be hashed)
        current_password (Optional[str]): Current password for verification

    Config:
        from_attributes: Allows creation from ORM objects
    """

    email: EmailStr | None = None
    password: str | None = None
    current_password: str | None = None

    @field_validator("email", mode="after")
    @classmethod
    def normalize_optional_email(cls, value):
        return str(value).strip().lower() if value is not None else value

    @field_validator("password", mode="before")
    @classmethod
    def check_optional_password_strength(cls, value):
        if isinstance(value, str):
            return validate_password(value)
        return value

    model_config = ConfigDict(from_attributes=True)


class UserOut(UserBase):
    """
    Schema for user data returned to clients.

    Used in responses that need to expose user information.
    Does NOT include password or sensitive data.

    Attributes:
        id (int): User's unique identifier
        email (EmailStr): User's email address
        is_active (bool): Whether the account is active
        email_verified (bool): Whether the email was verified
        created_at (datetime): Account creation timestamp

    Config:
        from_attributes: Allows creation from ORM objects
    """

    id: int
    is_active: bool
    email_verified: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RegisterResponse(BaseModel):
    """Registration result; ``message`` is used when verification is required."""

    id: int | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    email_verified: bool | None = None
    created_at: datetime | None = None
    message: str | None = None

    model_config = ConfigDict(from_attributes=True)
