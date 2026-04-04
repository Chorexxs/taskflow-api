from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_password_hash, verify_password


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user(db: Session, user_id: int, user_update: schemas.UserCreate):
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    if user_update.password:
        db_user.hashed_password = get_password_hash(user_update.password)
    if user_update.email:
        db_user.email = user_update.email
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def create_team(db: Session, team: schemas.TeamCreate, user_id: int):
    db_team = models.Team(
        name=team.name,
        slug=team.slug,
        description=team.description,
        created_by=user_id,
    )
    db.add(db_team)
    db.commit()
    db.refresh(db_team)

    member = models.TeamMember(
        team_id=db_team.id,
        user_id=user_id,
        role="admin",
    )
    db.add(member)
    db.commit()

    return db_team


def get_team_by_id(db: Session, team_id: int):
    return db.query(models.Team).filter(models.Team.id == team_id).first()


def get_team_by_slug(db: Session, slug: str):
    return db.query(models.Team).filter(models.Team.slug == slug).first()


def get_teams_by_user(db: Session, user_id: int):
    return (
        db.query(models.Team)
        .join(models.TeamMember)
        .filter(models.TeamMember.user_id == user_id)
        .all()
    )


def add_member(db: Session, team_id: int, user_id: int, role: str):
    member = models.TeamMember(
        team_id=team_id,
        user_id=user_id,
        role=role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def remove_member(db: Session, team_id: int, user_id: int):
    member = (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user_id,
        )
        .first()
    )
    if member:
        db.delete(member)
        db.commit()
    return member


def get_team_members(db: Session, team_id: int):
    return db.query(models.TeamMember).filter(models.TeamMember.team_id == team_id).all()


def get_team_member(db: Session, team_id: int, user_id: int):
    return (
        db.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.user_id == user_id,
        )
        .first()
    )


def update_member_role(db: Session, team_id: int, user_id: int, role: str):
    member = get_team_member(db, team_id, user_id)
    if member:
        member.role = role
        db.commit()
        db.refresh(member)
    return member
