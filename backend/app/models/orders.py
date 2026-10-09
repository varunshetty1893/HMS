"""Ordering tables: `orders`, `order_items`, `order_status_history`, `order_modification_events`.

Order lines freeze the menu name/code/price/tax at order time (`*_snapshot` columns), so later
menu edits never change history. No transition logic lives here (Phase 6+ services).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time_utils import utc_now
from app.models.base import (
    Base,
    CreatedAtMixin,
    TimestampMixin,
    UpdatedAtMixin,
    UUIDPrimaryKeyMixin,
    money,
    percentage,
    uuid_fk,
)
from app.models.enums import (
    ActorRole,
    ModificationType,
    OrderItemStatus,
    OrderSource,
    OrderStatus,
    in_check,
)
from app.models.menu import MenuItem, MenuPriceVariant
from app.models.qr_sessions import CustomerSession, TableSession
from app.models.restaurant import RestaurantTable

if TYPE_CHECKING:
    from app.models.billing import BillItem


def _ts(*, nullable: bool = True, default_now: bool = False) -> Mapped[Any]:
    if default_now:
        return mapped_column(
            DateTime(timezone=True), nullable=False, default=utc_now, server_default=func.now()
        )
    return mapped_column(DateTime(timezone=True), nullable=nullable)


class Order(UUIDPrimaryKeyMixin, UpdatedAtMixin, Base):
    """Unified order batch for `CUSTOMER_QR` and `WAITER` sources inside a table session."""

    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_table_session_id_status", "table_session_id", "status"),
        Index("ix_orders_table_session_id_placed_at", "table_session_id", "placed_at"),
        Index(
            "ix_orders_kitchen_queue",
            "status",
            "placed_at",
            postgresql_where=text("status IN ('PLACED','ACCEPTED','PREPARING','READY')"),
        ),
        Index(
            "ix_orders_created_by_user_id_placed_at", "created_by_user_id", text("placed_at DESC")
        ),
        CheckConstraint(in_check("source", OrderSource), name="source_valid"),
        CheckConstraint(in_check("status", OrderStatus), name="status_valid"),
        CheckConstraint("order_subtotal >= 0", name="subtotal_non_negative"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint(
            "status <> 'REJECTED' OR rejection_reason IS NOT NULL", name="rejection_reason_required"
        ),
        CheckConstraint(
            "status <> 'CANCELLED' OR cancellation_reason IS NOT NULL",
            name="cancellation_reason_required",
        ),
    )

    order_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    table_session_id: Mapped[uuid.UUID] = uuid_fk("table_sessions.id", nullable=False)
    table_id: Mapped[uuid.UUID] = uuid_fk("restaurant_tables.id", nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    customer_session_id: Mapped[uuid.UUID | None] = uuid_fk("customer_sessions.id", nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    order_subtotal: Mapped[Decimal] = mapped_column(money(), nullable=False)
    special_instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_first_qr_order_of_session: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    has_unacknowledged_mods: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # Optimistic-concurrency counter (service layer checks it under row locks).
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )

    # Lifecycle timestamps and actors
    placed_at: Mapped[datetime] = _ts(default_now=True)
    accepted_at: Mapped[datetime | None] = _ts()
    accepted_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    preparing_at: Mapped[datetime | None] = _ts()
    preparing_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    ready_at: Mapped[datetime | None] = _ts()
    ready_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    served_at: Mapped[datetime | None] = _ts()
    served_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    completed_at: Mapped[datetime | None] = _ts()
    rejected_at: Mapped[datetime | None] = _ts()
    rejected_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancelled_at: Mapped[datetime | None] = _ts()
    cancelled_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    cancelled_by_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    table_session: Mapped[TableSession] = relationship(back_populates="orders")
    table: Mapped[RestaurantTable] = relationship()
    customer_session: Mapped[CustomerSession | None] = relationship(back_populates="orders")
    items: Mapped[list[OrderItem]] = relationship(back_populates="order")
    status_history: Mapped[list[OrderStatusHistory]] = relationship(back_populates="order")
    modification_events: Mapped[list[OrderModificationEvent]] = relationship(back_populates="order")


class OrderItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Order line with immutable historical snapshots of the menu data used at order time."""

    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_order_id_item_status", "order_id", "item_status"),
        Index("ix_order_items_menu_item_id", "menu_item_id"),
        CheckConstraint("unit_price_snapshot >= 0", name="unit_price_snapshot_non_negative"),
        CheckConstraint("original_quantity >= 1", name="original_quantity_positive"),
        CheckConstraint("active_quantity >= 0", name="active_quantity_non_negative"),
        CheckConstraint("cancelled_quantity >= 0", name="cancelled_quantity_non_negative"),
        CheckConstraint(
            "line_subtotal = active_quantity * unit_price_snapshot", name="line_subtotal_matches"
        ),
        CheckConstraint(in_check("item_status", OrderItemStatus), name="item_status_valid"),
    )

    order_id: Mapped[uuid.UUID] = uuid_fk("orders.id", nullable=False)
    menu_item_id: Mapped[uuid.UUID] = uuid_fk("menu_items.id", nullable=False)
    menu_price_variant_id: Mapped[uuid.UUID] = uuid_fk("menu_price_variants.id", nullable=False)

    # --- Historical snapshots (frozen at order creation) ---
    item_code_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    item_name_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    variant_code_snapshot: Mapped[str | None] = mapped_column(String(24), nullable=True)
    variant_name_snapshot: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity_value_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(8, 2, asdecimal=True), nullable=False
    )
    unit_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(money(), nullable=False)
    tax_rate_snapshot: Mapped[Decimal] = mapped_column(percentage(), nullable=False)

    original_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    active_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    cancelled_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    line_subtotal: Mapped[Decimal] = mapped_column(money(), nullable=False)
    item_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=OrderItemStatus.ACTIVE.value, server_default="ACTIVE"
    )
    item_notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    order: Mapped[Order] = relationship(back_populates="items")
    menu_item: Mapped[MenuItem] = relationship(back_populates="order_items")
    variant: Mapped[MenuPriceVariant] = relationship(back_populates="order_items")
    modification_events: Mapped[list[OrderModificationEvent]] = relationship(
        back_populates="order_item"
    )
    bill_items: Mapped[list[BillItem]] = relationship(back_populates="order_item")


