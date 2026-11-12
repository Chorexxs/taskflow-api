from fastapi.testclient import TestClient

from app import models
from app.config import settings
from app.routers import attachments as attachments_router
from app.storage import StorageError


class FakeObjectStorage:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def build_key(self, task_id: int, extension: str, filename: str | None = None) -> str:
        return f"attachments/{task_id}/fake{extension}"

    def put(self, key: str, data: bytes, content_type: str, filename: str | None = None) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


def test_insforge_storage_upload_download_delete(client: TestClient, db_session, monkeypatch):
    owner_token = setup_full_hierarchy_with_task(client, "storage@example.com")
    storage = FakeObjectStorage()
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "insforge")
    monkeypatch.setattr("app.storage._service", storage)
    headers = {"Authorization": f"Bearer {owner_token}"}
    url = "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/"

    upload = client.post(
        url,
        files={"file": ("stored.txt", b"object bytes", "text/plain")},
        headers=headers,
    )

    assert upload.status_code == 201
    attachment_id = upload.json()["id"]
    stored = db_session.query(models.Attachment).filter_by(id=attachment_id).one()
    assert stored.storage_key == "attachments/1/fake.txt"
    assert stored.content is None
    assert storage.objects[stored.storage_key] == b"object bytes"

    download = client.get(f"{url}{attachment_id}/download", headers=headers)
    assert download.status_code == 200
    assert download.content == b"object bytes"

    deleted = client.delete(f"{url}{attachment_id}", headers=headers)
    assert deleted.status_code == 204
    assert stored.storage_key not in storage.objects


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


def test_upload_rejects_content_that_does_not_match_the_extension(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "signature@example.com")
    headers = {"Authorization": f"Bearer {owner_token}"}
    url = "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/"

    mismatch = client.post(
        url,
        files={"file": ("fake.png", b"not a png", "image/png")},
        headers=headers,
    )
    assert mismatch.status_code == 415
    assert "does not match" in mismatch.json()["detail"]

    executable = client.post(
        url,
        files={"file": ("payload.txt", b"MZ\x90\x00", "text/plain")},
        headers=headers,
    )
    assert executable.status_code == 415

    valid = client.post(
        url,
        files={"file": ("note.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert valid.status_code == 201


def test_upload_rejects_malware(client: TestClient, db_session, monkeypatch):
    from app.malware import MalwareDetected, ScannerUnavailable
    from app.routers import attachments as attachments_router

    owner_token = setup_full_hierarchy_with_task(client, "malware@example.com")
    headers = {"Authorization": f"Bearer {owner_token}"}
    url = "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/"

    def infected(_data):
        raise MalwareDetected("stream: Eicar FOUND")

    monkeypatch.setattr(attachments_router, "scan_upload", infected)
    rejected = client.post(
        url,
        files={"file": ("note.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert rejected.status_code == 422
    assert db_session.query(models.Attachment).count() == 0

    def unavailable(_data):
        raise ScannerUnavailable("scanner down")

    monkeypatch.setattr(attachments_router, "scan_upload", unavailable)
    unavailable_response = client.post(
        url,
        files={"file": ("note.txt", b"hello", "text/plain")},
        headers=headers,
    )
    assert unavailable_response.status_code == 503


def test_upload_attachment_requires_file(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "upload@example.com")

    response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 422


def test_list_attachments(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "listattach@example.com")

    response = client.get(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_member_can_upload_attachment(client: TestClient):
    client.post(
        "/api/v1/auth/register", json={"email": "member@example.com", "password": "password123"}
    )
    owner_token = setup_full_hierarchy_with_task(client, "memberupload@example.com")

    member_token = client.post(
        "/api/v1/auth/login", data={"username": "member@example.com", "password": "password123"}
    ).json()["access_token"]
    client.post(
        "/api/v1/teams/test-team/members",
        json={"email": "member@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        files={"file": ("test.txt", b"test content", "text/plain")},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    if response.status_code == 201:
        assert response.json()["filename"] == "test.txt"


def test_delete_own_attachment(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "deleteattach@example.com")

    upload_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        files={"file": ("delete.txt", b"content", "text/plain")},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    if upload_response.status_code == 201:
        attachment_id = upload_response.json()["id"]

        response = client.delete(
            f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert response.status_code == 204


def test_member_cannot_delete_others_attachment(client: TestClient):
    client.post(
        "/api/v1/auth/register", json={"email": "member2@example.com", "password": "password123"}
    )
    setup_full_hierarchy_with_task(client, "deletemember@example.com")

    owner_token2 = client.post(
        "/api/v1/auth/login",
        data={"username": "deletemember@example.com", "password": "password123"},
    ).json()["access_token"]
    member_token = client.post(
        "/api/v1/auth/login", data={"username": "member2@example.com", "password": "password123"}
    ).json()["access_token"]
    client.post(
        "/api/v1/teams/test-team/members",
        json={"email": "member2@example.com", "role": "member"},
        headers={"Authorization": f"Bearer {owner_token2}"},
    )

    upload_response = client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/",
        files={"file": ("owner_file.txt", b"content", "text/plain")},
        headers={"Authorization": f"Bearer {owner_token2}"},
    )

    if upload_response.status_code == 201:
        attachment_id = upload_response.json()["id"]

        response = client.delete(
            f"/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/{attachment_id}",
            headers={"Authorization": f"Bearer {member_token}"},
        )
        assert response.status_code == 403


def test_delete_unknown_attachment_returns_404(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "delete404@example.com")

    response = client.delete(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/999999",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Attachment not found"


def test_delete_attachment_from_another_task_returns_404(client: TestClient):
    owner_token = setup_full_hierarchy_with_task(client, "deleteother@example.com")
    headers = {"Authorization": f"Bearer {owner_token}"}
    attachment_url = "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/"

    upload = client.post(
        attachment_url,
        files={"file": ("keep.txt", b"content", "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    attachment_id = upload.json()["id"]

    client.post(
        "/api/v1/teams/test-team/projects/Test Project/tasks/",
        json={"title": "Other Task"},
        headers=headers,
    )

    response = client.delete(
        "/api/v1/teams/test-team/projects/Test Project/tasks/Other Task"
        f"/attachments/{attachment_id}",
        headers=headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Attachment does not belong to this task"


def test_delete_attachment_survives_object_storage_failure(
    client: TestClient, db_session, monkeypatch
):
    owner_token = setup_full_hierarchy_with_task(client, "deletestorage@example.com")
    headers = {"Authorization": f"Bearer {owner_token}"}
    url = "/api/v1/teams/test-team/projects/Test Project/tasks/Test Task/attachments/"

    upload = client.post(
        url,
        files={"file": ("stored.txt", b"content", "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    attachment_id = upload.json()["id"]

    stored = db_session.query(models.Attachment).filter(models.Attachment.id == attachment_id).one()
    stored.storage_key = "attachments/1/stored.txt"
    db_session.commit()

    class BrokenStorage:
        def delete(self, key):
            raise StorageError("storage is down")

    monkeypatch.setattr(attachments_router, "get_storage", lambda: BrokenStorage())

    response = client.delete(f"{url}{attachment_id}", headers=headers)

    assert response.status_code == 204
    assert (
        db_session.query(models.Attachment).filter(models.Attachment.id == attachment_id).count()
        == 0
    )
