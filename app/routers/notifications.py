"""
TaskFlow API - Notifications Router

This module handles user notification endpoints:
- GET /: List notifications for current user
- PATCH /{notification_id}/read: Mark a notification as read
- PATCH /read-all: Mark all notifications as read

Notifications are created when users are assigned to tasks or
receive comments on tasks they're working on.
"""

import asyncio
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.config import settings
from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.logging_config import get_logger
from app.rate_limit import rate_limit

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=schemas.PaginatedNotificationResponse)
def get_notifications(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    is_read: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
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
        PaginatedNotificationResponse: Page of notifications plus metadata.
    
    Example:
        >>> # Get all notifications
        >>> curl -X GET https://api.taskflow.com/api/v1/notifications/ \\
        ...   -H "Authorization: Bearer eyJhbGc..."
        
        >>> # Get only unread
        >>> curl "https://api.taskflow.com/api/v1/notifications/?is_read=false" \\
        ...   -H "Authorization: Bearer eyJhbGc..."
    """
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    return crud.get_notifications_by_user(db, current_user.id, is_read, page, page_size)


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Return the number of unread notifications for the current user."""
    return {"count": crud.count_unread_notifications(db, current_user.id)}


async def iter_notification_events(request: Request, db: Session, user_id: int, start_after: int):
    """Yield SSE frames with new notifications and periodic heartbeats.

    Extracted from the route so it can be unit-tested without an infinite HTTP
    response. The caller owns the database session and must close it.
    """
    last_id = start_after
    last_heartbeat = time.monotonic()
    while True:
        if await request.is_disconnected():
            break
        try:
            pending = (
                db.query(models.Notification)
                .filter(
                    models.Notification.user_id == user_id,
                    models.Notification.id > last_id,
                )
                .order_by(models.Notification.id)
                .limit(50)
                .populate_existing()
                .all()
            )
            for notification in pending:
                last_id = notification.id
                payload = schemas.NotificationOut.model_validate(
                    notification
                ).model_dump(mode="json")
                yield (
                    f"id: {notification.id}\n"
                    "event: notification\n"
                    f"data: {json.dumps(payload)}\n\n"
                )
            db.expire_all()
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("sse_poll_failed", error=str(exc))

        now = time.monotonic()
        if now - last_heartbeat >= settings.SSE_HEARTBEAT_SECONDS:
            yield ": heartbeat\n\n"
            last_heartbeat = now
        try:
            await asyncio.sleep(settings.SSE_POLL_SECONDS)
        except asyncio.CancelledError:  # pragma: no cover - client closed
            break


@router.get("/stream")
@rate_limit("10/minute")
async def stream_notifications(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Stream new notifications as Server-Sent Events.

    The client must send ``Authorization: Bearer`` (EventSource does not allow
    custom headers, so the frontend uses ``fetch`` with a ReadableStream).
    ``Last-Event-ID`` resumes after a reconnect; without it only notifications
    created from now on are streamed. A heartbeat comment keeps proxies from
    closing idle connections.
    """
    header_last_id = request.headers.get("Last-Event-ID", "").strip()

    if header_last_id.isdigit():
        start_after = int(header_last_id)
    else:
        row = (
            db.query(models.Notification.id)
            .filter(models.Notification.user_id == current_user.id)
            .order_by(models.Notification.id.desc())
            .first()
        )
        start_after = row[0] if row else 0

    return StreamingResponse(
        iter_notification_events(request, db, current_user.id, start_after),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
