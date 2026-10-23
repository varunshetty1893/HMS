"""Fail-closed environment guard for development-only seed scripts.

`scripts/seed_dev.py` creates well-known staff accounts (admin / AdminPass123!, ...) and demo
tables. Running it against a real deployment would hand out working credentials, so it must
only ever run in an explicitly allow-listed local environment.

Rules (intentionally strict and NOT configurable):
* Allow-list, not block-list: only ``development`` and ``test`` pass. ``production``,
  ``staging`` and any unexpected value are refused.
* There is no environment variable or CLI flag that bypasses the check.
* The check is pure: it touches no database and no network, so callers can (and must) run it
  BEFORE opening any connection.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

ALLOWED_SEED_ENVIRONMENTS: frozenset[str] = frozenset({"development", "test"})


class SeedBlockedError(RuntimeError):
    """Raised when a development seed is attempted in a non-development environment."""


def assert_dev_seed_allowed(environment: str) -> None:
    """Raise `SeedBlockedError` unless `environment` is explicitly allowed for dev seeding."""
    normalized = (environment or "").strip().lower()
    if normalized in ALLOWED_SEED_ENVIRONMENTS:
        return
    raise SeedBlockedError(
        f"seed_dev.py refuses to run with ENVIRONMENT={environment!r}. "
        "It creates synthetic staff accounts with hardcoded passwords "
        "(admin / AdminPass123!, ...) and demo data, and is allowed only when "
        f"ENVIRONMENT is one of: {', '.join(sorted(ALLOWED_SEED_ENVIRONMENTS))}. "
        "There is no override. To bootstrap a real deployment use "
        "backend/scripts/init_production.py."
    )


class _EnvironmentOnly(BaseSettings):
    """Reads ONLY `ENVIRONMENT` (process env + `.env`, same sources as `app.config.Settings`).

    Full `Settings` validation can fail first in production (e.g. placeholder secrets), which
    would hide the real reason. This lets the guard fire with a clear message before that.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    environment: str = "development"


def read_environment() -> str:
    """Return the raw ENVIRONMENT value without validating the rest of the settings."""
    return _EnvironmentOnly().environment
