"""
TaskFlow API - Main Application Module

This is the main entry point for the FastAPI application. It configures:
- FastAPI app with lifespan events
- Middleware (CORS, security headers, logging, rate limiting)
- Router registration
- Exception handlers
- Health check endpoint
- Root endpoint

The application uses:
- PostgreSQL as the database
- Redis for caching (optional)
- Sentry for error tracking (optional)
"""

import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.logging_config import configure_logging, get_logger, request_id_context
from app.middleware import LoggingMiddleware
from app.rate_limit import limiter
from app.routers import attachments, auth, comments, notifications, projects, tasks, teams, users

# Configure structured logging at module import
configure_logging()
logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.
    
    Adds the following headers:
    - X-Content-Type-Options: nosniff - Prevents MIME type sniffing
    - X-Frame-Options: DENY - Prevents clickjacking attacks
    - Strict-Transport-Security: Forces HTTPS connections
    - X-XSS-Protection: Enables XSS filter in browsers
    
    Args:
        request (Request): The incoming HTTP request.
        call_next: The next middleware/handler in the chain.
    
    Returns:
        Response: The HTTP response with security headers added.
    """
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        # The API only returns JSON, but /docs uses Swagger UI assets from a CDN.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://fastapi.tiangolo.com; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application startup and shutdown events.
    
    This lifespan context manager handles:
    1. Startup:
       - Initialize Sentry if SENTRY_DSN is configured
       - Create database tables if engine is available
       - Log application start
    2. Shutdown:
       - Log application shutdown
    
    Args:
        app (FastAPI): The FastAPI application instance.
    
    Yields:
        None: Control flows to the application during the "running" phase.
    
    Example:
        The lifespan is automatically invoked by FastAPI on startup/shutdown.
    """
    # Initialize Sentry for error tracking if configured. Observability is
    # optional: a misconfigured Sentry instance must not prevent the API from
    # serving traffic.
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                integrations=[FastApiIntegration()],
                environment=settings.ENVIRONMENT,
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            )
            logger.info("sentry_initialized")
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("sentry_initialization_failed", error=str(exc))

    # Schema creation is owned by Alembic. Tests create their own schema in
    # tests/conftest.py, so the application must never call create_all.
    #
    # Housekeeping is best-effort and must never prevent startup. Tests use
    # their own in-memory database and skip this production cleanup.
    if not os.environ.get("TESTING"):
        try:
            from app.auth import clean_expired_tokens
            from app.database import get_db_context

            with get_db_context() as db:
                clean_expired_tokens(db)
            logger.info("expired_tokens_cleaned")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("token_cleanup_failed", error=str(exc))

    logger.info("application_started")
    yield
    logger.info("application_shutdown")


# Create FastAPI application with metadata and lifespan
app = FastAPI(
    title="TaskFlow API",
    description="API REST con FastAPI y JWT",
    lifespan=lifespan
)

# Attach rate limiter to app state for access in routes
app.state.limiter = limiter


_STATUS_ERROR_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    413: "FILE_TOO_LARGE",
    415: "UNSUPPORTED_MEDIA_TYPE",
    422: "VALIDATION_ERROR",
    423: "ACCOUNT_LOCKED",
    429: "RATE_LIMITED",
    500: "INTERNAL_ERROR",
}


