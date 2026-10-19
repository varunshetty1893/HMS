"""WaiterRequest model — customer-initiated waiter-call with atomic single-claim semantics.

Designed per `docs/04-database-design.md` Section 2.2 patterns:
- status transitions: PENDING → CLAIMED → COMPLETED
                       PENDING → CANCELLED
                       PENDING/CLAIMED → EXPIRED (system-set)
- Only ONE waiter can claim a request (enforced by SELECT FOR UPDATE in service layer).
- Linked to a valid, ACTIVE CustomerSession so authorization is checked server-side.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time_utils import utc_now
from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin, uuid_fk
from app.models.enums import WaiterRequestReason, WaiterRequestStatus, in_check


class WaiterRequest(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A customer's call-waiter request for a table session.

    Uniqueness invariant: at most one PENDING or CLAIMED request per table_session_id at a time
    (enforced by partial unique index). This prevents duplicate simultaneous calls.
    """

    __tablename__ = "waiter_requests"
    __table_args__ = (
        # Only one open (PENDING or CLAIMED) request per table session at a time.
        Index(
            "uq_waiter_requests_one_open_per_table_session",
            "table_session_id",
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'CLAIMED')"),
        ),
        Index("ix_waiter_requests_table_session_status", "table_session_id", "status"),
        Index("ix_waiter_requests_status_created_at", "status", text("created_at DESC")),
        CheckConstraint(in_check("status", WaiterRequestStatus), name="status_valid"),
        CheckConstraint(in_check("reason", WaiterRequestReason), name="reason_valid"),
    )

    # ── Foreign keys ──────────────────────────────────────────────────────────
    customer_session_id: Mapped[uuid.UUID] = uuid_fk("customer_sessions.id", nullable=False)
    table_session_id: Mapped[uuid.UUID] = uuid_fk("table_sessions.id", nullable=False)
    table_id: Mapped[uuid.UUID] = uuid_fk("restaurant_tables.id", nullable=False)

    # ── Request payload ───────────────────────────────────────────────────────
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=WaiterRequestStatus.PENDING.value,
        server_default=text("'PENDING'"),
    )
    claimed_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        # Default 15 minutes; set in service layer using utc_now() + timedelta
        default=utc_now,
        server_default=func.now() + text("INTERVAL '15 minutes'"),
    )

    def __repr__(self) -> str:
        return (
            f"<WaiterRequest id={self.id} table_session={self.table_session_id} "
            f"reason={self.reason} status={self.status}>"
        )
