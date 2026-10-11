"""Order placement, response, and history Pydantic schemas.

Follows `docs/05-api-specification.md` (Section 7) and
`docs/13-final-implementation-blueprint.md` Phase 6.

All pricing fields use `Decimal` with two decimal places.  Unit prices are
*never* accepted from the client; they are always set server-side from the
authoritative `menu_price_variants` row (historical snapshot pattern).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from pydantic import Field, field_validator, model_validator

from app.schemas.common import StrictRequestModel

# ─────────────────────────────────────────────────────────────────────────────
# Request schemas
# ─────────────────────────────────────────────────────────────────────────────


class OrderItemCreate(StrictRequestModel):
    """A single line in the customer's order submission payload.

    Only the variant UUID and quantity are accepted.  All price, name, and code
    information is resolved server-side.
    """

    variant_id: uuid.UUID = Field(..., description="menu_price_variants.id to order.")
    quantity: int = Field(..., ge=1, le=20, description="Number of portions (1–20).")
    item_notes: str | None = Field(
        default=None,
        max_length=255,
        description="Optional per-item customer note (allergens, spice, etc.).",
    )

    @field_validator("quantity")
    @classmethod
    def quantity_must_be_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("quantity must be at least 1")
        return v


class OrderCreate(StrictRequestModel):
    """Customer QR order submission payload.

    `idempotency_key` maps to the `Idempotency-Key` HTTP header and is echoed
    back in the response so the client can detect replays (HTTP 200 on replay,
    not HTTP 201).
    """

    items: list[OrderItemCreate] = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Non-empty list of order lines (1–30 items per submission).",
    )
    special_instructions: str | None = Field(
        default=None,
        max_length=500,
        description="Free-text note for the entire order batch.",
    )

    @model_validator(mode="after")
    def items_not_empty(self) -> OrderCreate:
        if not self.items:
            raise ValueError("At least one item is required.")
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Response schemas
# ─────────────────────────────────────────────────────────────────────────────


class OrderItemResponse(StrictRequestModel):
    """Order line with fully-frozen historical snapshot values.

    Snapshot fields are the values locked at order-creation time; subsequent
    menu edits never retroactively alter them.
    """

    model_config = {"from_attributes": True}

    id: uuid.UUID
    order_id: uuid.UUID
    menu_item_id: uuid.UUID
    menu_price_variant_id: uuid.UUID

    # ── historical snapshots ──────────────────────────────────────────────
    item_code_snapshot: str
    item_name_snapshot: str
    variant_code_snapshot: str | None
    variant_name_snapshot: str
    quantity_value_snapshot: Decimal
    unit_snapshot: str
    unit_price_snapshot: Decimal
    tax_rate_snapshot: Decimal

    # ── mutable quantities ────────────────────────────────────────────────
    original_quantity: int
    active_quantity: int
    cancelled_quantity: int
    line_subtotal: Decimal
    item_status: str
    item_notes: str | None


class OrderResponse(StrictRequestModel):
    """Full order batch response returned to all actors after creation or query."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    order_number: str
    table_session_id: uuid.UUID
    table_id: uuid.UUID
    source: str
    customer_session_id: uuid.UUID | None
    status: str
    order_subtotal: Decimal
    special_instructions: str | None
    is_first_qr_order_of_session: bool
    version: int
    items: list[OrderItemResponse]

    # Lifecycle timestamps are included so clients can display "placed X mins ago"
    placed_at: Any  # datetime  – Any avoids cross-tz serialisation friction
    accepted_at: Any | None = None
    ready_at: Any | None = None
    served_at: Any | None = None
    has_unacknowledged_mods: bool = False


class CustomerOrderListResponse(StrictRequestModel):
    """Paginated order history for the current customer session."""

    model_config = {"from_attributes": True}

    orders: list[OrderResponse]
    total: int


class TableSessionInfo(StrictRequestModel):
    """Minimal table-session info included in the order-creation response."""

    model_config = {"from_attributes": True}

    session_id: uuid.UUID
    session_code: str
    status: str
    current_outstanding_amount: Decimal
    custom_outstanding_limit: Decimal
    is_first_order: bool


