"""HTTP-level rate limiting tests (T-031)."""

import pytest

from app import main


@pytest.fixture
def rate_limited_client(client):
    """Enable the shared limiter for a single test and reset its counters."""
    limiter = main.app.state.limiter
    limiter.reset()
    limiter.enabled = True
    try:
        yield client
    finally:
        limiter.enabled = False
        limiter.reset()


def _login(client):
    return client.post(
        "/api/v1/auth/login",
        data={"username": "nobody@example.com", "password": "not-the-password"},
    )


def test_login_returns_429_with_retry_after(rate_limited_client):
    """The 11th login attempt in a minute is rejected with backoff headers."""
    for _ in range(10):
        response = _login(rate_limited_client)
        assert response.status_code == 401

    response = _login(rate_limited_client)

    assert response.status_code == 429
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) >= 0
    assert response.headers["X-RateLimit-Limit"] == "10"
    assert response.headers["X-RateLimit-Remaining"] == "0"

    body = response.json()
    assert body["detail"] == "Too many requests"
    assert body["error"]["code"] == "RATE_LIMITED"


def test_rate_limit_is_per_endpoint(rate_limited_client):
    """Exhausting login must not consume the refresh or search budgets."""
    for _ in range(10):
        assert _login(rate_limited_client).status_code == 401

    response = rate_limited_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-jwt"}
    )
    # Refresh has its own 30/minute budget, so it is not rate limited yet.
    assert response.status_code == 401
