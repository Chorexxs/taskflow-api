import pytest
from fastapi.testclient import TestClient


def test_register_user(client: TestClient):
    response = client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "testpassword123"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data
    assert "hashed_password" not in data


def test_register_duplicate_email(client: TestClient):
    client.post(
        "/auth/register",
        json={"email": "duplicate@example.com", "password": "password123"}
    )
    response = client.post(
        "/auth/register",
        json={"email": "duplicate@example.com", "password": "password456"}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(client: TestClient):
    client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "password123"}
    )
    response = client.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    response = client.post(
        "/auth/login",
        data={"username": "nonexistent@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_get_current_user(client: TestClient):
    register_response = client.post(
        "/auth/register",
        json={"email": "current@example.com", "password": "password123"}
    )
    login_response = client.post(
        "/auth/login",
        data={"username": "current@example.com", "password": "password123"}
    )
    token = login_response.json()["access_token"]
    
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "current@example.com"


def test_get_current_user_no_token(client: TestClient):
    response = client.get("/users/me")
    assert response.status_code == 401
