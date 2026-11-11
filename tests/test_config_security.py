"""Security hardening for runtime configuration (SEC-2.3)."""

import pytest

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
