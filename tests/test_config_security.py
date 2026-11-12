"""Security hardening for runtime configuration (SEC-2.3)."""

import pytest
from pydantic import ValidationError

from app.config import Settings

STRONG_KEY = "k" * 64


def _production(**overrides) -> Settings:
    values = {
        "ENVIRONMENT": "production",
        "SECRET_KEY": STRONG_KEY,
        "DATABASE_URL": "postgresql://user:pass@localhost/db",
        "DB_SSLMODE": "require",
        "CORS_ORIGINS": "https://app.example.com",
    }
    values.update(overrides)
    return Settings(**values)


def test_production_rejects_short_secret_key():
    with pytest.raises(RuntimeError, match="at least 32"):
        _production(SECRET_KEY="short-key").validate_runtime()


def test_production_rejects_short_previous_key():
    with pytest.raises(RuntimeError, match="SECRET_KEY_PREVIOUS"):
        _production(SECRET_KEY_PREVIOUS="old-short").validate_runtime()


def test_production_rejects_unknown_algorithm():
    with pytest.raises(RuntimeError, match="ALGORITHM"):
        _production(ALGORITHM="none").validate_runtime()


def test_production_requires_tls_to_database():
    with pytest.raises(RuntimeError, match="DB_SSLMODE"):
        _production(DB_SSLMODE="prefer").validate_runtime()


def test_development_and_test_allow_short_keys():
    for environment in ("development", "test"):
        config = Settings(
            ENVIRONMENT=environment,
            SECRET_KEY="short-key",
            DATABASE_URL="postgresql://user:pass@localhost/db",
            DB_SSLMODE="prefer",
        )
        config.validate_runtime()


def test_valid_production_configuration_passes():
    _production().validate_runtime()


def test_verification_requires_smtp_outside_development():
    with pytest.raises(RuntimeError, match="EMAIL_BACKEND=smtp"):
        _production(EMAIL_VERIFICATION_REQUIRED=True, EMAIL_BACKEND="log").validate_runtime()


def test_smtp_backend_requires_host_and_from():
    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        _production(
            EMAIL_BACKEND="smtp", SMTP_HOST="", SMTP_FROM="no-reply@example.com"
        ).validate_runtime()
    with pytest.raises(RuntimeError, match="SMTP_FROM"):
        _production(
            EMAIL_BACKEND="smtp", SMTP_HOST="smtp.example.com", SMTP_FROM=""
        ).validate_runtime()


def test_valid_smtp_configuration_for_verification_passes():
    _production(
        EMAIL_VERIFICATION_REQUIRED=True,
        EMAIL_BACKEND="smtp",
        SMTP_HOST="smtp.example.com",
        SMTP_FROM="no-reply@example.com",
    ).validate_runtime()


def test_health_redis_url_only_when_redis_backs_rate_limiting():
    assert Settings(RATE_LIMIT_STORAGE_URI="memory://").health_redis_url == ""

    redis_settings = Settings(RATE_LIMIT_STORAGE_URI="redis://cache:6379/0")
    assert redis_settings.health_redis_url == "redis://cache:6379/0"


def test_port_must_be_within_range():
    with pytest.raises(ValidationError):
        Settings(PORT=70000)
