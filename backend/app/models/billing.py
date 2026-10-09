"""Billing tables: `bills`, `bill_items`, `payments` (`docs/04` Sections 17-18).

Paid bills and completed payments are permanent ledger records: every FK is `RESTRICT`,
nothing cascades. Superseded unpaid bills move to `VOIDED_FOR_REVISION` (service concern).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time_utils import utc_now
from app.models.base import (
    Base,
    CreatedAtMixin,
    UpdatedAtMixin,
    UUIDPrimaryKeyMixin,
    money,
    percentage,
    uuid_fk,
)
from app.models.enums import BillStatus, PaymentMethod, PaymentStatus, in_check
from app.models.orders import OrderItem
from app.models.qr_sessions import TableSession


class Bill(UUIDPrimaryKeyMixin, UpdatedAtMixin, Base):
    __tablename__ = "bills"
    __table_args__ = (
        Index(
            "uq_bills_one_active_per_session",
            "table_session_id",
            unique=True,
            postgresql_where=text("status IN ('ISSUED','PAID')"),
        ),
        Index("ix_bills_status_generated_at", "status", text("generated_at DESC")),
        CheckConstraint(in_check("status", BillStatus), name="status_valid"),
        CheckConstraint("subtotal_amount >= 0", name="subtotal_non_negative"),
        CheckConstraint(
            "discount_amount >= 0 AND discount_amount <= subtotal_amount", name="discount_in_range"
        ),
        CheckConstraint(
            "discount_amount = 0 OR discount_reason IS NOT NULL", name="discount_reason_required"
        ),
        CheckConstraint(
            "taxable_amount = subtotal_amount - discount_amount", name="taxable_matches"
        ),
        CheckConstraint("cgst_amount >= 0", name="cgst_non_negative"),
        CheckConstraint("sgst_amount >= 0", name="sgst_non_negative"),
        CheckConstraint("service_charge_amount >= 0", name="service_charge_non_negative"),
        CheckConstraint("grand_total >= 0", name="grand_total_non_negative"),
    )

    bill_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    table_session_id: Mapped[uuid.UUID] = uuid_fk("table_sessions.id", nullable=False)
    table_id: Mapped[uuid.UUID] = uuid_fk("restaurant_tables.id", nullable=False)
    status: Mapped[str] = mapped_column(String(25), nullable=False)
    subtotal_amount: Mapped[Decimal] = mapped_column(money(), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(
        money(), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    discount_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    discount_approved_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    taxable_amount: Mapped[Decimal] = mapped_column(money(), nullable=False)
    cgst_rate_snapshot: Mapped[Decimal] = mapped_column(percentage(), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(money(), nullable=False)
    sgst_rate_snapshot: Mapped[Decimal] = mapped_column(percentage(), nullable=False)
    sgst_amount: Mapped[Decimal] = mapped_column(money(), nullable=False)
    service_charge_amount: Mapped[Decimal] = mapped_column(
        money(), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    rounding_adjustment: Mapped[Decimal] = mapped_column(
        percentage(), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    grand_total: Mapped[Decimal] = mapped_column(money(), nullable=False)
    generated_by_user_id: Mapped[uuid.UUID] = uuid_fk("users.id", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    voided_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    void_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    table_session: Mapped[TableSession] = relationship(back_populates="bills")
    items: Mapped[list[BillItem]] = relationship(back_populates="bill")
    payments: Mapped[list[Payment]] = relationship(back_populates="bill")


class BillItem(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Frozen invoice line so a bill can always be reproduced exactly."""

    __tablename__ = "bill_items"
    __table_args__ = (
        Index("ix_bill_items_bill_id", "bill_id"),
        CheckConstraint("quantity_billed >= 1", name="quantity_billed_positive"),
        CheckConstraint("unit_price_snapshot >= 0", name="unit_price_snapshot_non_negative"),
        CheckConstraint(
            "line_total = quantity_billed * unit_price_snapshot", name="line_total_matches"
        ),
    )

    bill_id: Mapped[uuid.UUID] = uuid_fk("bills.id", nullable=False)
    order_id: Mapped[uuid.UUID] = uuid_fk("orders.id", nullable=False)
    order_item_id: Mapped[uuid.UUID] = uuid_fk("order_items.id", nullable=False)
    order_number_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    item_code_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    item_name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    variant_code_snapshot: Mapped[str | None] = mapped_column(String(24), nullable=True)
    variant_name_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    unit_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity_billed: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(money(), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(money(), nullable=False)

    bill: Mapped[Bill] = relationship(back_populates="items")
    order_item: Mapped[OrderItem] = relationship(back_populates="bill_items")


class Payment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Manual settlement record (no payment gateway). Append-only; never hard-deleted."""

    __tablename__ = "payments"
    __table_args__ = (
        Index(
            "uq_payments_one_completed_per_bill",
            "bill_id",
            unique=True,
            postgresql_where=text("status = 'COMPLETED'"),
        ),
        Index("ix_payments_bill_id_status", "bill_id", "status"),
        Index(
            "ix_payments_completed_at_payment_method",
            text("completed_at DESC"),
            "payment_method",
            postgresql_where=text("status = 'COMPLETED'"),
        ),
        CheckConstraint(in_check("payment_method", PaymentMethod), name="method_valid"),
        CheckConstraint(in_check("status", PaymentStatus), name="status_valid"),
        CheckConstraint("amount_paid > 0", name="amount_paid_positive"),
    )

    bill_id: Mapped[uuid.UUID] = uuid_fk("bills.id", nullable=False)
    table_session_id: Mapped[uuid.UUID] = uuid_fk("table_sessions.id", nullable=False)
    payment_method: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(money(), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    reference_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    recorded_by_user_id: Mapped[uuid.UUID] = uuid_fk("users.id", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_or_voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_or_void_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    bill: Mapped[Bill] = relationship(back_populates="payments")
