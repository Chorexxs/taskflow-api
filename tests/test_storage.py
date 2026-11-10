"""Object storage backend tests (T-053/T-054)."""

import httpx

from app.storage import StorageService


def _service(handler) -> StorageService:
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return StorageService(
        base_url="https://storage.example",
        api_key="test-key",
        bucket="taskflow-attachments",
        client=client,
    )


def test_build_key_is_unique_and_under_task():
    service = _service(lambda request: httpx.Response(500))
    first = service.build_key(7, ".txt")
    second = service.build_key(7, ".txt")

    assert first.startswith("attachments/7/")
    assert first.endswith(".txt")
    assert first != second


def test_direct_upload_uses_multipart_put():
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path.endswith("/upload-strategy"):
            return httpx.Response(
                200,
                json={
                    "method": "direct",
                    "uploadUrl": "/api/storage/buckets/taskflow-attachments/objects/attachments/1/a.txt",
                    "key": "attachments/1/a.txt",
                    "confirmRequired": False,
                },
            )
        return httpx.Response(200, json={"ok": True})

    service = _service(handler)
    service.put("attachments/1/a.txt", b"hello", "text/plain", "a.txt")

    assert calls == [
        ("POST", "/api/storage/buckets/taskflow-attachments/upload-strategy"),
        (
            "PUT",
            "/api/storage/buckets/taskflow-attachments/objects/attachments/1/a.txt",
        ),
    ]


def test_presigned_upload_confirms_size():
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        if request.url.path.endswith("/upload-strategy"):
            return httpx.Response(
                200,
                json={
                    "method": "presigned",
                    "uploadUrl": "https://s3.example/bucket",
                    "fields": {"key": "attachments/1/a.txt", "policy": "abc"},
                    "key": "attachments/1/a.txt",
                    "confirmRequired": True,
                    "confirmUrl": "/api/storage/buckets/taskflow-attachments/objects/attachments/1/a.txt/confirm-upload",
                },
            )
        return httpx.Response(200, json={"ok": True})

    service = _service(handler)
    service.put("attachments/1/a.txt", b"hello", "text/plain", "a.txt")

    assert calls[0][1].endswith("/upload-strategy")
    assert calls[1] == ("POST", "https://s3.example/bucket")
    assert calls[2][0] == "POST"
    assert calls[2][1].endswith("/objects/attachments/1/a.txt/confirm-upload")


def test_download_resolves_strategy_and_returns_bytes():
    def handler(request: httpx.Request) -> httpx.Response:
        if "/download-strategy/" in request.url.path:
            return httpx.Response(200, json={"url": "/files/object"})
        assert request.url.path == "/files/object"
        assert request.headers["Authorization"] == "Bearer test-key"
        return httpx.Response(200, content=b"payload")

    service = _service(handler)

    assert service.get("attachments/1/a.txt") == b"payload"


def test_delete_treats_missing_object_as_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "DELETE"
        return httpx.Response(404)

    service = _service(handler)

    service.delete("attachments/1/a.txt")
