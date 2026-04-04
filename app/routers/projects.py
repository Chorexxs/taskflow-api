from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.dependencies import get_current_team_admin, get_current_team_member

router = APIRouter()


def get_project_from_id_or_slug(db: Session, project_id_or_slug: str, team_id: int) -> models.Project:
    if project_id_or_slug.isdigit():
        project = crud.get_project_by_id(db, int(project_id_or_slug))
    else:
        project = db.query(models.Project).filter(
            models.Project.team_id == team_id,
            models.Project.name.ilike(project_id_or_slug)
        ).first()
    if not project or project.team_id != team_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/", response_model=schemas.ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    team_id_or_slug: str,
    project: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    return crud.create_project(db, project, team.id, current_user.id)


@router.get("/", response_model=list[schemas.ProjectOut])
def list_projects(
    team_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    return crud.get_projects_by_team(db, team.id)


@router.get("/{project_id_or_slug}", response_model=schemas.ProjectOut)
def get_project(
    team_id_or_slug: str,
    project_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    member: models.TeamMember = Depends(get_current_team_member),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    return get_project_from_id_or_slug(db, project_id_or_slug, team.id)


@router.patch("/{project_id_or_slug}", response_model=schemas.ProjectOut)
def update_project(
    team_id_or_slug: str,
    project_id_or_slug: str,
    project_update: schemas.ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_slug(db, project_id_or_slug, team.id)
    return crud.update_project(db, project.id, project_update)


@router.delete("/{project_id_or_slug}", status_code=status.HTTP_204_NO_CONTENT)
def archive_project(
    team_id_or_slug: str,
    project_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    from app.dependencies import get_team_from_id_or_slug
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    project = get_project_from_id_or_slug(db, project_id_or_slug, team.id)
    crud.archive_project(db, project.id)
