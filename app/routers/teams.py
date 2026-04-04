from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, models, schemas
from app.auth import get_current_user
from app.dependencies import get_current_team_admin, get_current_team_member

router = APIRouter()


def get_team_from_id_or_slug(db: Session, team_id_or_slug: str) -> models.Team:
    if team_id_or_slug.isdigit():
        team = crud.get_team_by_id(db, int(team_id_or_slug))
    else:
        team = crud.get_team_by_slug(db, team_id_or_slug)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.post("/", response_model=schemas.TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    team: schemas.TeamCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    existing_team = crud.get_team_by_slug(db, team.slug)
    if existing_team:
        raise HTTPException(status_code=400, detail="Team slug already exists")
    return crud.create_team(db, team, current_user.id)


@router.get("/", response_model=list[schemas.TeamOut])
def get_teams(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return crud.get_teams_by_user(db, current_user.id)


@router.get("/{team_id_or_slug}", response_model=schemas.TeamOut)
def get_team(
    team_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    get_current_team_member(team_id_or_slug, db, current_user)
    return team


@router.post("/{team_id_or_slug}/members", response_model=schemas.TeamMemberOut, status_code=status.HTTP_201_CREATED)
def invite_member(
    team_id_or_slug: str,
    member_data: schemas.TeamMemberAdd,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    team = get_team_from_id_or_slug(db, team_id_or_slug)

    user = crud.get_user_by_email(db, member_data.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_member = crud.get_team_member(db, team.id, user.id)
    if existing_member:
        raise HTTPException(status_code=400, detail="User is already a member")

    return crud.add_member(db, team.id, user.id, member_data.role.value)


@router.get("/{team_id_or_slug}/members", response_model=list[schemas.TeamMemberOut])
def list_members(
    team_id_or_slug: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    get_current_team_member(team_id_or_slug, db, current_user)
    return crud.get_team_members(db, team.id)


@router.delete("/{team_id_or_slug}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    team_id_or_slug: str,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    member = crud.get_team_member(db, team.id, user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.user_id != current_user.id and member.role != "admin":
        get_current_team_admin(team_id_or_slug, db, current_user)

    crud.remove_member(db, team.id, user_id)


@router.patch("/{team_id_or_slug}/members/{user_id}", response_model=schemas.TeamMemberOut)
def update_member_role(
    team_id_or_slug: str,
    user_id: int,
    role_update: schemas.TeamMemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    admin: models.TeamMember = Depends(get_current_team_admin),
):
    team = get_team_from_id_or_slug(db, team_id_or_slug)
    member = crud.get_team_member(db, team.id, user_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if member.user_id == admin.user_id and role_update.role.value == "member":
        raise HTTPException(status_code=400, detail="Cannot change own admin role")

    return crud.update_member_role(db, team.id, user_id, role_update.role.value)
