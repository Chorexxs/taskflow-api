"""Attachments expose a SHA-256 checksum and never overwrite duplicates (T-055)."""

import hashlib

from fastapi.testclient import TestClient


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup(client: TestClient) -> tuple[str, str]:
    assert (
        client.post(
            "/api/v1/auth/register",
            json={"email": "checksum@example.com", "password": "password123"},
        ).status_code
        == 201
    )
    token = client.post(
        "/api/v1/auth/login",
        data={"username": "checksum@example.com", "password": "password123"},
    ).json()["access_token"]
    assert (
        client.post(
            "/api/v1/teams/",
            json={"name": "Checksum", "slug": "checksum"},
            headers=_headers(token),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/checksum/projects/",
            json={"name": "Checksum Project"},
            headers=_headers(token),
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/teams/checksum/projects/Checksum Project/tasks/",
            json={"title": "Checksum Task"},
            headers=_headers(token),
        ).status_code
        == 201
    )
    return token, (
        "/api/v1/teams/checksum/projects/Checksum Project/tasks/Checksum Task/attachments/"
    )


def test_upload_computes_checksum_and_keeps_duplicates(client: TestClient):
    token, url = _setup(client)
    payload = b"same content"
    expected = hashlib.sha256(payload).hexdigest()

    first = client.post(
        url,
        files={"file": ("same.txt", payload, "text/plain")},
        headers=_headers(token),
    )
    second = client.post(
        url,
        files={"file": ("same.txt", payload, "text/plain")},
        headers=_headers(token),
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["checksum"] == expected
    assert second.json()["checksum"] == expected
    assert first.json()["id"] != second.json()["id"]

    listed = client.get(url, headers=_headers(token)).json()["items"]
    assert {item["checksum"] for item in listed} == {expected}
