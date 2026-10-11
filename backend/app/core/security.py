"""Cryptographic security utilities for staff authentication.

Implements Argon2id password hashing, JWT access token generation/verification,
and cryptographically secure refresh token generation and hashing.
Follows `docs/06-security-specification.md` (Sections 3 & 4) and
`docs/11-project-structure-and-coding-standards.md`.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from starlette.concurrency import run_in_threadpool

from app.config import get_settings

# Canonical Argon2id parameters (docs/06 Section 4):
# memory_cost=65536 (64 MB), time_cost=3 iterations, parallelism=2, salt_len=16, hash_len=32.
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

# Constant-time dummy hash used when user is not found to prevent username
# enumeration (docs/09 AUTH-T02).
DUMMY_PASSWORD_HASH = _hasher.hash("dummy_password_for_timing_safety_only")

JWT_ALGORITHM = "HS256"


def hash_password_sync(password: str) -> str:
    """Synchronously hash a plaintext password with Argon2id."""
    return _hasher.hash(password)


async def hash_password(password: str) -> str:
    """Asynchronously hash a plaintext password via threadpool (never blocks the event loop)."""
    return await run_in_threadpool(hash_password_sync, password)


def verify_password_sync(plain_password: str, hashed_password: str) -> bool:
    """Synchronously verify a plaintext password against an Argon2id hash."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Asynchronously verify a password via threadpool (never blocks the event loop)."""
    return await run_in_threadpool(verify_password_sync, plain_password, hashed_password)


def generate_refresh_token() -> str:
    """Generate a high-entropy 256-bit URL-safe token (docs/06 Section 3.2)."""
    return f"rt_{secrets.token_urlsafe(32)}"


def hash_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of a raw token string (64 characters)."""
    return hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()


def create_access_token(
    *,
    user_id: uuid.UUID,
    username: str,
    role: str,
    token_version: int,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    """Create a signed HS256 JWT access token.

    Returns a tuple of (token_string, expires_in_seconds).
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expires_at = now + delta
    expires_in_seconds = int(delta.total_seconds())

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "token_version": token_version,
        "jti": str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    return token, expires_in_seconds


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT access token.

    Raises jwt.ExpiredSignatureError or jwt.PyJWTError if invalid.
    """
    settings = get_settings()
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat", "role"]},
    )
