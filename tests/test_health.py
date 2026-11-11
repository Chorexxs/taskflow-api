"""Liveness and readiness probes."""

from fastapi.testclient import TestClient


def test_liveness_probe(client: TestClient):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_root_endpoint(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "TaskFlow API"}


def test_security_headers_are_present(client: TestClient):
    response = client.get("/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["Permissions-Policy"]


def test_readiness_probe_ready(client: TestClient, monkeypatch):
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, _statement):
            return None

    class FakeEngine:
        def connect(self):
            return FakeConnection()

    monkeypatch.setattr("app.database.get_engine", lambda: FakeEngine())
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "connected"}


def test_readiness_probe_not_ready(client: TestClient, monkeypatch):
    monkeypatch.setattr("app.database.get_engine", lambda: None)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_health_does_not_block_on_unreachable_redis(client: TestClient, monkeypatch):
    """An optional Redis must fail fast instead of delaying /health (T-094)."""
    captured: dict[str, float] = {}

    def fake_from_url(_url, **kwargs):
        captured.update(kwargs)
        raise ConnectionError("redis unreachable")

    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    monkeypatch.setattr("redis.from_url", fake_from_url)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["redis"] == "not_available"
    assert captured["socket_connect_timeout"] <= 0.5
    assert captured["socket_timeout"] <= 0.5


def test_health_skips_redis_without_url(client: TestClient, monkeypatch):
    """Without REDIS_URL the probe reports not_configured and does not block."""
    monkeypatch.delenv("REDIS_URL", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["redis"] == "not_configured"


def test_health_does_not_leak_database_errors(client: TestClient, monkeypatch):
    class BrokenEngine:
        def connect(self):
            raise RuntimeError("connection to secret-host:5432 failed for user admin")

    monkeypatch.setattr("app.database.get_engine", lambda: BrokenEngine())

    response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["database"] == "unavailable"
    assert "secret-host" not in response.text
    assert "admin" not in response.text
