"""Staff management service for user creation, credential administration, and revocation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError, StateConflictError
from app.core.security import hash_password
from app.core.time_utils import utc_now
from app.models.enums import ActorRole, UserRole, UserStatus
from app.models.identity import StaffRefreshToken, User
from app.realtime.manager import ws_manager
from app.schemas.staff import (
    StaffPasswordResetRequest,
    StaffUserAdminResponse,
    StaffUserCreate,
    StaffUserUpdate,
)
from app.services.audit_service import AuditService


class StaffService:
    """Administrative service for staff user accounts."""

    @classmethod
    async def list_users(
        cls,
        db: AsyncSession,
        role: UserRole | None = None,
        active_only: bool = False,
    ) -> list[StaffUserAdminResponse]:
        """List staff accounts ordered by creation date."""
        stmt = select(User).order_by(User.created_at.desc())
        if role:
            stmt = stmt.where(User.role == role.value)
        if active_only:
            stmt = stmt.where(User.is_active.is_(True))

        users = (await db.scalars(stmt)).all()
        return [StaffUserAdminResponse.model_validate(u) for u in users]

    @classmethod
    async def get_user(cls, db: AsyncSession, user_id: uuid.UUID) -> User:
        """Fetch a single staff user by ID."""
        user = await db.get(User, user_id)
        if not user:
            raise ResourceNotFoundError("USER_NOT_FOUND", f"Staff user {user_id} not found.")
        return user

    @classmethod
    async def create_user(
        cls,
        db: AsyncSession,
        payload: StaffUserCreate,
        admin_user: User,
    ) -> StaffUserAdminResponse:
        """Create a new staff account with Argon2id password hashing."""
        uname = payload.username.strip().lower()

        # Check unique username
        existing = await db.scalar(
            select(User).where(func.lower(User.username) == uname)
        )
        if existing:
            raise StateConflictError(
                "USERNAME_ALREADY_EXISTS",
                f"A staff account with username '{payload.username}' already exists.",
            )

        hashed = await hash_password(payload.password)
        now = utc_now()

        user = User(
            username=payload.username.strip(),
            full_name=payload.full_name.strip(),
            password_hash=hashed,
            role=payload.role.value,
            status=UserStatus.ACTIVE.value,
            is_active=True,
            failed_login_attempts=0,
            token_version=1,
            password_changed_at=now,
            created_by_user_id=admin_user.id,
        )
        db.add(user)
        await db.flush()

        await AuditService.record_event(
            db,
            action_type="STAFF_USER_CREATED",
            entity_type="USER",
            entity_id=str(user.id),
            actor_role=ActorRole.ADMIN,
            actor_user_id=admin_user.id,
            reason=f"Created {payload.role.value} account for {payload.username}",
            new_value={"username": user.username, "role": user.role},
        )

        return StaffUserAdminResponse.model_validate(user)

    @classmethod
    async def update_user(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: StaffUserUpdate,
        admin_user: User,
    ) -> StaffUserAdminResponse:
        """Update staff parameters, role, or deactivate immediately."""
        user = await cls.get_user(db, user_id)

        # Safety: an admin must not be able to lock themselves out of the system.
        if user.id == admin_user.id:
            wants_disable = payload.is_active is False or (
                payload.status is not None and payload.status != UserStatus.ACTIVE
            )
            wants_role_change = payload.role is not None and payload.role.value != user.role
            if wants_disable or wants_role_change:
                raise StateConflictError(
                    "CANNOT_MODIFY_SELF",
                    "You cannot disable your own account or change your own role.",
                )

        old_state = {
            "full_name": user.full_name,
            "role": user.role,
            "status": user.status,
            "is_active": user.is_active,
        }

        if payload.full_name is not None:
            user.full_name = payload.full_name.strip()
        if payload.role is not None:
            user.role = payload.role.value
        if payload.status is not None:
            user.status = payload.status.value
        if payload.is_active is not None:
            user.is_active = payload.is_active
            if not payload.is_active:
                user.status = UserStatus.DISABLED.value
            elif payload.status is None and user.status == UserStatus.DISABLED.value:
                # Reactivation must also lift the DISABLED status, otherwise login stays blocked.
                user.status = UserStatus.ACTIVE.value

        # If deactivated or locked, revoke tokens and disconnect WebSockets
        if not user.is_active or user.status == UserStatus.DISABLED.value:
            user.token_version += 1
            now = datetime.now(timezone.utc)
            rev_stmt = (
                update(StaffRefreshToken)
                .where(
                    StaffRefreshToken.user_id == user.id,
                    StaffRefreshToken.is_revoked.is_(False),
                )
                .values(is_revoked=True, revoked_at=now, revoked_reason="USER_DEACTIVATED")
            )
            await db.execute(rev_stmt)
            await ws_manager.disconnect_user(user.id, close_code=1008, reason="ACCOUNT_DISABLED")

        await AuditService.record_event(
            db,
            action_type="STAFF_USER_UPDATED",
            entity_type="USER",
            entity_id=str(user.id),
            actor_role=ActorRole.ADMIN,
            actor_user_id=admin_user.id,
            old_value=old_state,
            new_value={
                "full_name": user.full_name,
                "role": user.role,
                "status": user.status,
                "is_active": user.is_active,
            },
        )

        return StaffUserAdminResponse.model_validate(user)

    @classmethod
    async def reset_password(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        payload: StaffPasswordResetRequest,
        admin_user: User,
    ) -> StaffUserAdminResponse:
        """Reset staff password, invalidate existing tokens, and disconnect sessions."""
        user = await cls.get_user(db, user_id)

        hashed = await hash_password(payload.new_password)
        now = utc_now()

        user.password_hash = hashed
        user.password_changed_at = now
        user.token_version += 1
        user.failed_login_attempts = 0
        user.locked_until = None
        if user.status == UserStatus.LOCKED.value:
            user.status = UserStatus.ACTIVE.value

        rev_stmt = (
            update(StaffRefreshToken)
            .where(
                StaffRefreshToken.user_id == user.id,
                StaffRefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now, revoked_reason="PASSWORD_RESET")
        )
        await db.execute(rev_stmt)
        await ws_manager.disconnect_user(user.id, close_code=1008, reason="PASSWORD_RESET")

        await AuditService.record_event(
            db,
            action_type="STAFF_PASSWORD_RESET",
            entity_type="USER",
            entity_id=str(user.id),
            actor_role=ActorRole.ADMIN,
            actor_user_id=admin_user.id,
            reason="Admin password reset",
        )

        return StaffUserAdminResponse.model_validate(user)

    @classmethod
    async def unlock_user(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        admin_user: User,
    ) -> StaffUserAdminResponse:
        """Clear lockout counter and lift time-based lockout."""
        user = await cls.get_user(db, user_id)

        user.failed_login_attempts = 0
        user.locked_until = None
        if user.status == UserStatus.LOCKED.value:
            user.status = UserStatus.ACTIVE.value

        await AuditService.record_event(
            db,
            action_type="STAFF_USER_UNLOCKED",
            entity_type="USER",
            entity_id=str(user.id),
            actor_role=ActorRole.ADMIN,
            actor_user_id=admin_user.id,
            reason="Admin unlocked user account",
        )

        return StaffUserAdminResponse.model_validate(user)
