"""Comment listing supports explicit ascending/descending order (T-050)."""

from fastapi.testclient import TestClient


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup(client: TestClient):
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": "order@example.com", "password": "password123"},
        ).status_code
        == 201
    )
    token = client.post(
        "/api/v1/auth/login",
        data={"username": "order@example.com", "password": "password123"},
    ).json()["access_token"]
    assert (
        client.post(
            "/api/v1/teams/",
            json={"name": "Order", "slug": "order"},
            headers=_headers(token),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/order/projects/",
            json={"name": "Order Project"},
            headers=_headers(token),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/order/projects/Order Project/tasks/",
            json={"title": "Order Task"},
            headers=_headers(token),
        ).status_code
        == 201
    )
    url = "/api/v1/teams/order/projects/Order Project/tasks/Order Task/comments/"
    for content in ("first", "second", "third"):
        assert (
            client.post(url, json={"content": content}, headers=_headers(token)).status_code == 201
        )
    return token, url


def test_comments_order_is_configurable(client: TestClient):
    token, url = _setup(client)

    ascending = client.get(f"{url}?order=asc", headers=_headers(token)).json()
    descending = client.get(f"{url}?order=desc", headers=_headers(token)).json()

    assert [comment["content"] for comment in ascending["items"]] == [
        "first",
        "second",
        "third",
    ]
    assert [comment["content"] for comment in descending["items"]] == [
        "third",
        "second",
        "first",
    ]


def test_invalid_comment_order_is_rejected(client: TestClient):
    token, url = _setup(client)

    response = client.get(f"{url}?order=random", headers=_headers(token))

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
