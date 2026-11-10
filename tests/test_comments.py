from fastapi.testclient import TestClient


def setup_full_hierarchy_with_task(client: TestClient, owner_email: str):
    client.post("/api/v1/auth/register", json={"email": owner_email, "password": "password123"})
    owner_token = client.post(
        "/api/v1/auth/login", data={"username": owner_email, "password": "password123"}
    ).json()["access_token"]

    client.post(
        "/api/v1/teams/",
        json={"name": "Test Team", "slug": "test-team"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    client.post(
        "/api/v1/teams/test-team/projects/",
        json={"name": "Test Project"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/",
        json={"title": "Test Task"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    return owner_token


def test_create_comment(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "commentowner@example.com")

    response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "This is a comment"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["content"] == "This is a comment"
    assert "id" in data


def test_list_comments(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "listcomment@example.com")

    client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "Comment 1"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "Comment 2"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert set(body) == {"items", "total", "page", "pages", "has_next"}


def test_comments_pagination(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "commentpage@example.com")

    for index in range(3):
        client.post(
            "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
            json={"content": f"Comment {index}"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/?page=2&page_size=2",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 2
    assert body["pages"] == 2
    assert len(body["items"]) == 1
    assert body["has_next"] is False


def test_removed_member_cannot_edit_comment(client: TestClient):
    client.post(
        "/api/v1/auth/register", json={"email": "exmember@example.com", "password": "password123"}
    )
    owner_token = setup_full_hierarchy_with_task(client, "commentowner4@example.com")
    exmember_token = client.post(
        "/api/v1/auth/login",
        data={"username": "exmember@example.com", "password": "password123"},
    ).json()["access_token"]
    client.post(
        "/api/v1/teams/test-team/members",
        json={"email": "exmember@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    comment = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "Old member comment"},
        headers={"Authorization": f"Bearer {exmember_token}"},
    ).json()

    # The ex-member leaves voluntarily.
    members = client.get(
        "/api/v1/teams/test-team/members",
        headers={"Authorization": f"Bearer {exmember_token}"},
    ).json()["items"]
    member_id = next(m["user_id"] for m in members if m["user"]["email"] == "exmember@example.com")
    assert (
        client.delete(
            f"/api/v1/teams/test-team/members/{member_id}",
            headers={"Authorization": f"Bearer {exmember_token}"},
        ).status_code
        == 204
    )

    response = client.patch(
        f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/{comment['id']}",
        json={"content": "Should not work"},
        headers={"Authorization": f"Bearer {exmember_token}"},
    )
    assert response.status_code == 403


def test_update_own_comment(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "updatecomment@example.com")

    create_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "Original content"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    comment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/{comment_id}",
        json={"content": "Updated content"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Updated content"


def test_update_others_comment_returns_403(client: TestClient):
    client.post(
        "/api/v1/auth/register", json={"email": "member@example.com", "password": "password123"}
    )
    owner_token = setup_full_hierarchy_with_task(client, "commentowner2@example.com")

    member_token = client.post(
        "/api/v1/auth/login", data={"username": "member@example.com", "password": "password123"}
    ).json()["access_token"]
    client.post(
        "/api/v1/teams/test-team/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    create_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "Owner's comment"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    comment_id = create_response.json()["id"]

    response = client.patch(
        f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/{comment_id}",
        json={"content": "Trying to edit"},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert response.status_code == 403


def test_delete_own_comment(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "deletecomment@example.com")

    create_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "To delete"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    comment_id = create_response.json()["id"]

    response = client.delete(
        f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/{comment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 204


def test_admin_can_delete_others_comment(client: TestClient):
    client.post(
        "/api/v1/auth/register", json={"email": "admin@example.com", "password": "password123"}
    )
    owner_token = setup_full_hierarchy_with_task(client, "commentowner3@example.com")

    admin_token = client.post(
        "/api/v1/auth/login", data={"username": "admin@example.com", "password": "password123"}
    ).json()["access_token"]
    client.post(
        "/api/v1/teams/test-team/members",
        json={"email": "admin@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    client.post(
        "/api/v1/teams/test-team/members",
        json={"email": "admin@example.com", "role": "admin"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    create_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/",
        json={"content": "Member's comment"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    comment_id = create_response.json()["id"]

    response = client.delete(
        f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/comments/{comment_id}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 204
