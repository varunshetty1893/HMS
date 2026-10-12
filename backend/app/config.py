"""Centralized environment configuration and startup validation.

All configuration is loaded via Pydantic BaseSettings from environment variables
or `backend/.env`. No other module may call `os.getenv` or `os.environ` directly.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

FORBIDDEN_PRODUCTION_SECRET_PATTERNS: tuple[str, ...] = (
    "change_me",
    "dev_only",
    "placeholder",
    "example",
    "secret_key",
    "your_secret",
)


class Settings(BaseSettings):
    """Typed, validated application settings for the FastAPI backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Core Application Settings ---
    app_name: str = Field(default="Restaurant Management & QR Ordering API")
    app_version: str = Field(default="0.1.0")
    environment: Literal["development", "test", "staging", "production"] = Field(
        default="development"
    )
    debug: bool = Field(default=False)
    api_v1_prefix: str = Field(default="/api/v1")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO")

    # --- PostgreSQL Database Configuration ---
    database_url: str = Field(
        default="postgresql+asyncpg://restaurant_app:dev_pass@127.0.0.1:5432/restaurant_dev"
    )
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=100)
    db_pool_recycle_seconds: int = Field(default=1800, ge=60)
    db_connect_timeout_seconds: float = Field(default=5.0, gt=0.1, le=60.0)
    db_echo_sql: bool = Field(default=False)

    # --- Authentication & Cryptographic Secrets ---
    jwt_secret_key: str = Field(
        default="dev_only_jwt_secret_key_do_not_use_in_production_0123456789abcdef"
    )
    csrf_secret_key: str = Field(
        default="dev_only_csrf_secret_key_do_not_use_in_production_0123456789abcdef"
    )
    qr_token_encryption_key: str | None = Field(default=None)
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)

    # --- Network, CORS & QR Base URL ---
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:3000",
        ]
    )
    public_qr_base_url: str = Field(default="http://localhost:5173/q")

    # --- Realtime WebSockets ---
    ws_max_connections: int = Field(default=200, ge=10, le=5000)
    ws_heartbeat_interval_seconds: int = Field(default=30, ge=5, le=300)

    # --- Local File Storage ---
    upload_dir: Path = Field(default=Path("./uploads/menu"))
    max_upload_size_bytes: int = Field(default=2_097_152, ge=1024, le=10_485_760)

    @field_validator("api_v1_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        if not cleaned.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/' (e.g., '/api/v1').")
        return cleaned

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    raise ValueError("CORS_ALLOWED_ORIGINS JSON value must be a list.")
                return [str(origin).strip() for origin in parsed if str(origin).strip()]
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return [str(origin).strip() for origin in value if str(origin).strip()]

    @field_validator("cors_allowed_origins")
    @classmethod
    def forbid_wildcard_cors(cls, origins: list[str]) -> list[str]:
        for origin in origins:
            if origin == "*":
                raise ValueError(
                    "Wildcard '*' is forbidden in CORS_ALLOWED_ORIGINS. "
                    "Specify explicit origins only."
                )
        return origins

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("DATABASE_URL cannot be empty.")
        allowed_schemes = (
            "postgresql+asyncpg://",
            "sqlite+aiosqlite://",
        )
        if not cleaned.startswith(allowed_schemes):
            raise ValueError(
                "DATABASE_URL must use an async SQLAlchemy driver "
                "('postgresql+asyncpg://' or 'sqlite+aiosqlite://' for isolated tests)."
            )
        return cleaned

    @model_validator(mode="after")
    def validate_production_safety(self) -> Settings:
        """Enforce non-negotiable production security invariants (`docs/06` & `docs/10`)."""
        if self.environment == "production":
            if self.debug:
                raise ValueError("DEBUG=true is strictly forbidden when ENVIRONMENT='production'.")
            if self.db_echo_sql:
                raise ValueError(
                    "DB_ECHO_SQL=true is strictly forbidden when ENVIRONMENT='production'."
                )
            secrets_to_validate: list[tuple[str, str]] = [
                ("JWT_SECRET_KEY", self.jwt_secret_key),
                ("CSRF_SECRET_KEY", self.csrf_secret_key),
            ]
            if self.qr_token_encryption_key is not None:
                secrets_to_validate.append(
                    ("QR_TOKEN_ENCRYPTION_KEY", self.qr_token_encryption_key)
                )
            for secret_name, secret_val in secrets_to_validate:
                if len(secret_val.strip()) < 32:
                    raise ValueError(f"{secret_name} must be at least 32 characters in production.")
                lowered = secret_val.lower()
                if any(pattern in lowered for pattern in FORBIDDEN_PRODUCTION_SECRET_PATTERNS):
                    raise ValueError(
                        f"{secret_name} contains an unsafe placeholder or development "
                        "value and cannot be used in production."
                    )
            if self.database_url.startswith("sqlite"):
                raise ValueError(
                    "SQLite is forbidden in production; PostgreSQL ('postgresql+asyncpg://') "
                    "is required."
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def docs_enabled(self) -> bool:
        """OpenAPI /docs and /redoc are enabled only in development and test (`docs/10`)."""
        return self.environment in ("development", "test")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached singleton Settings instance."""
    return Settings()
