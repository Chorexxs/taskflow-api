"""
TaskFlow API - Authentication Module

This module handles all authentication-related functionality including:
- JWT token creation and validation
- Password hashing with bcrypt
- User lockout after failed login attempts
- Token revocation and refresh

The authentication system uses:
- Access tokens: Short-lived (15 min default) for API access
- Refresh tokens: Long-lived (7 days default) for session persistence
- Token rotation: New tokens issued on refresh, old ones revoked
- Account lockout: After 5 failed attempts, locked for 15 minutes
"""

import os
import uuid
import warnings
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session

load_dotenv()

from app.database import get_db


# OAuth2 scheme for extracting Bearer token from Authorization header
# tokenUrl points to the login endpoint for OpenAPI documentation
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Supports loading from .env file via pydantic-settings.
    All settings are case-insensitive for flexibility.
    """
    model_config = ConfigDict(env_file=".env", extra="allow", case_sensitive=False)

    SECRET_KEY: str = ""  # Secret key for JWT signing
    ALGORITHM: str = "HS256"  # JWT algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # Access token lifetime
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # Refresh token lifetime
    MAX_LOGIN_ATTEMPTS: int = 5  # Failed attempts before lockout
    LOCKOUT_DURATION_MINUTES: int = 15  # Lockout duration


# Initialize settings singleton
settings = Settings()


# Get secret key from settings or environment
# Falls back to temp key in development (with warning)
SECRET_KEY = settings.SECRET_KEY or os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    warnings.warn("SECRET_KEY is not set, using a temporary key for development")
    SECRET_KEY = "temp-dev-key-do-not-use-in-production"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.
    
    Uses bcrypt for secure password verification. The function handles
    encoding conversion between UTF-8 bytes and strings.
    
    Args:
        plain_password (str): The plain text password to verify.
        hashed_password (str): The bcrypt hashed password to compare against.
    
    Returns:
        bool: True if the password matches, False otherwise.
    
    Example:
        >>> hashed = get_password_hash("mypassword")
        >>> verify_password("mypassword", hashed)
        True
        >>> verify_password("wrongpassword", hashed)
        False
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Generates a salt internally and creates a secure hash of the password.
    The resulting hash can be stored in the database and verified later.
    
    Args:
        password (str): The plain text password to hash.
    
    Returns:
        str: The bcrypt hashed password as a string.
    
    Example:
        >>> hashed = get_password_hash("securepassword123")
        >>> print(hashed)  # $2b$12$...
        $2b$12$...
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token for authenticated API access.
    
    Access tokens are short-lived tokens used for API authentication.
    They contain the user's email in the "sub" claim and expire automatically.
    
    Args:
        data (dict): Dictionary containing claims to encode in the token.
                     Must include "sub" with the user's email.
        expires_delta (timedelta | None): Optional custom expiration time.
                                          If None, uses default from settings.
    
    Returns:
        str: The encoded JWT token string.
    
    Raises:
        ValueError: If data doesn't contain required "sub" claim.
    
    Example:
        >>> token = create_access_token(data={"sub": "user@example.com"})
        >>> print(token)  # eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT refresh token for session persistence.
    
    Refresh tokens are longer-lived tokens used to obtain new access tokens
    without requiring the user to log in again. They include a unique "jti"
    (JWT ID) claim for token tracking and revocation.
    
    Args:
        data (dict): Dictionary containing claims to encode in the token.
                     Must include "sub" with the user's email.
        expires_delta (timedelta | None): Optional custom expiration time.
                                          If None, uses default from settings (7 days).
    
    Returns:
        str: The encoded JWT refresh token string.
    
    Example:
        >>> token = create_refresh_token(data={"sub": "user@example.com"})
        >>> print(token)  # eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token_jti = str(uuid.uuid4())
    to_encode.update({"exp": expire, "type": "refresh", "jti": token_jti})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def is_token_revoked(db: Session, token: str) -> bool:
    """
    Check if a token has been revoked.
    
    Revoked tokens are stored in the database and checked during authentication
    to prevent use of logged-out or manually revoked tokens.
    
    Args:
        db (Session): SQLAlchemy database session.
        token (str): The JWT token string to check.
    
    Returns:
        bool: True if the token has been revoked, False otherwise.
    
    Example:
        >>> if is_token_revoked(db, token):
        ...     raise HTTPException(status_code=401, detail="Token revoked")
    """
    from app.models import RevokedToken
    revoked = db.query(RevokedToken).filter(RevokedToken.token == token).first()
    return revoked is not None


def revoke_token(db: Session, token: str, token_type: str = "access") -> None:
    """
    Revoke a token to prevent its future use.
    
    Revoked tokens are stored with their expiration time and can be checked
    during authentication. Old revoked tokens are automatically cleaned up
    by clean_expired_tokens().
    
    Args:
        db (Session): SQLAlchemy database session.
        token (str): The JWT token string to revoke.
        token_type (str): Type of token ("access" or "refresh"). Defaults to "access".
    
    Returns:
        None: This function doesn't return anything.
    
    Raises:
        JWTError: If the token cannot be decoded (invalid token format).
    
    Example:
        >>> revoke_token(db, old_access_token, "access")
    """
    from app.models import RevokedToken
    payload = jwt.decode(token, SECRET_KEY, algorithms=[settings.ALGORITHM])
    exp = payload.get("exp")
    expires_at = datetime.fromtimestamp(exp, tz=timezone.utc) if exp else datetime.now(timezone.utc) + timedelta(days=7)
    revoked_token = RevokedToken(token=token, token_type=token_type, expires_at=expires_at)
    db.add(revoked_token)
    db.commit()


def clean_expired_tokens(db: Session) -> None:
    """
    Remove expired tokens from the revoked tokens table.
    
    This function should be called periodically (e.g., on startup or via cron)
    to clean up expired tokens and prevent the table from growing indefinitely.
    
    Args:
        db (Session): SQLAlchemy database session.
    
    Returns:
        None: This function doesn't return anything.
    
    Example:
        >>> clean_expired_tokens(db)  # Removes all expired tokens
    """
    from app.models import RevokedToken
    db.query(RevokedToken).filter(RevokedToken.expires_at < datetime.now(timezone.utc)).delete()
    db.commit()


def check_user_locked(db: Session, user) -> bool:
    """
    Check if a user account is currently locked due to failed login attempts.
    
    If the user is locked and the lockout period has expired, the account
    is automatically unlocked and failed attempts are reset.
    
    Args:
        db (Session): SQLAlchemy database session.
        user (User): The user object to check.
    
    Returns:
        bool: True if the user is currently locked, False otherwise.
    
    Example:
        >>> if check_user_locked(db, user):
        ...     raise HTTPException(status_code=423, detail="Account locked")
    """
    if user.is_blocked:
        if user.locked_until and user.locked_until > datetime.now(timezone.utc):
            return True
        else:
            # Lockout expired, auto-unlock
            user.is_blocked = False
            user.failed_login_attempts = 0
            user.locked_until = None
            db.commit()
    return False


def record_failed_login(db: Session, user) -> None:
    """
    Record a failed login attempt and lock account if threshold exceeded.
    
    Increments the failed login counter and locks the account if the maximum
    number of attempts is reached. The lockout duration is configured via
    settings.LOCKOUT_DURATION_MINUTES.
    
    Args:
        db (Session): SQLAlchemy database session.
        user (User): The user object to update.
    
    Returns:
        None: This function doesn't return anything.
    
    Example:
        >>> record_failed_login(db, user)
        >>> print(user.failed_login_attempts)  # 1
    """
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
        user.is_blocked = True
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
    db.commit()


def reset_failed_login(db: Session, user) -> None:
    """
    Reset failed login counter and unlock account on successful login.
    
    Called when a user successfully authenticates to clear any failed
    login attempts and ensure the account is not locked.
    
    Args:
        db (Session): SQLAlchemy database session.
        user (User): The user object to reset.
    
    Returns:
        None: This function doesn't return anything.
    
    Example:
        >>> reset_failed_login(db, user)
        >>> print(user.failed_login_attempts)  # 0
    """
    user.failed_login_attempts = 0
    user.is_blocked = False
    user.locked_until = None
    db.commit()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> "User":
    """
    Get the current authenticated user from JWT access token.
    
    This is a FastAPI dependency that validates the access token and returns
    the corresponding user. It checks:
    - Token validity and expiration
    - Token type (must be "access")
    - Token revocation status
    - User existence
    
    Args:
        token (str): JWT access token extracted from Authorization header.
        db (Session): SQLAlchemy database session injected by FastAPI.
    
    Returns:
        User: The authenticated user object.
    
    Raises:
        HTTPException 401: If token is invalid, expired, revoked, or user not found.
        HTTPException 401: If token type is not "access" (e.g., refresh token used).
    
    Example:
        >>> @router.get("/protected")
        ... async def protected_route(current_user: User = Depends(get_current_user)):
        ...     return {"email": current_user.email}
    """
    from app.crud import get_user_by_email

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if is_token_revoked(db, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user


async def get_current_user_from_refresh(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> "User":
    """
    Get the current authenticated user from JWT refresh token.
    
    This dependency is used specifically for refresh token endpoints.
    It validates that the token is a refresh token (not access token).
    
    Args:
        token (str): JWT refresh token extracted from Authorization header.
        db (Session): SQLAlchemy database session injected by FastAPI.
    
    Returns:
        User: The authenticated user object.
    
    Raises:
        HTTPException 401: If token is invalid, expired, revoked, or user not found.
        HTTPException 401: If token type is not "refresh" (e.g., access token used).
    
    Example:
        >>> @router.post("/refresh")
        ... async def refresh_token(
        ...     user: User = Depends(get_current_user_from_refresh),
        ...     refresh_token: str
        ... ):
        ...     # Issue new tokens
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type")
        if token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if is_token_revoked(db, token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    from app.crud import get_user_by_email
    user = get_user_by_email(db, email=email)
    if user is None:
        raise credentials_exception
    return user
