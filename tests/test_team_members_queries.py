"""T-117: the members page must not query once per member (CA-1-01)."""

from sqlalchemy import event

from app import crud, models, schemas
from app.auth import get_password_hash


def _seed_team(db, prefix: str, extra_members: int):
    owner = models.User(
        email=f"{prefix}-owner@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        email_verified=True,
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    team = models.Team(name="Query Team", slug=f"{prefix}-team", created_by=owner.id)
    db.add(team)
    db.commit()
    db.refresh(team)

    db.add(models.TeamMember(team_id=team.id, user_id=owner.id, role="admin"))
    for index in range(extra_members):
        member = models.User(
            email=f"{prefix}-{index}@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            email_verified=True,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        db.add(models.TeamMember(team_id=team.id, user_id=member.id, role="member"))
    db.commit()
    return team


def test_members_page_serializes_without_extra_queries(db_session):
    team = _seed_team(db_session, "no-n-plus-one", 4)

    items, total, _ = crud.get_team_members_paginated(db_session, team.id, 1, 20)
    assert total == 5
    assert len(items) == 5

    selects: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            selects.append(statement)

    engine = db_session.get_bind()
    event.listen(engine, "before_cursor_execute", record)
    try:
        payload = [schemas.TeamMemberOut.model_validate(item) for item in items]
    finally:
        event.remove(engine, "before_cursor_execute", record)

    assert len(payload) == 5
    assert payload[0].user.email.endswith("-owner@example.com")
    assert selects == [], f"serialization issued {len(selects)} extra SELECTs"
