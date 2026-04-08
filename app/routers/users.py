"""
TaskFlow API - Users Router

This module handles user-related API endpoints:
- GET /me: Get current authenticated user
- PUT /me: Update current user profile (email, password)

All endpoints in this router require authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter()


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
def update_current_user(
    user_update: schemas.UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update the current user's profile.
    
    Allows updating email and/or password. Only provided fields
    are updated - omitted fields remain unchanged.
    
    Args:
        user_update (UserCreate): Schema with email and/or password to update.
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
    # Check if email is being changed and if it's already taken
    if user_update.email:
        existing_user = crud.get_user_by_email(db, email=user_update.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(status_code=400, detail="Email already in use")
    
    # Update the user
    updated_user = crud.update_user(db, current_user.id, user_update)
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user
