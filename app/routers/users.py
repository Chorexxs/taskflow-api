"""
TaskFlow API - Users Router

This module handles user-related API endpoints:
- GET /me: Get current authenticated user
- PUT /me: Update current user profile (email, password)

All endpoints in this router require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app import crud, schemas
from app.auth import get_current_user, verify_password
from app.database import get_db
from app.logging_config import get_logger
from app.models import User
from app.rate_limit import rate_limit

router = APIRouter()
logger = get_logger(__name__)


@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Get the currently authenticated user.
    
    Returns the profile information of the currently logged-in user.
    This endpoint is used to verify authentication and get user details.
    
    Args:
        current_user (User): The authenticated user (injected via JWT dependency).
    
    Returns:
        UserOut: User profile with id, email, is_active, and created_at.
    
    Example:
        >>> curl -X GET https://api.taskflow.com/api/v1/users/me \\
        ...   -H "Authorization: Bearer eyJhbGc..."
        
        Response:
        {
            "id": 1,
            "email": "user@example.com",
            "is_active": true,
            "created_at": "2024-01-01T00:00:00Z"
        }
    """
    return current_user


@router.put("/me", response_model=schemas.UserOut)
@rate_limit("10/minute")
def update_current_user(
    request: Request,
    user_update: schemas.UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's profile.
    
    Allows updating email and/or password. Only provided fields
    are updated - omitted fields remain unchanged.
    
    Args:
        user_update (UserUpdate): Schema with email and/or password to update.
        current_user (User): The authenticated user (injected via JWT dependency).
        db (Session): Database session (injected by FastAPI).
    
    Returns:
        UserOut: Updated user profile.
    
    Raises:
        HTTPException 400: If the new email is already in use by another user.
        HTTPException 404: If user not found (should not happen for authenticated users).
    
    Example:
        >>> curl -X PUT https://api.taskflow.com/api/v1/users/me \\
        ...   -H "Authorization: Bearer eyJhbGc..." \\
        ...   -H "Content-Type: application/json" \\
        ...   -d '{"email":"newemail@example.com"}'
    """
    changing_credentials = user_update.email is not None or user_update.password is not None

    if changing_credentials:
        # Never allow an email/password change with a stolen access token.
        if not user_update.current_password:
            raise HTTPException(
                status_code=400,
                detail="current_password is required to change credentials",
            )
        if not verify_password(user_update.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect",
            )

    # Check if email is being changed and if it's already taken
    if user_update.email:
        existing_user = crud.get_user_by_email(db, email=user_update.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already in use")
    
    # Update the user
    updated_user = crud.update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    if changing_credentials:
        logger.info(
            "auth_credentials_updated",
            user_id=updated_user.id,
            password_changed=user_update.password is not None,
            email_changed=user_update.email is not None,
        )
    return updated_user


def _preferences_payload(user: User) -> dict:
    return {
        "muted_types": [
            value
            for value in (user.muted_notification_types or "").split(",")
            if value
        ]
    }


@router.get(
    "/me/notification-preferences",
    response_model=schemas.NotificationPreferences,
)
def get_notification_preferences(current_user: User = Depends(get_current_user)):
    """Return the notification types the current user has muted."""
    return _preferences_payload(current_user)


@router.put(
    "/me/notification-preferences",
    response_model=schemas.NotificationPreferences,
)
def update_notification_preferences(
    preferences: schemas.NotificationPreferences,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mute or unmute notification types for the current user."""
    current_user.muted_notification_types = ",".join(  # type: ignore[assignment]
        sorted({value.value for value in preferences.muted_types})
    )
    db.commit()
    db.refresh(current_user)
    logger.info(
        "notification_preferences_updated",
        user_id=current_user.id,
        muted_count=len(preferences.muted_types),
    )
    return _preferences_payload(current_user)
