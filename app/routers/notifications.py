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
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.auth import get_current_user, get_stream_user_id
from app.config import settings
from app.database import get_db, get_session_local
from app.events import NotificationEventBus, notification_bus, sse_limiter
from app.logging_config import get_logger
from app.rate_limit import rate_limit

router = APIRouter()
logger = get_logger(__name__)


def _session_factory():
    """Return a factory for short-lived SSE database sessions."""
    factory = get_session_local()
    if factory is None:  # pragma: no cover - misconfigured deployment
        raise RuntimeError("DATABASE_URL is not configured")
    return factory


def _latest_notification_id(user_id: int, session_factory) -> int:
    with session_factory() as db:
        row = (
            db.query(models.Notification.id)
            .filter(models.Notification.user_id == user_id)
            .order_by(models.Notification.id.desc())
            .first()
        )
    return int(row[0]) if row else 0


def _pending_notifications(user_id: int, last_id: int, session_factory) -> list[dict]:
    with session_factory() as db:
        rows = (
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
        return [
            schemas.NotificationOut.model_validate(notification).model_dump(mode="json")
            for notification in rows
        ]


def _sse_frame(payload: dict) -> str:
    return (
        f"id: {payload['id']}\nevent: notification\n"
        f"data: {json.dumps(payload, separators=(',', ':'))}\n\n"
    )


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


async def iter_notification_events(
    request: Request,
    user_id: int,
    start_after: int,
    *,
    bus: NotificationEventBus | None = None,
    session_factory=None,
):
    """Yield SSE frames from the event bus with periodic DB reconciliation.

    Events arrive through the bus (Redis pub/sub or in-process). Every
    ``SSE_FALLBACK_POLL_SECONDS`` the generator also queries the database, so a
    missed publish (Redis down, reconnect, dropped queue) is recovered without
    keeping a database session open for the whole stream.
    """
    bus = bus or notification_bus
    session_factory = session_factory or _session_factory()
    last_id: int = start_after
    last_heartbeat = time.monotonic()
    last_poll = 0.0
    fallback_seconds = max(settings.SSE_FALLBACK_POLL_SECONDS, 0.05)
    heartbeat_seconds = max(settings.SSE_HEARTBEAT_SECONDS, 0.01)

    async with bus.subscription(user_id) as queue:
        while True:
            if await request.is_disconnected():
                break

            now = time.monotonic()
            if now >= last_poll + fallback_seconds:
                try:
                    pending = await asyncio.to_thread(
                        _pending_notifications, user_id, last_id, session_factory
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning("sse_poll_failed", error=str(exc))
                    pending = []
                for payload in pending:
                    notification_id = int(payload["id"])
                    if notification_id <= last_id:
                        continue
                    last_id = notification_id
                    yield _sse_frame(payload)
                last_poll = time.monotonic()

            now = time.monotonic()
            timeout = max(
                0.01,
                min(
                    last_heartbeat + heartbeat_seconds,
                    last_poll + fallback_seconds,
                )
                - now,
            )
            event = await bus.wait_for_event(queue, timeout)
            if event is not None:
                try:
                    notification_id = int(event["id"])
                except (KeyError, TypeError, ValueError):
                    continue
                if notification_id > last_id:
                    last_id = notification_id
                    yield _sse_frame(event)

            now = time.monotonic()
            if now - last_heartbeat >= heartbeat_seconds:
                yield ": heartbeat\n\n"
                last_heartbeat = now


@router.get("/stream")
@rate_limit("10/minute")
async def stream_notifications(
    request: Request,
    response: Response,
    user_id: int = Depends(get_stream_user_id),
):
    """Stream new notifications as Server-Sent Events.

    The client must send ``Authorization: Bearer`` (EventSource does not allow
    custom headers, so the frontend uses ``fetch`` with a ReadableStream).
    ``Last-Event-ID`` resumes after a reconnect; without it only notifications
    created from now on are streamed.

    Events are delivered through Redis pub/sub when available, with an
    in-process fallback and a periodic database reconciliation. Concurrent
    streams are capped by ``SSE_MAX_CONNECTIONS`` and
    ``SSE_MAX_CONNECTIONS_PER_USER``; over the limit returns 503 + Retry-After.
    """
    header_last_id = request.headers.get("Last-Event-ID", "").strip()
    session_factory = _session_factory()

    if header_last_id.isdigit():
        start_after = int(header_last_id)
    else:
        start_after = await asyncio.to_thread(_latest_notification_id, user_id, session_factory)

    if not sse_limiter.acquire(user_id):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Too many concurrent notification streams",
            headers={"Retry-After": "5"},
        )

    async def guarded_events():
        try:
            async for frame in iter_notification_events(
                request,
                user_id,
                start_after,
                session_factory=session_factory,
            ):
                yield frame
        finally:
            sse_limiter.release(user_id)

    return StreamingResponse(
        guarded_events(),
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
