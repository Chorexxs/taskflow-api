"""Authentication payloads."""

from pydantic import BaseModel, EmailStr, field_validator

__all__ = [
    "EmailVerificationRequest",
    "ResendVerificationRequest",
    "MessageResponse",
    "Token",
    "TokenData",
    "RefreshTokenRequest",
    "LogoutRequest",
]


class EmailVerificationRequest(BaseModel):
    """Payload for POST /auth/verify-email."""

    token: str


class ResendVerificationRequest(BaseModel):
    """Payload for POST /auth/resend-verification."""

    email: EmailStr

    @field_validator("email", mode="after")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class MessageResponse(BaseModel):
    """Generic message response for verification endpoints."""

    message: str


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


class RefreshTokenRequest(BaseModel):
    """Request body for token refresh.

    Refresh tokens must travel in the request body, never in a query string
    or URL, so they cannot leak through logs or browser history.
    """

    refresh_token: str


class LogoutRequest(BaseModel):
    """Request body for logout.

    The refresh token is optional for backwards compatibility, but clients
    should always send it so the server can revoke the whole session.
    """

    refresh_token: str | None = None
