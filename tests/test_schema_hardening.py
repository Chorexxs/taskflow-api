"""Database invariants: enum checks, audit columns and read indexes (T-082)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app import models


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup(client: TestClient):
    assert client.post(
        "/api/v1/auth/register",
        json={"email": "schema@example.com", "password": "password123"},
    ).status_code == 201
    token = client.post(
        "/api/v1/auth/login",
        data={"username": "schema@example.com", "password": "password123"},
    ).json()["access_token"]
    assert client.post(
        "/api/v1/teams/",
        json={"name": "Schema Team", "slug": "schema-team"},
        headers=_headers(token),
    ).status_code == 201
    assert client.post(
        "/api/v1/teams/schema-team/projects/",
        json={"name": "Schema Project"},
        headers=_headers(token),
    ).status_code == 201
    task = client.post(
        "/api/v1/teams/schema-team/projects/Schema Project/tasks/",
        json={"title": "Schema Task"},
        headers=_headers(token),
    )
    assert task.status_code == 201, task.text
    return token, task.json()


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE tasks SET status = 'blocked'",
        "UPDATE tasks SET priority = 'urgent'",
        "UPDATE projects SET status = 'deleted'",
    ],
)
def test_check_constraints_reject_invalid_enums(client: TestClient, db_session, statement):
    _setup(client)

    with pytest.raises(IntegrityError):
        db_session.execute(text(statement))
        db_session.commit()
    db_session.rollback()


def test_role_check_constraint(client: TestClient, db_session):
    _setup(client)

    with pytest.raises(IntegrityError):
        db_session.execute(text("UPDATE team_members SET role = 'owner'"))
        db_session.commit()
    db_session.rollback()


def test_audit_columns_are_populated(client: TestClient, db_session):
    _setup(client)
    db_session.expire_all()
    user = db_session.query(models.User).filter_by(email="schema@example.com").one()
    assert user.last_login_at is not None

    token = client.post(
        "/api/v1/auth/login",
        data={"username": "schema@example.com", "password": "password123"},
    ).json()["access_token"]
    response = client.put(
        "/api/v1/users/me",
        headers=_headers(token),
        json={"current_password": "password123", "password": "new-password123"},
    )
    assert response.status_code == 200, response.text

    db_session.expire_all()
    user = db_session.query(models.User).filter_by(email="schema@example.com").one()
    assert user.password_changed_at is not None


def test_read_indexes_exist(client: TestClient, db_session):
    _setup(client)
    inspector = inspect(db_session.bind)

    expected = {
        "tasks": {
            "ix_tasks_project_assignee_status",
            "ix_tasks_project_due_date",
        },
        "comments": {"ix_comments_task_created"},
        "attachments": {"ix_attachments_task_created"},
        "notifications": {"ix_notifications_user_read_created"},
        "projects": {"ix_projects_team_status_created"},
        "team_members": {"ix_team_members_user_id", "ix_team_members_team_role"},
    }
    for table, names in expected.items():
        existing = {index["name"] for index in inspector.get_indexes(table)}
        assert names <= existing
