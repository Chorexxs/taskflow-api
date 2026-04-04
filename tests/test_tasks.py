import pytest
from fastapi.testclient import TestClient


def setup_full_hierarchy(client: TestClient, owner_email: str, member_email: str = None):
    client.post("/api/v1/auth/register", json={"email": owner_email, "password": "password123"})
    owner_token = client.post("/api/v1/auth/login", data={"username": owner_email, "password": "password123"}).json()["access_token"]
    
    client.post("/api/v1/teams/", json={"name": "Test Team", "slug": "test-team"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/", json={"name": "Test Project"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    member_token = None
    if member_email:
        client.post("/api/v1/auth/register", json={"email": member_email, "password": "password123"})
        client.post("/api/v1/teams/test-team/members", json={"email": member_email, "role": "member"}, headers={"Authorization": f"Bearer {owner_token}"})
        member_token = client.post("/api/v1/auth/login", data={"username": member_email, "password": "password123"}).json()["access_token"]
    
    return owner_token, member_token


def test_create_task(client: TestClient):
    owner_token, _ = setup_full_hierarchy(client, "taskowner@example.com")

    response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/",
        json={"title": "New Task", "description": "Task description", "priority": "high"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Task"
    assert data["priority"] == "high"
    assert data["status"] == "todo"


def test_list_tasks(client: TestClient):
    owner_token, _ = setup_full_hierarchy(client, "listtask@example.com")

    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Task 1"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Task 2"}, headers={"Authorization": f"Bearer {owner_token}"})

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_get_task(client: TestClient):
    owner_token, _ = setup_full_hierarchy(client, "gettask@example.com")

    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Get Task"}, headers={"Authorization": f"Bearer {owner_token}"})

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Get Task",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Get Task"


def test_update_task_status(client: TestClient):
    owner_token, _ = setup_full_hierarchy(client, "updatetask@example.com")

    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Task to Update"}, headers={"Authorization": f"Bearer {owner_token}"})

    response = client.patch(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Task to Update",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_assign_task_to_member(client: TestClient):
    owner_token, member_token = setup_full_hierarchy(client, "assignowner@example.com", "taskmember@example.com")

    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Task to Assign"}, headers={"Authorization": f"Bearer {owner_token}"})

    member_response = client.get("/api/v1/teams/test-team/members", headers={"Authorization": f"Bearer {owner_token}"})
    member_id = member_response.json()[1]["user_id"]

    response = client.patch(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Task to Assign/assign",
        json={"user_id": member_id},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    assert response.json()["assigned_to"] == member_id


def test_assign_task_to_non_member_returns_400(client: TestClient):
    owner_token, _ = setup_full_hierarchy(client, "assignerror@example.com")
    client.post("/api/v1/auth/register", json={"email": "outsider@example.com", "password": "password123"})

    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Task"}, headers={"Authorization": f"Bearer {owner_token}"})

    outsider = client.post("/api/v1/auth/login", data={"username": "outsider@example.com", "password": "password123"}).json()
    outsider_id = 999

    response = client.patch(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Task/assign",
        json={"user_id": outsider_id},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 400


def test_delete_task_as_creator(client: TestClient):
    owner_token, _ = setup_full_hierarchy(client, "deletetask@example.com")

    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Task to Delete"}, headers={"Authorization": f"Bearer {owner_token}"})

    response = client.delete(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Task to Delete",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 204


def test_member_cannot_delete_others_task(client: TestClient):
    owner_token, member_token = setup_full_hierarchy(client, "deletemember@example.com", "deletemember2@example.com")

    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Owner's Task"}, headers={"Authorization": f"Bearer {owner_token}"})

    response = client.delete(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Owner's Task",
        headers={"Authorization": f"Bearer {member_token}"}
    )
    assert response.status_code == 403
