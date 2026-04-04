import pytest
from fastapi.testclient import TestClient


def setup_full_hierarchy_with_tasks(client: TestClient, owner_email: str):
    client.post("/api/v1/auth/register", json={"email": owner_email, "password": "password123"})
    owner_token = client.post("/api/v1/auth/login", data={"username": owner_email, "password": "password123"}).json()["access_token"]
    
    client.post("/api/v1/teams/", json={"name": "Test Team", "slug": "test-team"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/", json={"name": "Test Project"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Task 1", "priority": "high"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Task 2", "priority": "medium"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Task 3", "priority": "low"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    return owner_token


def test_filter_tasks_by_priority(client: TestClient):
    owner_token = setup_full_hierarchy_with_tasks(client, "filterpriority@example.com")

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/?priority=high",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["priority"] == "high"


def test_pagination(client: TestClient):
    owner_token = setup_full_hierarchy_with_tasks(client, "pagination@example.com")

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/?page=1&page_size=2",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["pages"] == 2


def test_sort_tasks(client: TestClient):
    owner_token = setup_full_hierarchy_with_tasks(client, "sorting@example.com")

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/?sort_by=title&order=asc",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["title"] == "Task 1"
    assert data["items"][2]["title"] == "Task 3"


def test_search_in_team(client: TestClient):
    owner_token = setup_full_hierarchy_with_tasks(client, "search@example.com")

    response = client.get(
        "/api/v1/teams/test-team/search?q=1",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200


def test_page_size_limit(client: TestClient):
    owner_token = setup_full_hierarchy_with_tasks(client, "limit@example.com")

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/?page_size=200",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 100
