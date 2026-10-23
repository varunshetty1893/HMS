"""Staff authentication service implementing Argon2id verification, lockout, and token rotation.

Follows `docs/05-api-specification.md` (Section 3),
`docs/06-security-specification.md` (Sections 3 & 4), and
`docs/11-project-structure-and-coding-standards.md` (Section 16).
"""

from __future__ import annotations

import hmac
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import (
    AccountLockedError,
    AuthenticationError,
    AuthorizationError,
    DomainValidationError,
)
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.enums import UserRole, UserStatus
from app.models.identity import StaffRefreshToken, User
from app.realtime.manager import ws_manager
from app.schemas.auth import (
    AdminRecoveryResetRequest,
    StaffChangePasswordRequest,
    StaffLoginRequest,
    StaffLogoutRequest,
    StaffRefreshTokenRequest,
    StaffTokenResponse,
    StaffUserResponse,
)
from app.services.audit_service import AuditService

MAX_FAILED_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


class AuthService:
    """Authoritative service for staff credential validation and session token lifecycle."""

    @classmethod
    async def login(
        cls,
        db: AsyncSession,
        request: StaffLoginRequest,
        client_ip: str | None = None,
    ) -> StaffTokenResponse:
        """Authenticate staff credentials and issue access + refresh token."""
        now = datetime.now(timezone.utc)

        # 1. Look up user by case-insensitive username (docs/04 Section 3)
        stmt = select(User).where(func.lower(User.username) == func.lower(request.username.strip()))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        # 2. Timing attack mitigation: if user not found, perform dummy Argon2 verification
        if not user:
            await verify_password(request.password, DUMMY_PASSWORD_HASH)
            await AuditService.record_event(
                db,
                action_type="STAFF_LOGIN_FAILED",
                entity_type="USER",
                entity_id="UNKNOWN",
                reason="Invalid credentials",
                client_ip=client_ip,
            )
            await db.commit()
            raise AuthenticationError(
                code="INVALID_CREDENTIALS",
                message="Invalid username or password.",
            )

        # 3. Check brute-force lockout status
        if user.locked_until and user.locked_until > now:
            seconds_remaining = int((user.locked_until - now).total_seconds())
            raise AccountLockedError(
                code="ACCOUNT_LOCKED",
                message=(
                    "Account is temporarily locked due to multiple failed login attempts. "
                    "Please try again later."
                ),
                locked_until_iso=user.locked_until.isoformat(),
                retry_after_seconds=max(seconds_remaining, 1),
            )

        # 3b. Lockout window has expired — auto-recover from temporary lockout.
        #     Only clears status when it was set to LOCKED by the brute-force counter
        #     (i.e. locked_until is set). Admin-disabled accounts have status=DISABLED
        #     and locked_until=None so they are never auto-recovered here.
        if (
            user.status == UserStatus.LOCKED.value
            and user.locked_until
            and user.locked_until <= now
        ):
            user.status = UserStatus.ACTIVE.value
            user.failed_login_attempts = 0
            user.locked_until = None

        # 4. Verify Argon2id password BEFORE any role or client-type checks.
        #    Checking client_type before the password would allow an attacker to distinguish
        #    "unknown user" (401) from "wrong client for this role" (403) without knowing the
        #    password, leaking both username existence and role (username enumeration).
        is_password_valid = await verify_password(request.password, user.password_hash)
        if not is_password_valid:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= MAX_FAILED_LOGIN_ATTEMPTS:
                user.status = UserStatus.LOCKED.value
                user.locked_until = now + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                await AuditService.record_event(
                    db,
                    action_type="STAFF_ACCOUNT_LOCKED",
                    entity_type="USER",
                    entity_id=str(user.id),
                    actor_user_id=user.id,
                    actor_role=user.role,
                    reason=f"{MAX_FAILED_LOGIN_ATTEMPTS} consecutive failed login attempts",
                    client_ip=client_ip,
                )
                await db.commit()
                raise AccountLockedError(
                    code="ACCOUNT_LOCKED",
                    message=(
                        f"Account has been locked for {LOCKOUT_DURATION_MINUTES} minutes "
                        "due to multiple failed attempts."
                    ),
                    locked_until_iso=user.locked_until.isoformat(),
                    retry_after_seconds=LOCKOUT_DURATION_MINUTES * 60,
                )
            else:
                await AuditService.record_event(
                    db,
                    action_type="STAFF_LOGIN_FAILED",
                    entity_type="USER",
                    entity_id=str(user.id),
                    actor_user_id=user.id,
                    actor_role=user.role,
                    reason="Invalid password",
                    client_ip=client_ip,
                )
                await db.commit()
                raise AuthenticationError(
                    code="INVALID_CREDENTIALS",
                    message="Invalid username or password.",
                )

        # 5. Client-role binding check (docs/06 Section 3.2 #2).
        #    Runs only after the password is proven correct so client_type cannot be used
        #    to enumerate usernames or roles via differential error responses.
        if request.client_type:
            if user.role == UserRole.KITCHEN.value and request.client_type in (
                "ADMIN_WEB",
                "WAITER_APP",
            ):
                raise AuthorizationError(
                    code="ROLE_CLIENT_MISMATCH",
                    message="Kitchen staff cannot log in to the Waiter App or Admin Web Dashboard.",
                )
            if user.role == UserRole.WAITER.value and request.client_type in (
                "ADMIN_WEB",
                "KITCHEN_APP",
            ):
                raise AuthorizationError(
                    code="ROLE_CLIENT_MISMATCH",
                    message="Waiters cannot log in to the Kitchen KDS or Admin Web Dashboard.",
                )

        # 6. Verify active status
        if not user.is_active or user.status != UserStatus.ACTIVE.value:
            raise AuthorizationError(
                code="ACCOUNT_DISABLED",
                message="Staff account is disabled. Please contact an administrator.",
            )

        # 7. Successful login: reset lockout counters and update last login
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now

        # 8. Issue access token and rotatable refresh token
        access_token, expires_in_seconds = create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            token_version=user.token_version,
        )
        raw_refresh_token = generate_refresh_token()
        refresh_token_row = StaffRefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh_token),
            expires_at=now + timedelta(days=7),
            device_label=request.device_label,
        )
        db.add(refresh_token_row)

        await AuditService.record_event(
            db,
            action_type="STAFF_LOGIN_SUCCESS",
            entity_type="USER",
            entity_id=str(user.id),
            actor_user_id=user.id,
            actor_role=user.role,
            client_ip=client_ip,
        )
        await db.commit()
        await db.refresh(user)

        return StaffTokenResponse(
            access_token=access_token,
            refresh_token=raw_refresh_token,
            token_type="Bearer",
            expires_in_seconds=expires_in_seconds,
            user=StaffUserResponse.model_validate(user),
        )

    @classmethod
    async def refresh_tokens(
        cls,
        db: AsyncSession,
        request: StaffRefreshTokenRequest,
        client_ip: str | None = None,
    ) -> StaffTokenResponse:
        """Rotate refresh token and issue a fresh access token."""
        now = datetime.now(timezone.utc)
        incoming_hash = hash_token(request.refresh_token)

        # 1. Look up refresh token by SHA-256 hash
        stmt = select(StaffRefreshToken).where(StaffRefreshToken.token_hash == incoming_hash)
        result = await db.execute(stmt)
        token_row = result.scalar_one_or_none()

        if not token_row or token_row.expires_at <= now:
            raise AuthenticationError(
                code="REFRESH_TOKEN_INVALID_OR_EXPIRED",
                message="Refresh token is invalid or expired.",
            )

        # 2. Token reuse / compromise detection (docs/06 Section 3.2 & docs/13 Section 12)
        if token_row.is_revoked:
            # Revoke all remaining active tokens for this user
            revoke_all_stmt = (
                update(StaffRefreshToken)
                .where(
                    StaffRefreshToken.user_id == token_row.user_id,
                    StaffRefreshToken.is_revoked.is_(False),
                )
                .values(
                    is_revoked=True,
                    revoked_at=now,
                    revoked_reason="REUSE_COMPROMISE",
                )
            )
            await db.execute(revoke_all_stmt)
            await AuditService.record_event(
                db,
                action_type="SUSPICIOUS_REFRESH_TOKEN_REUSE",
                entity_type="REFRESH_TOKEN",
                entity_id=str(token_row.id),
                actor_user_id=token_row.user_id,
                reason="Attempted use of already-revoked refresh token",
                client_ip=client_ip,
            )
            await db.commit()
            await ws_manager.disconnect_user(
                token_row.user_id, close_code=4001, reason="TOKEN_REUSE_REVOCATION"
            )
            raise AuthenticationError(
                code="REFRESH_TOKEN_REUSED",
                message=(
                    "Refresh token has already been revoked. "
                    "All active sessions have been terminated for security."
                ),
            )

        # 3. Verify user status
        user_stmt = select(User).where(User.id == token_row.user_id)
        user_res = await db.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user or not user.is_active or user.status != UserStatus.ACTIVE.value:
            raise AuthorizationError(
                code="ACCOUNT_DISABLED",
                message="Staff account is disabled.",
            )

        # 4. Rotate refresh token (atomic replacement)
        new_raw_refresh = generate_refresh_token()
        new_token_row = StaffRefreshToken(
            user_id=user.id,
            token_hash=hash_token(new_raw_refresh),
            expires_at=now + timedelta(days=7),
            device_label=token_row.device_label,
        )
        db.add(new_token_row)
        await db.flush()

        token_row.is_revoked = True
        token_row.revoked_at = now
        token_row.revoked_reason = "ROTATED"
        token_row.replaced_by_token_id = new_token_row.id

        access_token, expires_in_seconds = create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            token_version=user.token_version,
        )

        await db.commit()

        return StaffTokenResponse(
            access_token=access_token,
            refresh_token=new_raw_refresh,
            token_type="Bearer",
            expires_in_seconds=expires_in_seconds,
            user=StaffUserResponse.model_validate(user),
        )

    @classmethod
    async def logout(
        cls,
        db: AsyncSession,
        user: User,
        request: StaffLogoutRequest | None = None,
        client_ip: str | None = None,
    ) -> None:
        """Revoke refresh token session and disconnect active WebSockets."""
        now = datetime.now(timezone.utc)

        if request and request.refresh_token:
            target_hash = hash_token(request.refresh_token)
            stmt = (
                update(StaffRefreshToken)
                .where(
                    StaffRefreshToken.token_hash == target_hash,
                    StaffRefreshToken.user_id == user.id,
                )
                .values(is_revoked=True, revoked_at=now, revoked_reason="LOGOUT")
            )
            await db.execute(stmt)
        else:
            # Revoke all active tokens for this user on general logout
            stmt = (
                update(StaffRefreshToken)
                .where(
                    StaffRefreshToken.user_id == user.id,
                    StaffRefreshToken.is_revoked.is_(False),
                )
                .values(is_revoked=True, revoked_at=now, revoked_reason="LOGOUT")
            )
            await db.execute(stmt)

        await AuditService.record_event(
            db,
            action_type="STAFF_LOGOUT",
            entity_type="USER",
            entity_id=str(user.id),
            actor_user_id=user.id,
            actor_role=user.role,
            client_ip=client_ip,
        )
        await db.commit()

        # Disconnect any live WebSockets associated with the logging out user
        await ws_manager.disconnect_user(user.id, close_code=1000, reason="LOGGED_OUT")

    # ─────────────────────────────────────────────────────────────────────────
    # Password change / recovery
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    async def _apply_new_password(
        cls,
        db: AsyncSession,
        user: User,
        new_password: str,
        *,
        revoked_reason: str,
    ) -> None:
        """Set a new Argon2id hash, bump token_version and revoke every refresh token."""
        now = datetime.now(timezone.utc)
        user.password_hash = await hash_password(new_password)
        user.password_changed_at = now
        user.token_version += 1
        user.failed_login_attempts = 0
        user.locked_until = None
        if user.status == UserStatus.LOCKED.value:
            user.status = UserStatus.ACTIVE.value
        await db.execute(
            update(StaffRefreshToken)
            .where(
                StaffRefreshToken.user_id == user.id,
                StaffRefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now, revoked_reason=revoked_reason)
        )

    @classmethod
    async def change_password(
        cls,
        db: AsyncSession,
        user: User,
        request: StaffChangePasswordRequest,
        client_ip: str | None = None,
    ) -> None:
        """Self-service password change; signs the user out of every session."""
        if not await verify_password(request.current_password, user.password_hash):
            # 422 (not 401) so the web client does not mistake this for an expired session.
            raise DomainValidationError(
                code="INVALID_CURRENT_PASSWORD",
                message="Current password is incorrect.",
            )
        if request.new_password == request.current_password:
            raise DomainValidationError(
                code="PASSWORD_UNCHANGED",
                message="New password must be different from the current password.",
            )

        await cls._apply_new_password(
            db, user, request.new_password, revoked_reason="PASSWORD_CHANGED"
        )
        await AuditService.record_event(
            db,
            action_type="STAFF_PASSWORD_CHANGED",
            entity_type="USER",
            entity_id=str(user.id),
            actor_user_id=user.id,
            actor_role=user.role,
            client_ip=client_ip,
        )
        await db.commit()
        await ws_manager.disconnect_user(user.id, close_code=1008, reason="PASSWORD_CHANGED")

    @classmethod
    async def admin_recovery_reset(
        cls,
        db: AsyncSession,
        request: AdminRecoveryResetRequest,
        client_ip: str | None = None,
    ) -> None:
        """Break-glass reset for a locked-out ADMIN using the server-side recovery key.

        Disabled unless ``ADMIN_RECOVERY_KEY`` (16+ chars) is configured. Every failure returns
        the same generic error so usernames / roles / feature state cannot be probed.
        """
        configured = (get_settings().admin_recovery_key or "").strip()
        enabled = len(configured) >= 16

        stmt = select(User).where(func.lower(User.username) == func.lower(request.username.strip()))
        user = (await db.execute(stmt)).scalar_one_or_none()

        key_ok = hmac.compare_digest(
            request.recovery_key.encode("utf-8"),
            (configured if enabled else "x" * 16).encode("utf-8"),
        )
        eligible = (
            enabled
            and key_ok
            and user is not None
            and user.role == UserRole.ADMIN.value
            and user.status != UserStatus.DISABLED.value
        )
        if not eligible or user is None:
            await AuditService.record_event(
                db,
                action_type="ADMIN_RECOVERY_RESET_FAILED",
                entity_type="USER",
                entity_id=str(user.id) if user else "unknown",
                client_ip=client_ip,
            )
            await db.commit()
            raise AuthorizationError(
                code="INVALID_RECOVERY",
                message="Invalid username or recovery key.",
            )

        await cls._apply_new_password(
            db, user, request.new_password, revoked_reason="ADMIN_RECOVERY_RESET"
        )
        await AuditService.record_event(
            db,
            action_type="ADMIN_RECOVERY_RESET",
            entity_type="USER",
            entity_id=str(user.id),
            actor_user_id=user.id,
            actor_role=user.role,
            client_ip=client_ip,
        )
        await db.commit()
        await ws_manager.disconnect_user(user.id, close_code=1008, reason="PASSWORD_RESET")

