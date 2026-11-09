from fastapi.testclient import TestClient


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def setup_user_with_notification_check(client: TestClient, owner_email: str, member_email: str = None):
    client.post("/api/v1/auth/register", json={"email": owner_email, "password": "password123"})
    owner_token = client.post(
        "/api/v1/auth/login",
        data={"username": owner_email, "password": "password123"},
    ).json()["access_token"]

    client.post(
        "/api/v1/teams/",
        json={"name": "Test Team", "slug": "test-team"},
        headers=_headers(owner_token),
    )
    client.post(
        "/api/v1/teams/test-team/projects/",
        json={"name": "Test Project"},
        headers=_headers(owner_token),
    )
    client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/",
        json={"title": "Test Task"},
        headers=_headers(owner_token),
    )

    member_token = None
    if member_email:
        client.post("/api/v1/auth/register", json={"email": member_email, "password": "password123"})
        member_token = client.post(
            "/api/v1/auth/login",
            data={"username": member_email, "password": "password123"},
        ).json()["access_token"]
        client.post(
            "/api/v1/teams/test-team/members",
            json={"email": member_email, "role": "member"},
            headers=_headers(owner_token),
        )

    return owner_token, member_token


def _assign_task(client: TestClient, owner_token: str, member_token: str) -> None:
    members = client.get("/api/v1/teams/test-team/members", headers=_headers(owner_token)).json()
    member_id = next(member["user_id"] for member in members if member["role"] == "member")
    response = client.patch(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/assign",
        json={"user_id": member_id},
        headers=_headers(owner_token),
    )
    assert response.status_code == 200
    assert member_token


def test_get_notifications_returns_pagination_envelope(client: TestClient):
    owner_token, _ = setup_user_with_notification_check(client, "notifuser@example.com")

    response = client.get("/api/v1/notifications/", headers=_headers(owner_token))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "total", "page", "pages", "has_next"}
    assert isinstance(body["items"], list)


def test_get_notifications_with_filter(client: TestClient):
    owner_token, _ = setup_user_with_notification_check(client, "notiffilter@example.com")

    response = client.get(
        "/api/v1/notifications/?is_read=false",
        headers=_headers(owner_token),
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_notification_on_task_assignment_and_unread_count(client: TestClient):
    owner_token, member_token = setup_user_with_notification_check(
        client,
        "notifassign@example.com",
        "notifassignmember@example.com",
    )
    _assign_task(client, owner_token, member_token)

    response = client.get("/api/v1/notifications/", headers=_headers(member_token))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["type"] == "assigned"
    assert body["items"][0]["is_read"] is False

    count = client.get("/api/v1/notifications/unread-count", headers=_headers(member_token))
    assert count.status_code == 200
    assert count.json() == {"count": 1}


def test_mark_notification_read(client: TestClient):
    owner_token, member_token = setup_user_with_notification_check(
        client,
        "notifread@example.com",
        "notifmember@example.com",
    )
    _assign_task(client, owner_token, member_token)

    notifications = client.get(
        "/api/v1/notifications/",
        headers=_headers(member_token),
    ).json()["items"]
    assert notifications

    response = client.patch(
        f"/api/v1/notifications/{notifications[0]['id']}/read",
        headers=_headers(member_token),
    )
    assert response.status_code == 200
    assert response.json()["is_read"] is True

    count = client.get("/api/v1/notifications/unread-count", headers=_headers(member_token))
    assert count.json() == {"count": 0}


def test_mark_all_notifications_read(client: TestClient):
    owner_token, member_token = setup_user_with_notification_check(
        client,
        "notifreadall@example.com",
        "notifmember2@example.com",
    )
    _assign_task(client, owner_token, member_token)

    response = client.patch("/api/v1/notifications/read-all", headers=_headers(member_token))
    assert response.status_code == 204

    count = client.get("/api/v1/notifications/unread-count", headers=_headers(member_token))
    assert count.json() == {"count": 0}


def test_notifications_are_private_to_their_owner(client: TestClient):
    owner_token, member_token = setup_user_with_notification_check(
        client,
        "notifprivate@example.com",
        "notifprivatemember@example.com",
    )
    _assign_task(client, owner_token, member_token)

    owner_notifications = client.get(
        "/api/v1/notifications/",
        headers=_headers(owner_token),
    ).json()
    assert owner_notifications["total"] == 0
