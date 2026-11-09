"""Central application configuration.

All environment-driven settings live here so that the rest of the
application has a single, validated source of truth.

The module fails fast in production when a critical value is missing and
uses safe development defaults everywhere else.
"""

import warnings

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEV_SECRET_KEY = "dev-only-insecure-secret-key-change-me"
DEFAULT_DEV_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables and ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Runtime
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Security / JWT
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 15

    # Database
    DATABASE_URL: str = ""
    POOL_SIZE: int = 10
    MAX_OVERFLOW: int = 20
    POOL_PRE_PING: bool = True

    # HTTP
    CORS_ORIGINS: str = ""

    # Optional services
    REDIS_URL: str = "redis://localhost:6379/0"
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.0

    # Uploads
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    UPLOAD_DIR: str = "uploads"
    ALLOWED_UPLOAD_EXTENSIONS: str = (
        "png,jpg,jpeg,gif,webp,pdf,txt,csv,json,md,doc,docx,xls,xlsx,ppt,pptx,zip"
    )

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES", "REFRESH_TOKEN_EXPIRE_DAYS", mode="before")
    @classmethod
    def _positive_token_lifetimes(cls, value):
        """Reject empty or non-positive token lifetimes early."""
        if isinstance(value, str) and not value.strip():
            raise ValueError("token lifetime must be a positive integer")
        if int(value) <= 0:
            raise ValueError("token lifetime must be greater than zero")
        return value

    @property
    def is_production(self) -> bool:
        """Whether the app is running in a production-like environment."""
        return self.ENVIRONMENT.lower() in {"production", "prod"}

    @property
    def secret_key(self) -> str:
        """Return the configured secret, with a dev-only fallback."""
        if self.SECRET_KEY:
            return self.SECRET_KEY
        if self.is_production:
            raise RuntimeError("SECRET_KEY must be set in production")
        return DEV_SECRET_KEY

    @property
    def cors_origins(self) -> list[str]:
        """Parse the comma-separated CORS allowlist."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def effective_cors_origins(self) -> list[str]:
        """Return the CORS allowlist, using localhost defaults in development."""
        origins = self.cors_origins
        if origins:
            if "*" in origins and self.is_production:
                raise RuntimeError("CORS_ORIGINS cannot contain '*' in production")
            return origins
        if self.is_production:
            raise RuntimeError("CORS_ORIGINS must be set in production")
        return list(DEFAULT_DEV_ORIGINS)

    @property
    def allowed_upload_extensions(self) -> set[str]:
        """Return the normalized set of allowed upload extensions."""
        return {
            extension.strip().lower().lstrip(".")
            for extension in self.ALLOWED_UPLOAD_EXTENSIONS.split(",")
            if extension.strip()
        }

    def validate_runtime(self) -> None:
        """Validate critical settings at import time.

        Production must never start with insecure defaults. Development and
        test keep working with warnings so contributors can run the app
        without a full environment.
        """
        if not self.SECRET_KEY:
            if self.is_production:
                raise RuntimeError("SECRET_KEY must be set in production")
            warnings.warn(
                "SECRET_KEY is not set; using a development-only key",
                RuntimeWarning,
                stacklevel=2,
            )
        if not self.DATABASE_URL:
            if self.is_production:
                raise RuntimeError("DATABASE_URL must be set in production")
            warnings.warn(
                "DATABASE_URL is not set; database features will be unavailable",
                RuntimeWarning,
                stacklevel=2,
            )


settings = Settings()
settings.validate_runtime()
