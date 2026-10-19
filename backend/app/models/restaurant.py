"""Restaurant configuration and physical tables: `restaurant_settings`, `restaurant_tables`."""

from __future__ import annotations

import uuid
from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time_utils import utc_now
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, money, percentage
from app.models.enums import TableOperationalStatus, in_check

if TYPE_CHECKING:
    from app.models.qr_sessions import CustomerSession, TableQrToken, TableSession


def _bool_default(value: bool) -> dict:
    return {"nullable": False, "default": value, "server_default": text(str(value).lower())}


class RestaurantSettings(Base):
    """Singleton configuration row (`id = 1`). Updated in place; changes are audit-logged."""

    __tablename__ = "restaurant_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="singleton_row"),
        CheckConstraint("cgst_percentage >= 0", name="cgst_non_negative"),
        CheckConstraint("sgst_percentage >= 0", name="sgst_non_negative"),
        CheckConstraint("service_charge_percentage >= 0", name="service_charge_non_negative"),
        CheckConstraint(
            "default_session_outstanding_limit > 0", name="default_outstanding_limit_positive"
        ),
        CheckConstraint(
            "waiter_max_discount_percentage >= 0 AND waiter_max_discount_percentage <= 100",
            name="waiter_max_discount_range",
        ),
        CheckConstraint(
            "waiter_max_price_override_percentage >= 0 "
            "AND waiter_max_price_override_percentage <= 100",
            name="waiter_max_price_override_range",
        ),
        CheckConstraint(
            "qr_confirmation_timeout_seconds BETWEEN 30 AND 1800",
            name="qr_confirmation_timeout_range",
        ),
        CheckConstraint(
            "max_pending_qr_confirmations BETWEEN 1 AND 100",
            name="max_pending_qr_confirmations_range",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False, default=1, server_default=text("1")
    )
    restaurant_name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(15), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    currency_code: Mapped[str] = mapped_column(
        String(3), nullable=False, default="INR", server_default="INR"
    )
    currency_symbol: Mapped[str] = mapped_column(
        String(5), nullable=False, default="₹", server_default="₹"
    )
    prices_include_tax: Mapped[bool] = mapped_column(**_bool_default(False))
    cgst_percentage: Mapped[Decimal] = mapped_column(
        percentage(), nullable=False, default=Decimal("2.50"), server_default=text("2.50")
    )
    sgst_percentage: Mapped[Decimal] = mapped_column(
        percentage(), nullable=False, default=Decimal("2.50"), server_default=text("2.50")
    )
    service_charge_percentage: Mapped[Decimal] = mapped_column(
        percentage(), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    allowed_payment_methods_json: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # Configurable per-table-session unpaid exposure cap (default INR 5,000.00). This is a
    # setting, not a hardcoded DB constraint; only `> 0` is enforced.
    default_session_outstanding_limit: Mapped[Decimal] = mapped_column(
        money(), nullable=False, default=Decimal("5000.00"), server_default=text("5000.00")
    )
    is_ordering_enabled: Mapped[bool] = mapped_column(**_bool_default(True))
    opening_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    closing_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # --- Policy switches OD-01..OD-08 (`docs/13` Section 20.1; `docs/04` names win on overlap) ---
    allow_multi_device_per_table: Mapped[bool] = mapped_column(**_bool_default(True))  # OD-01
    allow_customer_cancel_placed: Mapped[bool] = mapped_column(**_bool_default(False))  # OD-02
    allow_waiter_cancel_preparing_item: Mapped[bool] = mapped_column(  # OD-03
        **_bool_default(False)
    )
    allow_kitchen_mark_served: Mapped[bool] = mapped_column(**_bool_default(False))  # OD-04
    kitchen_can_toggle_availability: Mapped[bool] = mapped_column(  # OD-05
        **_bool_default(True)
    )
    limit_includes_estimated_tax: Mapped[bool] = mapped_column(**_bool_default(False))  # OD-06
    apply_outstanding_limit_to_waiter_orders: Mapped[bool] = mapped_column(  # OD-07
        **_bool_default(True)
    )
    waiter_max_discount_percentage: Mapped[Decimal] = mapped_column(  # OD-08
        percentage(), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    # Maximum absolute per-line price movement a waiter may make at bill generation.
    # Administrators are intentionally not capped by this operational setting.
    waiter_max_price_override_percentage: Mapped[Decimal] = mapped_column(
        percentage(), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )

    # QR anti-abuse (threat T-01): a QR order on an empty table waits for a waiter to confirm
    # that guests are really seated before it reaches the kitchen. Quiet venues may turn it off.
    require_waiter_confirmation_for_first_qr_order: Mapped[bool] = mapped_column(
        **_bool_default(True)
    )
    qr_confirmation_timeout_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=180, server_default=text("180")
    )
    # Restaurant-wide ceiling on unconfirmed requests so the confirmation queue cannot be flooded.
    max_pending_qr_confirmations: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15, server_default=text("15")
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
        server_default=func.now(),
    )
    updated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )


class RestaurantTable(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Physical dining table. Occupancy is derived from `table_sessions`, never stored here."""

    __tablename__ = "restaurant_tables"
    __table_args__ = (
        Index("uq_restaurant_tables_display_name_lower", text("lower(display_name)"), unique=True),
        Index("ix_restaurant_tables_is_active_display_order", "is_active", "display_order"),
        CheckConstraint("table_number > 0", name="table_number_positive"),
        CheckConstraint(
            "seating_capacity IS NULL OR seating_capacity > 0", name="seating_capacity_positive"
        ),
        CheckConstraint(
            in_check("operational_status", TableOperationalStatus), name="status_valid"
        ),
    )

    table_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    seating_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor_or_zone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    operational_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TableOperationalStatus.ENABLED.value,
        server_default="ENABLED",
    )
    is_active: Mapped[bool] = mapped_column(**_bool_default(True))
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)

    qr_tokens: Mapped[list[TableQrToken]] = relationship(back_populates="table")
    table_sessions: Mapped[list[TableSession]] = relationship(back_populates="table")
    customer_sessions: Mapped[list[CustomerSession]] = relationship(back_populates="table")
