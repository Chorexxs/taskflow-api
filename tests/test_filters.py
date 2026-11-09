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
        "/api/v1/teams/test-team/search?q=Task",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["projects"]["total"] == 0
    assert body["tasks"]["total"] == 3

    project_response = client.get(
        "/api/v1/teams/test-team/search?q=Project",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    project_body = project_response.json()
    assert project_body["projects"]["total"] == 1
    assert project_body["projects"]["items"][0]["name"] == "Test Project"
    assert project_body["tasks"]["total"] == 0


def test_search_finds_tasks_outside_matching_projects(client: TestClient):
    owner_token = setup_full_hierarchy_with_tasks(client, "searchdesc@example.com")
    client.post(
        "/api/v1/teams/test-team/projects/",
        json={"name": "Other Project", "description": "secret alpha"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    client.post(
        "/api/v1/teams/test-team/projects/Other Project/tasks/",
        json={"title": "Unrelated", "description": "bravo content"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.get(
        "/api/v1/teams/test-team/search?q=bravo",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    assert response.json()["tasks"]["total"] == 1
    assert response.json()["tasks"]["items"][0]["title"] == "Unrelated"


def test_search_escapes_like_wildcards(client: TestClient):
    owner_token = setup_full_hierarchy_with_tasks(client, "searchwild@example.com")

    response = client.get(
        "/api/v1/teams/test-team/search?q=%25%25",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["projects"]["total"] == 0
    assert body["tasks"]["total"] == 0


def test_search_requires_two_characters(client: TestClient):
    owner_token = setup_full_hierarchy_with_tasks(client, "searchshort@example.com")

    response = client.get(
        "/api/v1/teams/test-team/search?q=a",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 422


def test_page_size_limit(client: TestClient):
    owner_token = setup_full_hierarchy_with_tasks(client, "limit@example.com")

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/?page_size=200",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 100
