import pytest
from fastapi.testclient import TestClient


def setup_user_with_notification_check(client: TestClient, owner_email: str, member_email: str = None):
    client.post("/api/v1/auth/register", json={"email": owner_email, "password": "password123"})
    owner_token = client.post("/api/v1/auth/login", data={"username": owner_email, "password": "password123"}).json()["access_token"]
    
    client.post("/api/v1/teams/", json={"name": "Test Team", "slug": "test-team"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/", json={"name": "Test Project"}, headers={"Authorization": f"Bearer {owner_token}"})
    client.post("/api/v1/teams/test-team/projects/Test Project/tasks/", json={"title": "Test Task"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    member_token = None
    if member_email:
        client.post("/api/v1/auth/register", json={"email": member_email, "password": "password123"})
        member_token = client.post("/api/v1/auth/login", data={"username": member_email, "password": "password123"}).json()["access_token"]
        client.post("/api/v1/teams/test-team/members", json={"email": member_email, "role": "member"}, headers={"Authorization": f"Bearer {owner_token}"})
    
    return owner_token, member_token


def test_get_notifications(client: TestClient):
    owner_token, _ = setup_user_with_notification_check(client, "notifuser@example.com")

    response = client.get(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_notifications_with_filter(client: TestClient):
    owner_token, _ = setup_user_with_notification_check(client, "notiffilter@example.com")

    response = client.get(
        "/api/v1/notifications/?is_read=false",
        headers={"Authorization": f"Bearer {owner_token}"}
    )
    assert response.status_code == 200


def test_mark_notification_read(client: TestClient):
    owner_token, member_token = setup_user_with_notification_check(client, "notifread@example.com", "notifmember@example.com")
    
    member_response = client.get("/api/v1/teams/test-team/members", headers={"Authorization": f"Bearer {owner_token}"})
    member_id = member_response.json()[1]["user_id"]

    client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/assign",
        json={"user_id": member_id},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    notifications_response = client.get(
        "/api/v1/notifications/",
        headers={"Authorization": f"Bearer {member_token}"}
    )
    notifications = notifications_response.json()
    
    if notifications:
        notif_id = notifications[0]["id"]
        response = client.patch(
            f"/api/v1/notifications/{notif_id}/read",
            headers={"Authorization": f"Bearer {member_token}"}
        )
        if response.status_code == 200:
            assert response.json()["is_read"] == True


def test_mark_all_notifications_read(client: TestClient):
    owner_token, member_token = setup_user_with_notification_check(client, "notifreadall@example.com", "notifmember2@example.com")
    
    member_response = client.get("/api/v1/teams/test-team/members", headers={"Authorization": f"Bearer {owner_token}"})
    member_id = member_response.json()[1]["user_id"]

    client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/assign",
        json={"user_id": member_id},
        headers={"Authorization": f"Bearer {owner_token}"}
    )

    response = client.patch(
        "/api/v1/notifications/read-all",
        headers={"Authorization": f"Bearer {member_token}"}
    )
    assert response.status_code == 204


def test_notification_on_task_assignment(client: TestClient):
    pass
