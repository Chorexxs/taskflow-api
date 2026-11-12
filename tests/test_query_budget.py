"""T-128: keep the number of SQL round trips per action bounded.

The API and the database can live in different regions, where every statement
costs a full network round trip. These budgets stop a regression from silently
turning a click into dozens of queries.
"""

from sqlalchemy import event

from tests.test_tasks import setup_full_hierarchy

COUNTED = {"SELECT", "INSERT", "UPDATE", "DELETE"}


def _count_statements(engine, action):
    statements: list[str] = []

    def record(conn, cursor, statement, parameters, context, executemany):
        head = statement.lstrip().split(None, 1)[0].upper()
        if head in COUNTED:
            statements.append(head)

    event.listen(engine, "before_cursor_execute", record)
    try:
        response = action()
    finally:
        event.remove(engine, "before_cursor_execute", record)
    return response, len(statements)


def _login(client, email: str):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_reads_and_writes_stay_within_the_query_budget(client):
    from tests.conftest import test_engine

    setup_full_hierarchy(client, "budget@example.com")
    headers = _login(client, "budget@example.com")
    tasks = "/api/v1/teams/test-team/projects/test-project/tasks/"

    response, count = _count_statements(
        test_engine, lambda: client.get("/api/v1/teams/test-team", headers=headers)
    )
    assert response.status_code == 200
    assert count <= 3, f"team detail used {count} statements"

    response, count = _count_statements(
        test_engine, lambda: client.get("/api/v1/users/me", headers=headers)
    )
    assert response.status_code == 200
    assert count <= 2, f"/users/me used {count} statements"

    response, count = _count_statements(test_engine, lambda: client.get(tasks, headers=headers))
    assert response.status_code == 200
    assert count <= 6, f"board used {count} statements"

    created, count = _count_statements(
        test_engine,
        lambda: client.post(
            tasks,
            json={"title": "Budget task"},
            headers={**headers, "Idempotency-Key": "budget-key-1"},
        ),
    )
    assert created.status_code == 201
    assert count <= 11, f"create task used {count} statements"

    task_id = created.json()["id"]
    response, count = _count_statements(
        test_engine, lambda: client.get(f"{tasks}{task_id}", headers=headers)
    )
    assert response.status_code == 200
    assert count <= 6, f"task detail used {count} statements"

    response, count = _count_statements(
        test_engine,
        lambda: client.patch(
            f"{tasks}{task_id}/status",
            json={"status": "in_progress"},
            headers=headers,
        ),
    )
    assert response.status_code == 200
    assert response.json()["updated_at"] is not None
    assert count <= 8, f"status change used {count} statements"


def test_task_response_keeps_its_timestamps(client):
    setup_full_hierarchy(client, "budget@example.com")
    headers = _login(client, "budget@example.com")
    tasks = "/api/v1/teams/test-team/projects/test-project/tasks/"

    created = client.post(tasks, json={"title": "Timestamps"}, headers=headers)
    assert created.status_code == 201
    payload = created.json()
    assert payload["created_at"]
    assert payload["updated_at"]

    moved = client.patch(
        f"{tasks}{payload['id']}/status",
        json={"status": "done"},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["updated_at"]
