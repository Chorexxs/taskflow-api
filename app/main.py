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

configure_logging()
logger = get_logger(__name__)

_test_engine = None

limiter = Limiter(key_func=get_remote_address)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response


def set_test_engine(engine):
    global _test_engine
    global _test_app
    _test_engine = engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.database import get_engine
    
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
    
    engine = _test_engine if _test_engine else get_engine()
    if engine is not None:
        Base.metadata.create_all(bind=engine)
    
    logger.info("application_started")
    yield
    logger.info("application_shutdown")


app = FastAPI(title="TaskFlow API", description="API REST con FastAPI y JWT", lifespan=lifespan)

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"}
    )


@app.exception_handler(Exception)
async def domain_exception_handler(request: Request, exc: Exception):
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.middleware import LoggingMiddleware
app.add_middleware(LoggingMiddleware)

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(teams.router, prefix="/api/v1/teams", tags=["teams"])
app.include_router(projects.router, prefix="/api/v1/teams/{team_id_or_slug}/projects", tags=["projects"])
app.include_router(tasks.router, prefix="/api/v1/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks", tags=["tasks"])
app.include_router(comments.router, prefix="/api/v1/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks/{task_id_or_title}/comments", tags=["comments"])
app.include_router(attachments.router, prefix="/api/v1/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks/{task_id_or_title}/attachments", tags=["attachments"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])


@app.get("/")
def root():
    return {"message": "TaskFlow API"}


@app.get("/health")
def health_check():
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "disk": "unknown",
    }
    
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
    
    try:
        import redis
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = "not_available"
    
    try:
        import shutil
        total, used, free = shutil.disk_usage("/")
        health_status["disk"] = f"{free // (2**30)}GB free"
    except Exception:
        health_status["disk"] = "unknown"
    
    if health_status["status"] == "degraded":
        return JSONResponse(status_code=503, content=health_status)
    
    return health_status


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
