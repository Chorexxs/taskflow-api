"""
TaskFlow API - Authentication Router

This module handles all authentication-related API endpoints:
- POST /register: User registration
- POST /login: User login with credentials
- POST /refresh: Token refresh for session extension
- POST /logout: User logout and token revocation

Security features:
- Rate limiting: 5/min for registration, 10/min for login
- Account lockout after 5 failed login attempts
- JWT with access and refresh tokens
- Token rotation on refresh
"""

from datetime import timedelta
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from functools import wraps

from app import crud, schemas
from app.database import get_db
from app.auth import (
    settings,
    create_access_token,
    create_refresh_token,
    verify_password,
    revoke_token,
    check_user_locked,
    record_failed_login,
    reset_failed_login,
)

router = APIRouter()

# Rate limiter instance using IP address as key
limiter = Limiter(key_func=get_remote_address)


def rate_limit_decorator(limit_str: str):
    """
    Decorator factory that applies rate limiting to routes.
    
    Automatically disables rate limiting when TESTING environment
    variable is set (for test execution).
    
    Args:
        limit_str (str): Rate limit string (e.g., "10/minute").
    
    Returns:
        Decorator function that applies the rate limit.
    
    Example:
        @rate_limit_decorator("5/minute")
        def my_endpoint():
            ...
    """
    if os.environ.get("TESTING"):
        def decorator(func):
            return func
        return decorator
    return limiter.limit(limit_str)


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
@rate_limit_decorator("5/minute")
def register(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user in the system.
    
    Creates a new user account with the provided email and password.
    The password is automatically hashed before storage.
    
    Rate limit: 5 requests per minute per IP.
    
    Args:
        request (Request): The incoming HTTP request (for logging/tracing).
        user (UserCreate): Schema containing email and password.
        db (Session): Database session (injected by FastAPI).
    
    Returns:
        UserOut: The newly created user (without password).
    
    Raises:
        HTTPException 400: If the email is already registered.
        HTTPException 429: If rate limit is exceeded.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/auth/register \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"email":"user@example.com","password":"secure123"}'
        
        Response:
        {
            "id": 1,
            "email": "user@example.com",
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z"
        }
    """
    # Check if email already exists
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create the user
    return crud.create_user(db=db, user=user)


@router.post("/login", response_model=schemas.Token)
@rate_limit_decorator("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Authenticate a user and return JWT tokens.
    
    Validates user credentials and returns access and refresh tokens.
    The endpoint supports OAuth2 password flow for compatibility.
    
    Rate limit: 10 requests per minute per IP.
    
    Args:
        request (Request): The incoming HTTP request (for rate limiting).
        form_data (OAuth2PasswordRequestForm): Form with username (email) and password.
        db (Session): Database session (injected by FastAPI).
    
    Returns:
        Token: Dictionary with access_token, refresh_token, and token_type.
    
    Raises:
        HTTPException 401: If credentials are incorrect.
        HTTPException 423: If account is locked due to failed attempts.
        HTTPException 429: If rate limit is exceeded.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/auth/login \\
        ...   -H "Content-Type: application/x-www-form-urlencoded" \\
        ...   -d "username=user@example.com&password=secure123"
        
        Response:
        {
            "access_token": "eyJhbGc...",
            "refresh_token": "eyJhbGc...",
            "token_type": "bearer"
        }
    """
    # Look up user by email (username in OAuth2 form is the email)
    user = crud.get_user_by_email(db, email=form_data.username)
    
    # Check if user exists
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if account is locked
    if check_user_locked(db, user):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed login attempts",
        )
    
    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        # Record failed attempt (may lock account)
        record_failed_login(db, user)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Successful login - reset failed attempts
    reset_failed_login(db, user)
    
    # Generate tokens
    access_token = create_access_token(data={"sub": user.email})
    refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=schemas.Token)
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    """
    Refresh access token using a valid refresh token.
    
    Validates the refresh token, revokes it, and issues new
    access and refresh tokens. This implements token rotation
    for improved security.
    
    Args:
        refresh_token (str): The refresh token string from the request body.
        db (Session): Database session (injected by FastAPI).
    
    Returns:
        Token: Dictionary with new access_token, refresh_token, and token_type.
    
    Raises:
        HTTPException 401: If refresh token is invalid or expired.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/auth/refresh \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"refresh_token":"eyJhbGc..."}'
        
        Response:
        {
            "access_token": "new_access_token...",
            "refresh_token": "new_refresh_token...",
            "token_type": "bearer"
        }
    """
    from app.auth import get_current_user_from_refresh
    
    # Validate refresh token and get user
    user = get_current_user_from_refresh(refresh_token, db)
    
    # Revoke the old refresh token (rotation)
    revoke_token(db, refresh_token, "refresh")
    
    # Generate new tokens
    new_access_token = create_access_token(data={"sub": user.email})
    new_refresh_token = create_refresh_token(data={"sub": user.email})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db), current_user: schemas.UserOut = Depends(crud.get_current_user_from_token)):
    """
    Logout the current user by revoking their access token.
    
    Extracts the access token from the Authorization header and
    adds it to the revoked tokens list. The user will need to
    login again to get a new token.
    
    Args:
        request (Request): The incoming HTTP request with Authorization header.
        db (Session): Database session (injected by FastAPI).
        current_user (UserOut): The authenticated user (injected via dependency).
    
    Returns:
        dict: Success message.
    
    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/auth/logout \\
        ...   -H "Authorization: Bearer eyJhbGc..."
        
        Response:
        {"message": "Successfully logged out"}
    """
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        try:
            # Revoke the access token
            revoke_token(db, token, "access")
        except Exception:
            # Ignore errors (token might be expired or invalid)
            pass
    
    return {"message": "Successfully logged out"}
