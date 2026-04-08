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
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from app.database import Base
from app.routers import auth, users, teams, projects, tasks, comments, attachments, notifications
from app.logging_config import configure_logging, get_logger

# Configure structured logging at module import
configure_logging()
logger = get_logger(__name__)

# Global test engine for pytest fixture injection
_test_engine = None


# Rate limiter instance using IP address as key
# Used to protect endpoints like login from brute force attacks
limiter = Limiter(key_func=get_remote_address)


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
        return response


def set_test_engine(engine):
    """
    Set a test database engine for pytest fixtures.
    
    This function allows test fixtures to inject a test database engine
    instead of using the production database.
    
    Args:
        engine (Engine): SQLAlchemy engine instance for testing.
    
    Returns:
        None: This function doesn't return anything.
    
    Example:
        >>> from sqlalchemy import create_engine
        >>> engine = create_engine("sqlite:///:memory:")
        >>> set_test_engine(engine)
    """
    global _test_engine
    global _test_app
    _test_engine = engine


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
    from app.database import get_engine
    
    # Initialize Sentry for error tracking if configured
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        import sentry_sdk
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                sentry_sdk.fastapi.FastApiIntegration(),
            ],
            environment=os.environ.get("ENVIRONMENT", "production"),
        )
        logger.info("sentry_initialized")
    
    # Create tables or use test engine
    engine = _test_engine if _test_engine else get_engine()
    if engine is not None:
        Base.metadata.create_all(bind=engine)
    
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


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """
    Handle rate limit exceeded errors.
    
    Returns a 429 Too Many Requests response when the user exceeds
    the rate limit for an endpoint.
    
    Args:
        request (Request): The incoming HTTP request that triggered the limit.
        exc (RateLimitExceeded): The exception containing limit details.
    
    Returns:
        JSONResponse: 429 status with error message.
    
    Example:
        When a user makes more than 10 login attempts per minute:
        HTTP/1.1 429 Too Many Requests
        {"detail": "Too many requests"}
    """
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"}
    )


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
        return JSONResponse(
            status_code=400,
            content={"error": exc.code, "detail": exc.message}
        )
    logger.error("unhandled_exception", error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# CORS middleware configuration
# Allows cross-origin requests from any origin for development
# In production, restrict allow_origins to specific domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom logging middleware for request/response logging
from app.middleware import LoggingMiddleware
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
        from app.database import get_engine
        from sqlalchemy import text
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
    except Exception as e:
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


# Entry point for running the application directly
# Reads PORT from environment variable (default: 8000)
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
