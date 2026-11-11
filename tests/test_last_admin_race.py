"""Last-admin invariant and the race that made it unsafe (T-101)."""

import threading

import pytest
from sqlalchemy.orm import sessionmaker

from app import crud, models


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client, email: str) -> dict:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "password123"},
        ).status_code
        == 201
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_last_admin_checks_run_under_the_team_lock(client, monkeypatch):
    owner = _register_and_login(client, "lock-owner@example.com")
    team = client.post(
        "/api/v1/teams/",
        json={"name": "Lock Team", "slug": "lock-team"},
        headers=_headers(owner["access_token"]),
    )
    assert team.status_code == 201, team.text
    team_id = team.json()["id"]
    owner_id = client.get("/api/v1/users/me", headers=_headers(owner["access_token"])).json()["id"]

    calls: list[int] = []
    original = crud.lock_team_for_membership_change

    def spy(db, locked_team_id):
        calls.append(locked_team_id)
        return original(db, locked_team_id)

    monkeypatch.setattr(crud, "lock_team_for_membership_change", spy)

    response = client.delete(
        f"/api/v1/teams/lock-team/members/{owner_id}",
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 409
    assert calls == [team_id]


def test_expulsions_keep_one_admin(client, db_session):
    owner = _register_and_login(client, "race-owner@example.com")
    other = _register_and_login(client, "race-admin@example.com")
    team = client.post(
        "/api/v1/teams/",
        json={"name": "Race Team", "slug": "race-team"},
        headers=_headers(owner["access_token"]),
    )
    assert team.status_code == 201, team.text
    team_id = team.json()["id"]
    assert (
        client.post(
            "/api/v1/teams/race-team/members",
            json={"email": "race-admin@example.com", "role": "admin"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    owner_id = client.get("/api/v1/users/me", headers=_headers(owner["access_token"])).json()["id"]
    other_id = client.get("/api/v1/users/me", headers=_headers(other["access_token"])).json()["id"]

    # Sequential invariant: the second removal must be refused.
    removed = client.delete(
        f"/api/v1/teams/race-team/members/{other_id}",
        headers=_headers(owner["access_token"]),
    )
    assert removed.status_code == 204, removed.text

    blocked = client.delete(
        f"/api/v1/teams/race-team/members/{owner_id}",
        headers=_headers(owner["access_token"]),
    )
    assert blocked.status_code == 409
    admins = (
        db_session.query(models.TeamMember)
        .filter(
            models.TeamMember.team_id == team_id,
            models.TeamMember.role == "admin",
        )
        .count()
    )
    assert admins == 1


def test_team_row_lock_serializes_membership_changes(database_engine):
    """The lock, not the process scheduler, enforces the invariant.

    Requires PostgreSQL: SQLite ignores ``FOR UPDATE``.
    """
    if database_engine.dialect.name != "postgresql":
        pytest.skip("row-level locks require PostgreSQL")

    session_factory = sessionmaker(bind=database_engine)
    with session_factory() as setup:
        first_user = models.User(email="lock-a@example.com", hashed_password="x", is_active=True)
        second_user = models.User(email="lock-b@example.com", hashed_password="x", is_active=True)
        setup.add_all([first_user, second_user])
        setup.flush()
        team = models.Team(
            name="Lock Race Team",
            slug="lock-race-team",
            created_by=first_user.id,
        )
        setup.add(team)
        setup.flush()
        setup.add_all(
            [
                models.TeamMember(team_id=team.id, user_id=first_user.id, role="admin"),
                models.TeamMember(team_id=team.id, user_id=second_user.id, role="admin"),
            ]
        )
        setup.commit()
        team_id = team.id

    holder = session_factory()
    crud.lock_team_for_membership_change(holder, team_id)
    acquired = threading.Event()

    def contender() -> None:
        db = session_factory()
        try:
            crud.lock_team_for_membership_change(db, team_id)
            acquired.set()
        finally:
            db.rollback()
            db.close()

    thread = threading.Thread(target=contender, daemon=True)
    thread.start()
    try:
        assert not acquired.wait(0.5), "second transaction acquired the lock too soon"
        holder.commit()
        assert acquired.wait(5), "second transaction never acquired the lock"
    finally:
        holder.close()
        thread.join(timeout=5)
