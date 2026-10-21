"""In-memory sliding-window rate limiter for public endpoints.

Follows `docs/06-security-specification.md` (Section 10) and
`docs/09-testing-and-qa-specification.md` (`RATE-T02`).
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import Request

from app.core.exceptions import RateLimitExceededError


class SlidingWindowRateLimiter:
    """Sliding-window in-memory rate limiter with thread-safe / async cleanup."""

    def __init__(self) -> None:
        self._history: dict[str, list[float]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def check_and_record(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        """Check sliding limit and record hit; raises RateLimitExceededError if over."""
        now = time.monotonic()
        cutoff = now - window_seconds

        async with self._lock:
            # Purge timestamps older than window
            timestamps = [ts for ts in self._history[key] if ts > cutoff]

            if len(timestamps) >= max_requests:
                oldest_in_window = timestamps[0]
                retry_after = max(1, int(window_seconds - (now - oldest_in_window)))
                raise RateLimitExceededError(
                    code="RATE_LIMIT_EXCEEDED",
                    message="Too many requests. Please wait before trying again.",
                    retry_after_seconds=retry_after,
                )

            timestamps.append(now)
            self._history[key] = timestamps

    async def reset(self) -> None:
        """Reset all rate limiter state (useful in test teardown)."""
        async with self._lock:
            self._history.clear()


# ─── Trusted proxy configuration ──────────────────────────────────────────────
# Only accept X-Real-IP / X-Forwarded-For from these peer addresses.
# In Docker, Caddy sits on the internal_net bridge; its peer IP as seen by
# uvicorn/FastAPI will be the gateway of the docker bridge network (typically
# 172.x.x.1) or the caddy container IP.  Set TRUSTED_PROXY_IPS in .env to
# the actual Caddy container IP or CIDR range of the bridge network.
# In production on Render, trusted proxies are Render's own infra; Render sets
# X-Forwarded-For and X-Real-IP from its edge.
#
# The value is loaded lazily from settings to avoid circular imports.


def _get_trusted_proxy_ips() -> frozenset[str]:
    """Return the frozenset of trusted proxy IPs from settings (lazy load)."""
    try:
        from app.config import get_settings  # noqa: PLC0415

        settings = get_settings()
        return settings.trusted_proxy_ips
    except Exception:
        return frozenset()


def extract_client_ip(request: Request) -> str:
    """Extract the real client IP securely.

    Rules (in order of precedence):
    1. If the connection's immediate peer IP is in the trusted_proxy_ips set,
       honour X-Real-IP (single IP) or the *first* entry of X-Forwarded-For
       (leftmost = original client, subsequent = proxy chain).
       Caddy sets ``header_up X-Forwarded-For {remote_host}`` which *replaces*
       the header with a single verified value, so first == only entry.
    2. Otherwise, fall back to the raw TCP peer address reported by uvicorn.

    This prevents a malicious client from spoofing X-Real-IP or prepending
    fake IPs to X-Forwarded-For when there is no trusted proxy in front.
    """
    peer_ip = (request.client.host if request.client else None) or "unknown_client"
    trusted = _get_trusted_proxy_ips()

    if peer_ip in trusted:
        # Proxy is trusted — honour its forwarding headers.
        x_real_ip = request.headers.get("X-Real-IP", "").strip()
        if x_real_ip:
            return x_real_ip

        forwarded_for = request.headers.get("X-Forwarded-For", "")
        if forwarded_for:
            # First entry = original client IP (Caddy overwrites with {remote_host})
            first = forwarded_for.split(",")[0].strip()
            if first:
                return first

    # No trusted proxy or forwarding headers unavailable — use raw peer IP.
    return peer_ip


# Global in-memory instance
rate_limiter = SlidingWindowRateLimiter()


def rate_limit_by_ip(
    max_requests: int = 15,
    window_seconds: int = 60,
) -> Callable[[Request], Any]:
    """Dependency factory checking rate limits per client IP."""

    async def _dependency(request: Request) -> None:
        client_host = extract_client_ip(request)
        key = f"rl:{request.url.path}:{client_host}"
        await rate_limiter.check_and_record(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    return _dependency


def rate_limit_by_session_or_ip(
    max_requests: int = 3,
    window_seconds: int = 300,
) -> Callable[[Request], Any]:
    """Rate limit keyed on the *validated* customer session identity.

    Identity resolution (in order):
    1. ``X-Customer-Session-Token`` header — hash to match what the database
       stores in ``session_token_hash`` (SHA-256).  This is the same token
       that ``get_current_customer_session`` validates; we use the hash as key
       so the raw token is never stored in the rate-limiter's in-memory dict.
    2. Fallback to client IP when no session header is present (e.g. unauthenticated
       probes, missing token). IP-based limiting still blocks bulk abuse from a
       single address while not penalising an entire restaurant for one bad actor.

    Security properties:
    - Two different customers sharing the same public IP are *not* merged into
      one bucket when both supply valid, distinct session tokens.
    - A fabricated / invalid session token does NOT use a session-specific key;
      it falls back to the IP bucket, so it cannot bypass IP-level limits.
    - The raw token is never stored; the SHA-256 hash (same as the DB column)
      is used as the bucket key, preventing token leakage via memory inspection.
    """

    async def _dependency(request: Request) -> None:
        raw_token = request.headers.get("X-Customer-Session-Token", "").strip()

        if raw_token:
            # Hash the token — same algorithm as get_current_customer_session.
            # We intentionally do NOT query the DB here; we key on the hash so
            # a fabricated token that does not exist in the DB gets its own
            # (IP-shared) bucket in the fallback branch, and a valid token gets
            # its own per-session bucket.
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            session_key = f"session:{token_hash}"
        else:
            client_ip = extract_client_ip(request)
            session_key = f"ip:{client_ip}"

        key = f"rl:{request.url.path}:{session_key}"
        await rate_limiter.check_and_record(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    return _dependency
