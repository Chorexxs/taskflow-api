import os
import uvicorn
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.database import Base
from app.routers import auth, users, teams, projects, tasks, comments, attachments

_test_engine = None


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

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(teams.router, prefix="/teams", tags=["teams"])
app.include_router(projects.router, prefix="/teams/{team_id_or_slug}/projects", tags=["projects"])
app.include_router(tasks.router, prefix="/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks", tags=["tasks"])
app.include_router(comments.router, prefix="/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks/{task_id_or_title}/comments", tags=["comments"])
app.include_router(attachments.router, prefix="/teams/{team_id_or_slug}/projects/{project_id_or_name}/tasks/{task_id_or_title}/attachments", tags=["attachments"])


@app.get("/")
def root():
    return {"message": "TaskFlow API"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
