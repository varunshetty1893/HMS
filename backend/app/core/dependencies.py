"""FastAPI dependencies for authentication, role-based authorization (RBAC), and session scoping.

Follows `docs/05-api-specification.md` (Section 4) and
`docs/06-security-specification.md` (Sections 3 & 5).
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable

import jwt
from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import decode_access_token
from app.core.time_utils import utc_now
from app.models.enums import CustomerSessionStatus, UserRole, UserStatus
from app.models.identity import User
from app.models.qr_sessions import CustomerSession

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False,
)


async def get_current_staff_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate Bearer access token and return the active User entity.

    Enforces token expiration, cryptographic signature, account active status,
    and token version invalidation.
    """
    if not token:
        # Also check Authorization header directly if oauth2_scheme missed it
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if not token:
        raise AuthenticationError(
            code="UNAUTHORIZED",
            message="Authentication credentials were not provided.",
        )

    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError as err:
        raise AuthenticationError(
            code="ACCESS_TOKEN_EXPIRED",
            message="Access token has expired. Please refresh your session.",
        ) from err
    except jwt.PyJWTError as err:
        raise AuthenticationError(
            code="INVALID_TOKEN",
            message="Access token is malformed or invalid.",
        ) from err

    sub = payload.get("sub")
    if not sub:
        raise AuthenticationError(
            code="INVALID_TOKEN",
            message="Token payload is missing subject claim.",
        )

    try:
        user_uuid = uuid.UUID(sub)
    except ValueError as err:
        raise AuthenticationError(
            code="INVALID_TOKEN",
            message="Token subject is not a valid UUID.",
        ) from err

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise AuthenticationError(
            code="USER_NOT_FOUND",
            message="User associated with this token does not exist.",
        )

    # Invalidate token if token_version was incremented on user deactivation/password reset
    if payload.get("token_version") != user.token_version:
        raise AuthenticationError(
            code="TOKEN_REVOKED",
            message="Session has been revoked due to credential changes.",
        )

    # Immediately reject disabled or locked accounts (docs/06 Section 3.2 #4)
    if not user.is_active or user.status != UserStatus.ACTIVE.value:
        raise AuthorizationError(
            code="ACCOUNT_DISABLED",
            message="Staff account is disabled or locked.",
        )

    return user


def require_roles(*allowed_roles: str | UserRole) -> Callable[[User], User]:
    """Dependency factory that verifies current staff member belongs to an allowed role.

    Supports UserRole enum or raw strings ('ADMIN', 'WAITER', 'KITCHEN').
    """
    role_strings = [r.value if isinstance(r, UserRole) else str(r) for r in allowed_roles]

    def _role_checker(current_user: User = Depends(get_current_staff_user)) -> User:
        if current_user.role not in role_strings:
            raise AuthorizationError(
                code="INSUFFICIENT_ROLE_PERMISSIONS",
                message="You do not have permission to perform this action.",
                details={
                    "required_roles": role_strings,
                    "user_role": current_user.role,
                },
            )
        return current_user

    return _role_checker


async def get_current_customer_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> CustomerSession:
    """Validate X-Customer-Session-Token and return the active CustomerSession entity.

    Follows `docs/05-api-specification.md` (Section 4) and
    `docs/06-security-specification.md` (Section 4).
    """
    token = request.headers.get("X-Customer-Session-Token")
    if not token or not token.strip():
        raise AuthenticationError(
            code="UNAUTHORIZED",
            message="Customer session token was not provided.",
        )

    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    stmt = (
        select(CustomerSession)
        .options(selectinload(CustomerSession.table))
        .where(CustomerSession.session_token_hash == token_hash)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise AuthenticationError(
            code="INVALID_TOKEN",
            message="Customer session token is invalid.",
        )

    if session.status != CustomerSessionStatus.ACTIVE.value:
        raise AuthenticationError(
            code="SESSION_REVOKED",
            message="Customer session is no longer active.",
        )

    now = utc_now()
    if session.expires_at < now:
        raise AuthenticationError(
            code="SESSION_EXPIRED",
            message="Customer session has expired. Please rescan the table QR code.",
        )

    # Touch session last_seen_at
    session.last_seen_at = now
    return session
