"""In-memory sliding-window rate limiter for public endpoints.

Follows `docs/06-security-specification.md` (Section 10) and
`docs/09-testing-and-qa-specification.md` (`RATE-T02`).
"""

from __future__ import annotations

import asyncio
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


def extract_client_ip(request: Request) -> str:
    """Extract client IP securely from headers or connection.

    Behind reverse proxies (Render, Caddy, Cloudflare, Nginx), the proxy appends
    the client IP to X-Forwarded-For (making the last entry the proxy-verified IP)
    or sets X-Real-IP. Using the first entry is dangerous because an untrusted client
    can spoof the header.
    """
    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip and x_real_ip.strip():
        return x_real_ip.strip()

    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]
        if ips:
            # Use the proxy-appended IP (last entry in chain) to prevent spoofing
            return ips[-1]

    if request.client and request.client.host:
        return request.client.host
    return "unknown_client"


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
    """Rate limit keyed on customer session token with fallback to client IP.

    Prevents throttling an entire restaurant of diners sharing one Wi-Fi IP.
    """

    async def _dependency(request: Request) -> None:
        auth_header = request.headers.get("Authorization") or ""
        session_key: str | None = None
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            if token:
                session_key = f"session:{token[:32]}"

        if not session_key:
            client_ip = extract_client_ip(request)
            session_key = f"ip:{client_ip}"

        key = f"rl:{request.url.path}:{session_key}"
        await rate_limiter.check_and_record(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    return _dependency
