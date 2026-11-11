"""Sentry events must never carry credentials or PII (SEC-2.1)."""

from app.main import _scrub_sentry_event


def test_scrub_sentry_event_redacts_auth_headers_and_bodies():
    event = {
        "request": {
            "headers": {
                "Authorization": "Bearer secret-token",
                "Cookie": "session=secret",
                "X-Api-Key": "key",
                "Content-Type": "application/json",
            },
            "data": {
                "email": "user@example.com",
                "password": "secret",
                "current_password": "secret",
                "refresh_token": "secret",
                "title": "visible",
            },
        }
    }

    scrubbed = _scrub_sentry_event(event, None)

    headers = scrubbed["request"]["headers"]
    assert headers["Authorization"] == "****"
    assert headers["Cookie"] == "****"
    assert headers["X-Api-Key"] == "****"
    assert headers["Content-Type"] == "application/json"
    data = scrubbed["request"]["data"]
    assert data["password"] == "****"
    assert data["current_password"] == "****"
    assert data["refresh_token"] == "****"
    assert data["title"] == "visible"


def test_scrub_sentry_event_handles_events_without_request():
    assert _scrub_sentry_event({"message": "boom"}, None) == {"message": "boom"}
