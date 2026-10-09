"""Timezone-aware UTC timestamp helpers (`docs/11` Section 22)."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    """Return the current UTC timestamp formatted as ISO-8601 with trailing 'Z'."""
    return utc_now().strftime("%Y-%m-%dT%H:%M:%SZ")