def _error_response(
    status_code: int,
    message: str,
    *,
    code: str | None = None,
    details=None,
    headers: dict | None = None,
) -> JSONResponse:
    """Build the consistent error envelope while keeping `detail` for legacy clients."""
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": message,
            "error": {
                "code": code or _STATUS_ERROR_CODES.get(status_code, "HTTP_ERROR"),
                "message": message,
                "details": details,
                "request_id": request_id_context.get(),
            },
        },
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Return HTTP errors with a stable machine-readable envelope."""
    return _error_response(
        exc.status_code,
        str(exc.detail),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return Pydantic validation errors in the same envelope."""
    return _error_response(
        422,
        "Validation error",
        details=jsonable_encoder(exc.errors()),
    )


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors with a consistent envelope.

    The response includes ``Retry-After`` and the ``X-RateLimit-*`` headers so
    clients can back off instead of retrying immediately.
    """
    response = _error_response(429, "Too many requests")
    try:
        response = request.app.state.limiter._inject_headers(
            response, request.state.view_rate_limit
        )
    except Exception:  # pragma: no cover - defensive
        if exc.limit is not None:
            response.headers.setdefault("Retry-After", str(exc.limit.get_expiry()))
    return response


@app.exception_handler(Exception)
async def domain_exception_handler(request: Request, exc: Exception):
    """
    Handle unhandled exceptions in the application.
    
    Catches all unhandled exceptions and:
    - If it's a DomainException, returns a 400 with error details
    - Otherwise, logs the error and returns a generic 500 response
    
    Args:
        request (Request): The incoming HTTP request that caused the error.
        exc (Exception): The unhandled exception.
    
    Returns:
        JSONResponse: 400 for domain errors, 500 for other errors.
    
    Example:
        >>> try:
        ...     something()
        ... except Exception as e:
        ...     return domain_exception_handler(request, e)
    """
    from app.exceptions import DomainException
    if isinstance(exc, DomainException):
        return _error_response(400, exc.message, code=exc.code)

    logger.error("unhandled_exception", error=str(exc), exc_info=True)
    return _error_response(500, "Internal server error")


# CORS middleware configuration.
# Origins come from CORS_ORIGINS (comma-separated). Development falls back to
# localhost; production must configure an explicit allowlist.
cors_origins = settings.effective_cors_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Requested-With"],
    expose_headers=["X-Request-ID"],
)

# Custom logging middleware for request/response logging
app.add_middleware(LoggingMiddleware)

# Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)


# Register all route routers with their prefixes
# Each router handles a specific resource type

# Authentication endpoints: /api/v1/auth/*
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# User endpoints: /api/v1/users/*
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])

# Team endpoints: /api/v1/teams/*
app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])

# Project endpoints: /api/v1/teams/{team_id}/projects/*
app.include_router(projects.router, prefix="/api/v1/teams/{team_id_or_slug}/projects", tags=["projects"])

# Task endpoints: /api/v1/teams/{team_id}/projects/{project_id}/tasks/*
app.include_router(tasks.router, prefix="/api/v1/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks", tags=["tasks"])

# Comment endpoints: /api/v1/teams/{team_id}/projects/{project_id}/tasks/{task_id}/comments/*
app.include_router(comments.router, prefix="/api/v1/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks/{task_id_or_title}/comments", tags=["comments"])

# Attachment endpoints: /api/v1/teams/{team_id}/projects/{project_id}/tasks/{task_id}/attachments/*
app.include_router(attachments.router, prefix="/api/v1/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks/{task_id_or_title}/attachments", tags=["attachments"])

# Notification endpoints: /api/v1/notifications/*
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])


@app.get("/")
def root():
    """
    Root endpoint returning API information.
    
    This is the base endpoint that provides a simple welcome message.
    Used for basic connectivity testing.
    
    Returns:
        dict: Dictionary with a welcome message.
    
    Example:
        >>> curl https://api.taskflow.com/
        {"message": "TaskFlow API"}
    """
    return {"message": "TaskFlow API"}


@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Checks the status of:
    - Database connection (PostgreSQL)
    - Redis connection (if REDIS_URL is configured)
    - Available disk space
    
    Returns:
        dict: Status of all system components.
    
    Raises:
        JSONResponse: Returns 503 if database is not connected.
    
    Example:
        >>> curl https://api.taskflow.com/health
        {
            "status": "healthy",
            "database": "connected",
            "redis": "connected",
            "disk": "1060GB free"
        }
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "disk": "unknown",
    }
    
    # Check database connection
    try:
        from sqlalchemy import text

        from app.database import get_engine
        engine = get_engine()
        if engine:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis connection (optional)
    try:
        import redis
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        health_status["redis"] = "connected"
    except Exception:
        health_status["redis"] = "not_available"
    
    # Check disk space
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        health_status["disk"] = f"{free // (2**30)}GB free"
    except Exception:
        health_status["disk"] = "unknown"
    
    # Return 503 if degraded
    if health_status["status"] == "degraded":
        return JSONResponse(status_code=503, content=health_status)
    
    return health_status


@app.get("/health/live")
def health_live():
    """Liveness probe: the process is running."""
    return {"status": "alive"}


@app.get("/health/ready")
def health_ready():
    """Readiness probe: the API can serve traffic (database reachable)."""
    from sqlalchemy import text

    from app.database import get_engine

    try:
        engine = get_engine()
        if engine is None:
            raise RuntimeError("database is not configured")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "unavailable"},
        )

    return {"status": "ready", "database": "connected"}


# Entry point for running the application directly
# Reads PORT from environment variable (default: 8000)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
