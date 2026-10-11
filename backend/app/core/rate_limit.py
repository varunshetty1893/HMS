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


# Global in-memory instance
rate_limiter = SlidingWindowRateLimiter()


def rate_limit_by_ip(
    max_requests: int = 15,
    window_seconds: int = 60,
) -> Callable[[Request], Any]:
    """Dependency factory checking rate limits per client IP."""

    async def _dependency(request: Request) -> None:
        client_host = request.client.host if request.client else "unknown_client"
        # Forwarded IP header support behind reverse proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_host = forwarded_for.split(",")[0].strip()

        key = f"rl:{request.url.path}:{client_host}"
        await rate_limiter.check_and_record(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

    return _dependency
