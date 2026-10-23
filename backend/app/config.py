"""Centralized environment configuration and startup validation.

All configuration is loaded via Pydantic BaseSettings from environment variables
or `backend/.env`. No other module may call `os.getenv` or `os.environ` directly.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

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
    # Secret used for daily-keyed HMAC-SHA256 IP pseudonymisation in audit logs.
    # Falls back to jwt_secret_key if not set.  Set a dedicated long random value in production.
    audit_ip_hash_secret: str = Field(
        default="dev_only_audit_ip_hash_secret_do_not_use_in_production_abcdef012345"
    )
    access_token_expire_minutes: int = Field(default=15, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=90)
    # Optional break-glass key that lets a locked-out ADMIN reset their own password from the
    # login page (no email infrastructure needed). Disabled unless set to 16+ characters.
    admin_recovery_key: str | None = Field(default=None)

    # --- Browser refresh-token cookie (opt-in per request via `X-Auth-Transport: cookie`) ---
    # The admin web can keep the refresh token in an httpOnly cookie instead of localStorage.
    # Use "lax"/"strict" when the web app and API share a site (e.g. Vercel rewrite of /api/*);
    # "none" is only for a cross-site deployment and is blocked by Safari/Firefox by default.
    auth_cookie_name: str = Field(default="hms_refresh", min_length=1, max_length=64)
    auth_cookie_samesite: Literal["lax", "strict", "none"] = Field(default="lax")
    # None = Secure in production, not Secure otherwise (plain-http localhost development).
    auth_cookie_secure: bool | None = Field(default=None)

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
    # WebSocket auth: clients send {"type":"auth", ...} as their FIRST frame, so tokens never
    # appear in the URL (proxy/access logs). The legacy ?token= / ?customer_token= query
    # parameters stay accepted while WS_ALLOW_QUERY_TOKEN=true (rollout); set it to false once
    # every client is updated.
    ws_allow_query_token: bool = Field(default=True)
    ws_auth_timeout_seconds: float = Field(default=5.0, ge=1.0, le=30.0)

    # --- Proxy Trust ---
    # Two independent ways to learn the real client IP behind a reverse proxy.
    # Both default to "off": forwarding headers are then NEVER trusted (safe default).
    #
    # TRUSTED_PROXY_IPS: comma-separated / JSON list of exact IPs or CIDR ranges of
    #   proxies with a STABLE peer address (Caddy container / Docker bridge).
    # PROXY_HOPS: number of trusted proxies in front of the app when their IPs are
    #   not stable (Render). X-Forwarded-For is read from the right, so values a
    #   client prepends cannot spoof its IP. Calibrate with
    #   GET /api/v1/admin/diagnostics/client-ip (see docs/12 / FIX8 note).
    trusted_proxy_ips: Annotated[frozenset[str], NoDecode] = Field(default_factory=frozenset)
    proxy_hops: int = Field(default=0, ge=0, le=5)

    # --- Local File Storage ---
    upload_dir: Path = Field(default=Path("./uploads/menu"))
    max_upload_size_bytes: int = Field(default=2_097_152, ge=1024, le=10_485_760)
    # Max body bytes allowed for the image upload endpoint specifically.
    # Must be larger than max_upload_size_bytes to accommodate multipart framing overhead.
    image_upload_max_body_bytes: int = Field(default=3_145_728, ge=1024, le=26_214_400)  # 3 MB

    # --- ImageKit CDN (optional; set IMAGEKIT_PRIVATE_KEY to enable) ---
    # imagekitio v5 SDK: only needs private_key. The CDN delivery URL is returned
    # by the upload API and stored directly in menu_items.image_url.
    imagekit_private_key: str = Field(default="")
    imagekit_upload_folder: str = Field(default="/menu")

    @field_validator("trusted_proxy_ips", mode="before")
    @classmethod
    def parse_trusted_proxy_ips(cls, value: str | list[str] | frozenset[str]) -> frozenset[str]:
        entries: frozenset[str]
        if isinstance(value, frozenset):
            entries = value
        elif isinstance(value, list | set):
            entries = frozenset(str(ip).strip() for ip in value if str(ip).strip())
        elif isinstance(value, str):
            raw = value.strip()
            if not raw:
                entries = frozenset()
            elif raw.startswith("["):
                parsed = json.loads(raw)
                entries = frozenset(str(ip).strip() for ip in parsed if str(ip).strip())
            else:
                entries = frozenset(ip.strip() for ip in raw.split(",") if ip.strip())
        else:
            entries = frozenset()
        # Fail fast on typos: each entry must be an IP address or CIDR range.
        from app.core.client_ip import parse_trusted_networks  # noqa: PLC0415

        try:
            parse_trusted_networks(entries)
        except ValueError as exc:
            raise ValueError(f"TRUSTED_PROXY_IPS contains an invalid IP/CIDR entry: {exc}") from exc
        return entries

    @field_validator("auth_cookie_secure", mode="before")
    @classmethod
    def blank_cookie_secure_means_default(cls, value: object) -> object:
        """`AUTH_COOKIE_SECURE=` (empty) in a .env file means "use the default"."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def auth_cookie_is_secure(self) -> bool:
        """`SameSite=None` requires Secure; otherwise default to Secure in production."""
        if self.auth_cookie_samesite == "none":
            return True
        if self.auth_cookie_secure is not None:
            return self.auth_cookie_secure
        return self.environment == "production"

    @property
    def imagekit_enabled(self) -> bool:
        """True only when the ImageKit private key is configured (imagekitio v5)."""
        return bool(self.imagekit_private_key.strip())

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
                return [str(origin).strip().rstrip("/") for origin in parsed if str(origin).strip()]
            return [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
        return [str(origin).strip().rstrip("/") for origin in value if str(origin).strip()]

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

        # Normalize hosted PostgreSQL provider schemes (Render, Neon, Supabase, Railway)
        if cleaned.startswith("postgres://"):
            cleaned = "postgresql+asyncpg://" + cleaned[len("postgres://") :]
        elif cleaned.startswith("postgresql://") and not cleaned.startswith("postgresql+"):
            cleaned = "postgresql+asyncpg://" + cleaned[len("postgresql://") :]

        # asyncpg does not understand libpq-style query params (sslmode, channel_binding).
        # Translate Neon/Render style URLs so they can be pasted as-is.
        if cleaned.startswith("postgresql+asyncpg://") and "?" in cleaned:
            from urllib.parse import parse_qsl, urlencode

            base, _, query = cleaned.partition("?")
            params = dict(parse_qsl(query, keep_blank_values=True))
            sslmode = params.pop("sslmode", None)
            params.pop("channel_binding", None)
            if sslmode and sslmode != "disable" and "ssl" not in params:
                params["ssl"] = "require" if sslmode in ("require", "prefer", "allow") else sslmode
            cleaned = base + ("?" + urlencode(params) if params else "")

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
