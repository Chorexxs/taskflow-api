"""T-119: team search must not query once per task assignee (CA-2-05)."""

from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from app import crud, models, schemas
from app.auth import get_password_hash


def _seed_search(db, prefix: str, tasks: int):
    owner = models.User(
        email=f"{prefix}-owner@example.com",
        hashed_password=get_password_hash("password123"),
        is_active=True,
        email_verified=True,
    )
    db.add(owner)
    db.commit()
    db.refresh(owner)

    team = models.Team(name="Search Team", slug=f"{prefix}-team", created_by=owner.id)
    db.add(team)
    db.commit()
    db.refresh(team)
    db.add(models.TeamMember(team_id=team.id, user_id=owner.id, role="admin"))

    project = models.Project(
        name="Search Project",
        slug=f"{prefix}-project",
        team_id=team.id,
        created_by=owner.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    for index in range(tasks):
        assignee = models.User(
            email=f"{prefix}-assignee{index}@example.com",
            hashed_password=get_password_hash("password123"),
            is_active=True,
            email_verified=True,
        )
        db.add(assignee)
        db.commit()
        db.refresh(assignee)
        db.add(
            models.Task(
                project_id=project.id,
                title=f"Searchable task {index}",
                status="todo",
                priority="medium",
                created_by=owner.id,
                assigned_to=assignee.id,
                position=float(index),
            )
        )
    db.commit()
    return team.id


def test_search_serializes_without_extra_queries(db_session):
    team_id = _seed_search(db_session, "search-budget", 3)

    # A fresh session emulates the request-scoped session: the seeded users are
    # not in its identity map, so a missing joinedload shows up as extra SELECTs.
    request_session = sessionmaker(bind=db_session.get_bind())()
    try:
        result = crud.search_in_team(request_session, team_id, "Searchable")
        tasks = result["tasks"]["items"]
        assert len(tasks) == 3

        selects: list[str] = []

        def record(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                selects.append(statement)

        engine = request_session.get_bind()
        event.listen(engine, "before_cursor_execute", record)
        try:
            payload = [schemas.TaskOut.model_validate(task) for task in tasks]
        finally:
            event.remove(engine, "before_cursor_execute", record)

        assert len(payload) == 3
        assert selects == [], f"serialization issued {len(selects)} extra SELECTs"
    finally:
        request_session.close()
