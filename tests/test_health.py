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
