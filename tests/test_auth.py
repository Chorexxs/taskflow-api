import pytest
from fastapi.testclient import TestClient


def test_register_user(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"}
    )
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "duplicate@example.com", "password": "password456"}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client: TestClient):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "password123"}
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "nonexistent@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_get_current_user(client: TestClient):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "current@example.com", "password": "password123"}
    )
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "current@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "current@example.com"


def test_get_current_user_no_token(client: TestClient):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_e2e_full_flow(client: TestClient):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "e2e@example.com", "password": "password123"}
    )
    assert register_response.status_code == 201
    
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "e2e@example.com", "password": "password123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    team_response = client.post(
        "/api/v1/teams/",
        json={"name": "E2E Team", "slug": "e2e-team", "description": "E2E test team"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert team_response.status_code == 201
    
    project_response = client.post(
        "/api/v1/teams/e2e-team/projects/",
        json={"name": "E2E Project", "description": "E2E test project"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert project_response.status_code == 201
    project_data = project_response.json()
    project_id = project_data["id"]
    
    task_response = client.post(
        f"/api/v1/teams/e2e-team/projects/{project_id}/tasks/",
        json={"title": "E2E Task", "description": "E2E test task", "priority": "high"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert task_response.status_code == 201
    task_data = task_response.json()
    
    comment_response = client.post(
        f"/api/v1/teams/e2e-team/projects/{project_id}/tasks/{task_data['id']}/comments/",
        json={"content": "E2E Comment"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert comment_response.status_code == 201
    
    notifications_response = client.get(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert notifications_response.status_code == 200
