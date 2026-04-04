import pytest
from fastapi.testclient import TestClient


def setup_full_hierarchy_with_task(client: TestClient, owner_email: str):
    client.post("/api/v1/auth/register", json={"email": owner_email, "password": "password123"})
    owner_token = client.post("/api/v1/auth/login", data={"username": owner_email, "password": "password123"}).json()["access_token"]
    
    client.post("/api/v1/teams/", json={"name": "Test Team", "slug": "test-team"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/", json={"name": "Test Project"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Test Task"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    return owner_token


def test_create_comment(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "commentowner@example.com")

    response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "This is a comment"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "This is a comment"
    assert "id" in data


def test_list_comments(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "listcomment@example.com")

    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/", json={"content": "Comment 1"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/", json={"content": "Comment 2"}, headers={"Authorization": f"Bearer {owner_token}"})

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_update_own_comment(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "updatecomment@example.com")

    create_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "Original content"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    comment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/{comment_id}",
        json={"content": "Updated content"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Updated content"


def test_update_others_comment_returns_403(client: TestClient):
    client.post("/api/v1/auth/register", json={"email": "member@example.com", "password": "password123"})
    owner_token = setup_full_hierarchy_with_task(client, "commentowner2@example.com")
    
    member_token = client.post("/api/v1/auth/login", data={"username": "member@example.com", "password": "password123"}).json()["access_token"]
    client.post("/api/v1/teams/test-team/members", json={"email": "member@example.com", "role": "member"}, headers={"Authorization": f"Bearer {owner_token}"})

    create_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "Owner's comment"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    comment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/{comment_id}",
        json={"content": "Trying to edit"},
        headers={"Authorization": f"Bearer {member_token}"}
    )
    assert response.status_code == 403


def test_delete_own_comment(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "deletecomment@example.com")

    create_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "To delete"},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    comment_id = create_response.json()["id"]

    response = client.delete(
        f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/{comment_id}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 204


def test_admin_can_delete_others_comment(client: TestClient):
    client.post("/api/v1/auth/register", json={"email": "admin@example.com", "password": "password123"})
    owner_token = setup_full_hierarchy_with_task(client, "commentowner3@example.com")
    
    admin_token = client.post("/api/v1/auth/login", data={"username": "admin@example.com", "password": "password123"}).json()["access_token"]
    client.post("/api/v1/teams/test-team/members", json={"email": "admin@example.com", "role": "member"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/members", json={"email": "admin@example.com", "role": "admin"}, headers={"Authorization": f"Bearer {owner_token}"})

    create_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "Member's comment"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    comment_id = create_response.json()["id"]

    response = client.delete(
        f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/{comment_id}",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 204