class OrderCreateResponse(StrictRequestModel):
    """Envelope returned from POST /api/v1/customer/orders (201 Created or 200 Replay)."""

    model_config = {"from_attributes": True}

    order: OrderResponse
    table_session: TableSessionInfo
    is_replay: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Waiter schemas (Phase 8)
# ─────────────────────────────────────────────────────────────────────────────


class WaiterOrderCreate(StrictRequestModel):
    """Waiter manual table-side order entry payload."""

    table_id: uuid.UUID = Field(..., description="Target restaurant table ID.")
    items: list[OrderItemCreate] = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Non-empty list of order lines.",
    )
    special_instructions: str | None = Field(
        default=None,
        max_length=500,
        description="Free-text note for the entire order batch.",
    )

    @model_validator(mode="after")
    def items_not_empty(self) -> WaiterOrderCreate:
        if not self.items:
            raise ValueError("At least one item is required.")
        return self


class OrderItemModification(StrictRequestModel):
    """Item line modification for an existing order."""

    order_item_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Existing order_item.id to modify. If null, variant_id must be "
            "provided to add a new line."
        ),
    )
    variant_id: uuid.UUID | None = Field(
        default=None,
        description="menu_price_variants.id if adding a new item.",
    )
    new_quantity: int = Field(
        ...,
        ge=0,
        le=20,
        description="Updated active quantity (0 cancels the item).",
    )
    new_notes: str | None = Field(
        default=None,
        max_length=255,
        description="Updated item notes.",
    )


class OrderModifyRequest(StrictRequestModel):
    """Payload to modify an active order (pre- or post-acceptance)."""

    expected_version: int = Field(..., ge=1, description="Optimistic concurrency control version.")
    items: list[OrderItemModification] = Field(
        ..., min_length=1, description="List of item additions, edits, or removals."
    )
    reason: str = Field(
        ..., min_length=1, max_length=255, description="Mandatory reason for modification."
    )


class OrderCancelRequest(StrictRequestModel):
    """Payload to cancel an order."""

    expected_version: int = Field(..., ge=1, description="Optimistic concurrency control version.")
    cancellation_reason: str = Field(
        ..., min_length=3, max_length=255, description="Mandatory reason for cancellation."
    )


class OrderServeRequest(StrictRequestModel):
    """Payload to mark a READY order as SERVED."""

    expected_version: int = Field(..., ge=1, description="Optimistic concurrency control version.")


class SessionLimitOverrideRequest(StrictRequestModel):
    """Payload to override/raise the session unpaid exposure limit."""

    new_limit: Decimal = Field(..., ge=Decimal("100.00"), le=Decimal("100000.00"))
    reason: str = Field(..., min_length=3, max_length=255)



class OrderModificationEventResponse(StrictRequestModel):
    """Audit log entry of an order modification."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    modification_type: str
    order_status_at_modification: str
    previous_quantity: int
    new_quantity: int
    previous_notes: str | None = None
    new_notes: str | None = None
    price_delta: Decimal
    reason: str
    modified_by_role: str
    kitchen_ack_required: bool
    acknowledged_at: Any | None = None
    created_at: Any


class WaiterOrderResponse(OrderResponse):
    """Order response extended with table and modification details for Waiter App."""

    table_number: int
    table_display_name: str
    modification_events: list[OrderModificationEventResponse] = []


class WaiterTableSessionDetail(StrictRequestModel):
    """Comprehensive table session details for the Waiter table detail sheet."""

    model_config = {"from_attributes": True}

    table_id: uuid.UUID
    table_number: int
    table_display_name: str
    table_status: str
    session_id: uuid.UUID | None = None
    session_code: str | None = None
    session_status: str | None = None
    current_outstanding_amount: Decimal = Decimal("0.00")
    custom_outstanding_limit: Decimal = Decimal("5000.00")
    orders: list[WaiterOrderResponse] = []
