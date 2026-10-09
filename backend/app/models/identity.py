"""Staff identity tables: `users`, `staff_refresh_tokens` (`docs/04` Sections 3 and 2.2 #2)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time_utils import utc_now
from app.models.base import Base, CreatedAtMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import UserRole, UserStatus, in_check


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Staff account (`ADMIN`, `WAITER`, `KITCHEN`). Soft-deactivate only; never hard-deleted."""

    __tablename__ = "users"
    __table_args__ = (
        Index("uq_users_username_lower", text("lower(username)"), unique=True),
        Index("ix_users_role_is_active", "role", "is_active"),
        CheckConstraint(in_check("role", UserRole), name="role_valid"),
        CheckConstraint(in_check("status", UserStatus), name="status_valid"),
        CheckConstraint("failed_login_attempts >= 0", name="failed_login_attempts_non_negative"),
    )

    username: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Argon2id hash string (salt + params included). Plaintext is never stored.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UserStatus.ACTIVE.value, server_default="ACTIVE"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    # `docs/13` Section 12: access-token invalidation counter (extra beyond `docs/04`).
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    refresh_tokens: Mapped[list[StaffRefreshToken]] = relationship(
        back_populates="user",
        foreign_keys="StaffRefreshToken.user_id",
    )


class StaffRefreshToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Hashed staff refresh-token session; revocable by Admin (`docs/04` + `docs/13` merged)."""

    __tablename__ = "staff_refresh_tokens"
    __table_args__ = (
        Index("ix_staff_refresh_tokens_user_id_is_revoked", "user_id", "is_revoked"),
        Index("ix_staff_refresh_tokens_expires_at", "expires_at"),
        CheckConstraint("expires_at > created_at", name="expires_after_created"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    device_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Rotation chain (`docs/13` Sec. 12; `docs/06` refresh rotation and reuse detection): the
    # token this one was rotated into. IP correlation for refresh events lives in
    # `audit_logs.ip_hash` (daily-salted hash), so no IP data is duplicated on this table.
    replaced_by_token_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey(
            "staff_refresh_tokens.id",
            ondelete="RESTRICT",
            name="fk_staff_refresh_tokens_replaced_by_token_id",
        ),
        nullable=True,
    )

    user: Mapped[User] = relationship(back_populates="refresh_tokens", foreign_keys=[user_id])
