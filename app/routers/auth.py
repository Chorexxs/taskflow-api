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

import jwt
from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import (
    SECRET_KEY,
    check_user_locked,
    create_access_token,
    create_refresh_token,
    get_revoked_token,
    record_failed_login,
    reset_failed_login,
    revoke_token,
    settings,
    verify_password,
)
from app.database import get_db
from app.logging_config import get_logger
from app.rate_limit import rate_limit

router = APIRouter()
logger = get_logger(__name__)


def _user_id_from_token(db: Session, token: str | None) -> int | None:
    """Return the user id encoded in a token, without logging or trusting PII.

    Expiration is ignored on purpose: logout must audit expired tokens too.
    The decoded subject is only used to resolve the numeric user id.
    """
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": False},
        )
    except PyJWTError:
        return None
    email = payload.get("sub")
    if not email:
        return None
    user = crud.get_user_by_email(db, email=email)
    return user.id if user else None


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
@rate_limit("5/minute")
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
    created_user = crud.create_user(db=db, user=user)
    logger.info("auth_register_succeeded", user_id=created_user.id)
    return created_user


@router.post("/login", response_model=schemas.Token)
@rate_limit("10/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
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

    # Check if user exists. The attempted email is never logged.
    if not user:
        logger.warning("auth_login_failed", user_id=None, reason="unknown_user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if account is locked
    if check_user_locked(db, user):
        logger.warning("auth_login_failed", user_id=user.id, reason="account_locked")
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account temporarily locked due to too many failed login attempts",
        )

    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        # Record failed attempt (may lock account)
        was_blocked = user.is_blocked
        record_failed_login(db, user)
        logger.warning("auth_login_failed", user_id=user.id, reason="bad_password")
        if not was_blocked and user.is_blocked:
            logger.warning(
                "auth_account_locked",
                user_id=user.id,
                lockout_minutes=settings.LOCKOUT_DURATION_MINUTES,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Successful login - reset failed attempts
    reset_failed_login(db, user)
    logger.info("auth_login_succeeded", user_id=user.id)

    # Generate tokens. `ver` lets a password change invalidate every session.
    token_data = {"sub": user.email, "ver": user.token_version or 0}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)

    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/refresh", response_model=schemas.Token)
@rate_limit("30/minute")
def refresh(
    request: Request,
    payload: schemas.RefreshTokenRequest | None = Body(default=None),
    db: Session = Depends(get_db),
):
    """
    Refresh access token using a valid refresh token.

    The refresh token must be sent in the JSON body:
    ``{"refresh_token": "..."}``. It is never accepted in the query string
    because tokens in URLs leak through logs, proxies and browser history.

    The old refresh token is revoked and a new pair is issued (rotation).

    Raises:
        HTTPException 401: If the refresh token is invalid, expired or revoked.
        HTTPException 422: If no refresh token is provided.
    """
    from app.auth import get_current_user_from_refresh

    token = payload.refresh_token if payload else None
    if not token:
        logger.warning("auth_refresh_failed", user_id=None, reason="missing_token")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="refresh_token is required",
        )

    # Refresh-token reuse: a rotated or logged-out refresh token must never
    # work again. Treat any replay as a compromised session and revoke every
    # token issued for the user (the family) by bumping token_version.
    revoked = get_revoked_token(db, token)
    if revoked is not None and revoked.token_type == "refresh":
        user_id = _user_id_from_token(db, token)
        user = crud.get_user_by_id(db, user_id) if user_id else None
        if user is not None:
            user.token_version = (user.token_version or 0) + 1
            db.commit()
        logger.warning(
            "auth_refresh_reuse_detected",
            user_id=user_id,
            sessions_revoked=True,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token reuse detected; all sessions were revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate refresh token and get user
    try:
        user = get_current_user_from_refresh(token, db)
    except HTTPException:
        logger.warning("auth_refresh_failed", user_id=None, reason="invalid_token")
        raise

    # Revoke the old refresh token (rotation)
    revoke_token(db, token, "refresh")
    logger.info("auth_refresh_succeeded", user_id=user.id)

    # Generate new tokens with the current token version.
    token_data = {"sub": user.email, "ver": user.token_version or 0}
    new_access_token = create_access_token(data=token_data)
    new_refresh_token = create_refresh_token(data=token_data)

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
@rate_limit("60/minute")
def logout(
    request: Request,
    payload: schemas.LogoutRequest | None = Body(default=None),
    db: Session = Depends(get_db),
):
    """
    Logout the current user by revoking both tokens.

    The access token comes from the ``Authorization`` header and the refresh
    token from the JSON body. Logout does not depend on an active session, so
    repeated calls are idempotent and an expired access token does not block
    revoking the refresh token.

    Example:
        >>> curl -X POST https://api.taskflow.com/api/v1/auth/logout \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"refresh_token":"eyJhbGc..."}'
    """
    auth_header = request.headers.get("Authorization", "")
    access_token = auth_header[7:] if auth_header.startswith("Bearer ") else None
    refresh_token = payload.refresh_token if payload else None

    if not access_token and not refresh_token:
        logger.warning("auth_logout_failed", user_id=None, reason="missing_tokens")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="An access or refresh token is required",
        )

    user_id = _user_id_from_token(db, access_token) or _user_id_from_token(db, refresh_token)
    access_revoked = False
    if access_token:
        try:
            revoke_token(db, access_token, "access")
            access_revoked = True
        except Exception:
            # Expired/malformed access token: still allow refresh revocation.
            access_revoked = False

    refresh_revoked = False
    if refresh_token:
        try:
            revoke_token(db, refresh_token, "refresh")
            refresh_revoked = True
        except Exception:
            # Invalid/expired refresh tokens must not break logout.
            refresh_revoked = False

    if not access_revoked and not refresh_revoked:
        logger.warning("auth_logout_failed", user_id=user_id, reason="no_valid_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No valid token to revoke",
        )

    logger.info(
        "auth_logout_succeeded",
        user_id=user_id,
        access_revoked=access_revoked,
        refresh_revoked=refresh_revoked,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
