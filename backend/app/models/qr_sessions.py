"""QR tokens and sessions: `table_qr_tokens`, `table_sessions`, `customer_sessions`.

`table_sessions` <-> `customer_sessions` reference each other (`docs/04` Sections 6-7), so
`table_sessions.opened_by_customer_session_id` is created with `use_alter=True` (added after
both tables exist) to keep the migration order valid without hiding a broken relationship.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time_utils import utc_now
from app.models.base import (
    Base,
    CreatedAtMixin,
    UpdatedAtMixin,
    UUIDPrimaryKeyMixin,
    money,
    uuid_fk,
)
from app.models.enums import (
    CustomerSessionStatus,
    OrderSource,
    QrTokenStatus,
    TableSessionStatus,
    in_check,
)
from app.models.restaurant import RestaurantTable

if TYPE_CHECKING:
    from app.models.billing import Bill
    from app.models.orders import Order


class TableQrToken(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Current and historical QR tokens per table.

    The raw 256-bit token is NEVER stored. Lookup uses `token_hash` (SHA-256 hex);
    `printable_token_ciphertext` holds the token encrypted (Fernet/AES-GCM) solely so Admin can
    re-render the printable QR card (`docs/04` Section 5.1).
    """

    __tablename__ = "table_qr_tokens"
    __table_args__ = (
        UniqueConstraint("table_id", "token_version", name="uq_table_qr_tokens_table_id_version"),
        Index(
            "uq_qr_tokens_one_active_per_table",
            "table_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        CheckConstraint(in_check("status", QrTokenStatus), name="status_valid"),
        CheckConstraint("token_version >= 1", name="token_version_positive"),
    )

    table_id: Mapped[uuid.UUID] = uuid_fk("restaurant_tables.id", nullable=False)
    token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    token_prefix: Mapped[str] = mapped_column(String(10), nullable=False)
    printable_token_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = uuid_fk("users.id", nullable=False)
    activated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    revoked_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    table: Mapped[RestaurantTable] = relationship(back_populates="qr_tokens")
    customer_sessions: Mapped[list[CustomerSession]] = relationship(back_populates="qr_token")


class TableSession(UUIDPrimaryKeyMixin, UpdatedAtMixin, Base):
    """One dining visit at a table; anchor of orders, bill, payment and the unpaid-exposure cap.

    `current_outstanding_amount` and `custom_outstanding_limit` are stored so a future service
    can recompute and enforce the (configurable) limit under `SELECT ... FOR UPDATE` on this
    row. The limit value itself is data, not a hardcoded DB constraint.
    """

    __tablename__ = "table_sessions"
    __table_args__ = (
        Index(
            "uq_table_sessions_one_open_per_table",
            "table_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
        Index("ix_table_sessions_status_started_at", "status", text("started_at DESC")),
        CheckConstraint(in_check("status", TableSessionStatus), name="status_valid"),
        CheckConstraint(in_check("opened_by_source", OrderSource), name="opened_by_source_valid"),
        CheckConstraint("current_outstanding_amount >= 0", name="outstanding_non_negative"),
        CheckConstraint("custom_outstanding_limit > 0", name="outstanding_limit_positive"),
    )

    session_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    table_id: Mapped[uuid.UUID] = uuid_fk("restaurant_tables.id", nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    opened_by_source: Mapped[str] = mapped_column(String(20), nullable=False)
    opened_by_customer_session_id: Mapped[uuid.UUID | None] = uuid_fk(
        "customer_sessions.id",
        nullable=True,
        use_alter=True,
        name="fk_table_sessions_opened_by_customer_session_id",
    )
    opened_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    current_outstanding_amount: Mapped[Decimal] = mapped_column(
        money(), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    custom_outstanding_limit: Mapped[Decimal] = mapped_column(
        money(), nullable=False, default=Decimal("5000.00"), server_default=text("5000.00")
    )
    limit_override_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    limit_override_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_locked_for_abuse: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    closed_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    table: Mapped[RestaurantTable] = relationship(back_populates="table_sessions")
    customer_sessions: Mapped[list[CustomerSession]] = relationship(
        back_populates="table_session",
        foreign_keys="CustomerSession.table_session_id",
    )
    orders: Mapped[list[Order]] = relationship(back_populates="table_session")
    bills: Mapped[list[Bill]] = relationship(back_populates="table_session")


class CustomerSession(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Anonymous browser session created by a QR scan; bearer token stored only as a hash."""

    __tablename__ = "customer_sessions"
    __table_args__ = (
        Index("ix_customer_sessions_table_id_status", "table_id", "status"),
        Index("ix_customer_sessions_table_session_id_status", "table_session_id", "status"),
        CheckConstraint(in_check("status", CustomerSessionStatus), name="status_valid"),
    )

    table_id: Mapped[uuid.UUID] = uuid_fk("restaurant_tables.id", nullable=False)
    qr_token_id: Mapped[uuid.UUID] = uuid_fk("table_qr_tokens.id", nullable=False)
    table_session_id: Mapped[uuid.UUID | None] = uuid_fk("table_sessions.id", nullable=True)
    session_token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(25), nullable=False)
    client_fingerprint_hash: Mapped[str | None] = mapped_column(CHAR(64), nullable=True)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    table: Mapped[RestaurantTable] = relationship(back_populates="customer_sessions")
    qr_token: Mapped[TableQrToken] = relationship(back_populates="customer_sessions")
    table_session: Mapped[TableSession | None] = relationship(
        back_populates="customer_sessions",
        foreign_keys=[table_session_id],
    )
    orders: Mapped[list[Order]] = relationship(back_populates="customer_session")
