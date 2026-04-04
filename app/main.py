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
    
    engine = _test_engine if _test_engine else get_engine()
    if engine is not None:
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="TaskFlow API", description="API REST con FastAPI y JWT", lifespan=lifespan)

app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests"}
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(SecurityHeadersMiddleware)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(teams.router, prefix="/teams", tags=["teams"])
app.include_router(projects.router, prefix="/teams/{team_id_or_slug}/projects", tags=["projects"])
app.include_router(tasks.router, prefix="/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks", tags=["tasks"])
app.include_router(comments.router, prefix="/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks/{task_id_or_title}/comments", tags=["comments"])
app.include_router(attachments.router, prefix="/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks/{task_id_or_title}/attachments", tags=["attachments"])
app.include_router(notifications.router, prefix="/notifications", tags=["notifications"])


@app.get("/")
def root():
    return {"message": "TaskFlow API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
