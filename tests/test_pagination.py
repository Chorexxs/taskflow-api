"""Uniform pagination envelope for every list endpoint (T-038)."""

from fastapi.testclient import TestClient


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(client: TestClient, email: str) -> dict:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "password123"},
        ).status_code
        == 201
    )
    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _assert_page(body: dict, *, total: int, page: int, pages: int, items: int):
    assert body["total"] == total
    assert body["page"] == page
    assert body["pages"] == pages
    assert body["has_next"] is (page < pages)
    assert len(body["items"]) == items


def _setup(client: TestClient):
    owner = _register_and_login(client, "pager-owner@example.com")
    for index in range(3):
        assert (
            client.post(
                "/api/v1/teams/",
                json={"name": f"Pager {index}", "slug": f"pager-{index}"},
                headers=_headers(owner["access_token"]),
            ).status_code
            == 201
        )

    _register_and_login(client, "pager-member@example.com")
    assert (
        client.post(
            "/api/v1/teams/pager-0/members",
            json={"email": "pager-member@example.com", "role": "member"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    _register_and_login(client, "pager-member2@example.com")
    assert (
        client.post(
            "/api/v1/teams/pager-0/members",
            json={"email": "pager-member2@example.com", "role": "member"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )

    for index in range(3):
        assert (
            client.post(
                "/api/v1/teams/pager-0/projects/",
                json={"name": f"Pager Project {index}"},
                headers=_headers(owner["access_token"]),
            ).status_code
            == 201
        )

    assert (
        client.post(
            "/api/v1/teams/pager-0/projects/Pager Project 0/tasks/",
            json={"title": "Pager Task"},
            headers=_headers(owner["access_token"]),
        ).status_code
        == 201
    )
    return owner


def test_teams_are_paginated(client: TestClient):
    owner = _setup(client)

    first = client.get(
        "/api/v1/teams/?page=1&page_size=2",
        headers=_headers(owner["access_token"]),
    )
    assert first.status_code == 200
    _assert_page(first.json(), total=3, page=1, pages=2, items=2)

    second = client.get(
        "/api/v1/teams/?page=2&page_size=2",
        headers=_headers(owner["access_token"]),
    )
    _assert_page(second.json(), total=3, page=2, pages=2, items=1)


def test_members_are_paginated(client: TestClient):
    owner = _setup(client)

    body = client.get(
        "/api/v1/teams/pager-0/members?page=1&page_size=2",
        headers=_headers(owner["access_token"]),
    ).json()

    _assert_page(body, total=3, page=1, pages=2, items=2)


def test_projects_are_paginated(client: TestClient):
    owner = _setup(client)

    body = client.get(
        "/api/v1/teams/pager-0/projects/?page=2&page_size=2",
        headers=_headers(owner["access_token"]),
    ).json()

    _assert_page(body, total=3, page=2, pages=2, items=1)


def test_attachments_are_paginated(client: TestClient, tmp_path, monkeypatch):
    from app.config import settings
    from app.routers import attachments as attachments_module

    monkeypatch.setattr(attachments_module, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    owner = _setup(client)
    url = "/api/v1/teams/pager-0/projects/Pager Project 0/tasks/Pager Task/attachments/"

    for name in ("first.txt", "second.txt"):
        assert (
            client.post(
                url,
                files={"file": (name, b"payload", "text/plain")},
                headers=_headers(owner["access_token"]),
            ).status_code
            == 201
        )

    body = client.get(
        f"{url}?page=1&page_size=1",
        headers=_headers(owner["access_token"]),
    ).json()

    _assert_page(body, total=2, page=1, pages=2, items=1)


def test_page_size_is_capped(client: TestClient):
    owner = _setup(client)

    response = client.get(
        "/api/v1/teams/?page_size=101",
        headers=_headers(owner["access_token"]),
    )

    assert response.status_code == 422
