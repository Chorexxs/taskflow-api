"""
TaskFlow API - Notifications Router

This module handles user notification endpoints:
- GET /: List notifications for current user
- PATCH /{notification_id}/read: Mark a notification as read
- PATCH /read-all: Mark all notifications as read

Notifications are created when users are assigned to tasks or
receive comments on tasks they're working on.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user

router = APIRouter()


@router.get("/", response_model=list[schemas.NotificationOut])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    is_read: Optional[bool] = None,
):
    """
    Get notifications for the current user.
    
    Returns all notifications for the authenticated user, optionally
    filtered by read status. Notifications are ordered by creation
    date (newest first).
    
    Args:
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
        is_read (bool | None): Filter by read status. None returns all.
    
    Returns:
        list[NotificationOut]: List of notifications.
    
    Example:
        >>> # Get all notifications
        >>> curl -X GET https://api.taskflow.com/api/v1/notifications/ \\
        ...   -H "Authorization: Bearer eyJhbGc..."
        
        >>> # Get only unread
        >>> curl "https://api.taskflow.com/api/v1/notifications/?is_read=false" \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    return crud.get_notifications_by_user(db, current_user.id, is_read)


@router.patch("/{notification_id}/read", response_model=schemas.NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Mark a single notification as read.
    
    Only the notification owner can mark it as read.
    
    Args:
        notification_id (int): ID of the notification to mark as read.
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
    
    Returns:
        NotificationOut: The updated notification.
    
    Raises:
        HTTPException 404: If notification not found.
        HTTPException 403: If user doesn't own the notification.
    
    Example:
        >>> curl -X PATCH https://api.taskflow.com/api/v1/notifications/1/read \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    notification = crud.get_notification_by_id(db, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud.mark_notification_read(db, notification_id)


@router.patch("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Mark all notifications as read.
    
    Bulk operation to mark all unread notifications as read
    for the current user.
    
    Args:
        db (Session): Database session (injected by FastAPI).
        current_user (User): The authenticated user.
    
    Returns:
        None: Returns 204 No Content on success.
    
    Example:
        >>> curl -X PATCH https://api.taskflow.com/api/v1/notifications/read-all \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    crud.mark_all_notifications_read(db, current_user.id)
