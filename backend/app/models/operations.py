"""Operational tables: `idempotency_keys`, `notifications`, `audit_logs` (`docs/04` 2.2 #17-19)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time_utils import utc_now
from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, uuid_fk
from app.models.enums import ActorRole, NotificationChannel, NotificationSeverity, in_check


class IdempotencyKey(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Cached responses for state-mutating POSTs; pruned after `expires_at` (24h)."""

    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "idempotency_key", "actor_scope", name="uq_idempotency_keys_key_actor_scope"
        ),
        Index("ix_idempotency_keys_expires_at", "expires_at"),
        CheckConstraint("expires_at > created_at", name="expires_after_created"),
    )

    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_scope: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint_path: Mapped[str] = mapped_column(String(200), nullable=False)
    request_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    response_status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Notification(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Persisted operational alert so reconnecting devices can recover missed events."""

    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "ix_notifications_channel_ack_created_at",
            "target_channel",
            "is_acknowledged",
            text("created_at DESC"),
        ),
        Index(
            "ix_notifications_table_session_id_created_at",
            "table_session_id",
            text("created_at DESC"),
        ),
        CheckConstraint(in_check("target_channel", NotificationChannel), name="channel_valid"),
        CheckConstraint(in_check("severity", NotificationSeverity), name="severity_valid"),
    )

    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    target_channel: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    payload_json: Mapped[Any] = mapped_column(JSONB, nullable=False)
    requires_acknowledgment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_acknowledged: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    table_id: Mapped[uuid.UUID | None] = uuid_fk("restaurant_tables.id", nullable=True)
    table_session_id: Mapped[uuid.UUID | None] = uuid_fk("table_sessions.id", nullable=True)
    order_id: Mapped[uuid.UUID | None] = uuid_fk("orders.id", nullable=True)
    target_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    acknowledged_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(UUIDPrimaryKeyMixin, Base):
    """Immutable audit trail. UPDATE/DELETE are blocked by trigger `trg_prevent_audit_log_mutation`
    (created in the initial Alembic migration, `docs/04` Section 22 and `docs/13` Phase 2).
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_created_at", text("created_at DESC")),
        Index("ix_audit_logs_entity", "entity_type", "entity_id", text("created_at DESC")),
        Index("ix_audit_logs_actor_user_id_created_at", "actor_user_id", text("created_at DESC")),
        Index("ix_audit_logs_action_type_created_at", "action_type", text("created_at DESC")),
        CheckConstraint(in_check("actor_role", ActorRole), name="actor_role_valid"),
    )

    actor_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    actor_customer_session_id: Mapped[uuid.UUID | None] = uuid_fk(
        "customer_sessions.id", nullable=True
    )
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    action_type: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    # String (not UUID) because `restaurant_settings.id` is an integer singleton.
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    old_value_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    new_value_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
    ip_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
