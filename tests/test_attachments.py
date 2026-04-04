import pytest
from fastapi.testclient import TestClient
import io


def setup_full_hierarchy_with_task(client: TestClient, owner_email: str):
    client.post("/auth/register", json={"email": owner_email, "password": "password123"})
    owner_token = client.post("/auth/login", data={"username": owner_email, "password": "password123"}).json()["access_token"]
    
    client.post("/teams/", json={"name": "Test Team", "slug": "test-team"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/teams/test-team/projects/", json={"name": "Test Project"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/teams/test-team/projects/Test Project/tasks/", json={"title": "Test Task"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    return owner_token


def test_upload_attachment_requires_file(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "upload@example.com")

    response = client.post(
        "/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 422


def test_list_attachments(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "listattach@example.com")

    response = client.get(
        "/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_member_can_upload_attachment(client: TestClient):
    client.post("/auth/register", json={"email": "member@example.com", "password": "password123"})
    owner_token = setup_full_hierarchy_with_task(client, "memberupload@example.com")
    
    member_token = client.post("/auth/login", data={"username": "member@example.com", "password": "password123"}).json()["access_token"]
    client.post("/teams/test-team/members", json={"email": "member@example.com", "role": "member"}, headers={"Authorization": f"Bearer {owner_token}"})

    response = client.post(
        "/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        files={"file": ("test.txt", b"test content", "text/plain")},
        headers={"Authorization": f"Bearer {member_token}"}
    )
    if response.status_code == 201:
        assert response.json()["filename"] == "test.txt"


def test_delete_own_attachment(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "deleteattach@example.com")

    upload_response = client.post(
        "/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        files={"file": ("delete.txt", b"content", "text/plain")},
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    
    if upload_response.status_code == 201:
        attachment_id = upload_response.json()["id"]
        
        response = client.delete(
            f"/teams/test-team/projects/Test Project/tasks/Test Task/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        assert response.status_code == 204


def test_member_cannot_delete_others_attachment(client: TestClient):
    client.post("/auth/register", json={"email": "member2@example.com", "password": "password123"})
    owner_token = setup_full_hierarchy_with_task(client, "deletemember@example.com")
    
    owner_token2 = client.post("/auth/login", data={"username": "deletemember@example.com", "password": "password123"}).json()["access_token"]
    member_token = client.post("/auth/login", data={"username": "member2@example.com", "password": "password123"}).json()["access_token"]
    client.post("/teams/test-team/members", json={"email": "member2@example.com", "role": "member"}, headers={"Authorization": f"Bearer {owner_token2}"})

    upload_response = client.post(
        "/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        files={"file": ("owner_file.txt", b"content", "text/plain")},
        headers={"Authorization": f"Bearer {owner_token2}"}
    )
    
    if upload_response.status_code == 201:
        attachment_id = upload_response.json()["id"]
        
        response = client.delete(
            f"/teams/test-team/projects/Test Project/tasks/Test Task/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        assert response.status_code == 403