class OrderStatusHistory(UUIDPrimaryKeyMixin, Base):
    """Append-only timeline of order status transitions."""

    __tablename__ = "order_status_history"
    __table_args__ = (
        Index("ix_order_status_history_order_id_changed_at", "order_id", "changed_at"),
        CheckConstraint(in_check("new_status", OrderStatus), name="new_status_valid"),
        CheckConstraint(
            "previous_status IS NULL OR " + in_check("previous_status", OrderStatus),
            name="previous_status_valid",
        ),
        CheckConstraint(in_check("changed_by_role", ActorRole), name="changed_by_role_valid"),
    )

    order_id: Mapped[uuid.UUID] = uuid_fk("orders.id", nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by_role: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by_user_id: Mapped[uuid.UUID | None] = uuid_fk("users.id", nullable=True)
    changed_by_customer_session_id: Mapped[uuid.UUID | None] = uuid_fk(
        "customer_sessions.id",
        nullable=True,
        name="fk_order_status_history_changed_by_customer_session_id",
    )
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    changed_at: Mapped[datetime] = _ts(default_now=True)

    order: Mapped[Order] = relationship(back_populates="status_history")


class OrderModificationEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Append-only edit ledger. Only `acknowledged_*` may change after insert."""

    __tablename__ = "order_modification_events"
    __table_args__ = (
        Index("ix_order_modification_events_order_id_created_at", "order_id", "created_at"),
        Index(
            "ix_order_modification_events_pending_kitchen_ack",
            "kitchen_ack_required",
            "acknowledged_at",
            postgresql_where=text("kitchen_ack_required = true AND acknowledged_at IS NULL"),
        ),
        CheckConstraint(in_check("modification_type", ModificationType), name="type_valid"),
        CheckConstraint("previous_quantity >= 0", name="previous_quantity_non_negative"),
        CheckConstraint("new_quantity >= 0", name="new_quantity_non_negative"),
        CheckConstraint("btrim(reason) <> ''", name="reason_not_blank"),
    )

    order_id: Mapped[uuid.UUID] = uuid_fk("orders.id", nullable=False)
    order_item_id: Mapped[uuid.UUID] = uuid_fk("order_items.id", nullable=False)
    modification_type: Mapped[str] = mapped_column(String(25), nullable=False)
    order_status_at_modification: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    new_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(money(), nullable=False)
    # Signed: positive for increases, negative for decreases/cancellations.
    price_delta: Mapped[Decimal] = mapped_column(money(), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    modified_by_user_id: Mapped[uuid.UUID] = uuid_fk("users.id", nullable=False)
    modified_by_role: Mapped[str] = mapped_column(String(20), nullable=False)
    kitchen_ack_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    acknowledged_by_kitchen_user_id: Mapped[uuid.UUID | None] = uuid_fk(
        "users.id", nullable=True, name="fk_order_modification_events_ack_kitchen_user_id"
    )
    acknowledged_at: Mapped[datetime | None] = _ts()

    order: Mapped[Order] = relationship(back_populates="modification_events")
    order_item: Mapped[OrderItem] = relationship(back_populates="modification_events")
