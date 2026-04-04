import pytest
from fastapi.testclient import TestClient


def setup_full_hierarchy_with_task(client: TestClient, owner_email: str):
    client.post("/api/v1/auth/register", json={"email": owner_email, "password": "password123"})
    owner_token = client.post("/api/v1/auth/login", data={"username": owner_email, "password": "password123"}).json()["access_token"]
    
    client.post("/api/v1/teams/", json={"name": "Test Team", "slug": "test-team"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/", json={"name": "Test Project"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Test Task"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    return owner_token


def test_task_creation_logs_activity(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "logowner@example.com")

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/activity",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    activities = response.json()
    assert len(activities) >= 1
    assert activities[0]["entity_type"] == "task"
    assert activities[0]["action"] == "created"


def test_task_status_change_logs_activity(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "statuslog@example.com")

    client.patch(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task",
        json={"status": "in_progress"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/activity",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    activities = response.json()
    status_activities = [a for a in activities if "status" in a["action"]]
    assert len(status_activities) >= 1


def test_task_assignment_logs_activity(client: TestClient):
    client.post("/api/v1/auth/register", json={"email": "member@example.com", "password": "password123"})
    owner_token = setup_full_hierarchy_with_task(client, "assignlog@example.com")
    
    member_token = client.post("/api/v1/auth/login", data={"username": "member@example.com", "password": "password123"}).json()["access_token"]
    client.post("/api/v1/teams/test-team/members", json={"email": "member@example.com", "role": "member"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    member_response = client.get("/api/v1/teams/test-team/members", headers={"Authorization": f"Bearer {owner_token}"})
    member_id = member_response.json()[1]["user_id"]

    client.patch(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/assign",
        json={"user_id": member_id},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/activity",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    activities = response.json()
    assigned_activities = [a for a in activities if a["action"] == "assigned"]
    assert len(assigned_activities) >= 1


def test_project_creation_logs_activity(client: TestClient):
    client.post("/api/v1/auth/register", json={"email": "projlog@example.com", "password": "password123"})
    token = client.post("/api/v1/auth/login", data={"username": "projlog@example.com", "password": "password123"}).json()["access_token"]
    
    client.post("/api/v1/teams/", json={"name": "Log Team", "slug": "log-team"}, headers={"Authorization": f"Bearer {token}"})
    client.post("/api/v1/teams/log-team/projects/", json={"name": "Log Project"}, headers={"Authorization": f"Bearer {token}"})
    
    response = client.get(
        "/api/v1/teams/log-team/projects/Log Project/activity",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    activities = response.json()
    assert len(activities) >= 1
    assert activities[0]["entity_type"] == "project"
    assert activities[0]["action"] == "created"


def test_role_change_logs_activity(client: TestClient):
    client.post("/api/v1/auth/register", json={"email": "roleadmin@example.com", "password": "password123"})
    owner_token = setup_full_hierarchy_with_task(client, "rolelog@example.com")
    
    member_token = client.post("/api/v1/auth/login", data={"username": "roleadmin@example.com", "password": "password123"}).json()["access_token"]
    client.post("/api/v1/teams/test-team/members", json={"email": "roleadmin@example.com", "role": "member"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    member_response = client.get("/api/v1/teams/test-team/members", headers={"Authorization": f"Bearer {owner_token}"})
    member_id = member_response.json()[1]["user_id"]

    client.patch(
        f"/api/v1/teams/test-team/members/{member_id}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
