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

from pydantic import Field, computed_field, field_validator, model_validator

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
    custom_unit_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        description="Staff-only custom unit price or negotiated price.",
    )
    custom_portion_name: str | None = Field(
        default=None,
        max_length=80,
        description="Staff-only custom portion label (e.g. 'Half bowl').",
    )
    extra_pieces: int = Field(
        default=0,
        ge=0,
        le=50,
        description="Staff-specified extra pieces added to this line.",
    )
    adjustment_type: str | None = Field(default=None)
    adjustment_amount: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    adjustment_reason: str | None = Field(default=None, max_length=255)

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

    # ── live bill & flexible portion adjustments ──────────────────────────
    base_price_snapshot: Decimal | None = None
    custom_portion_name: str | None = None
    extra_pieces_count: int = 0
    extra_piece_price: Decimal | None = None
    adjustment_type: str | None = None
    adjustment_amount: Decimal | None = None
    adjustment_reason: str | None = None
    adjustment_applied_by_user_id: uuid.UUID | None = None
    adjustment_approved_by_user_id: uuid.UUID | None = None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def item_name(self) -> str:
        return self.item_name_snapshot

    @computed_field  # type: ignore[prop-decorator]
    @property
    def item_code(self) -> str:
        return self.item_code_snapshot

    @computed_field  # type: ignore[prop-decorator]
    @property
    def variant_name(self) -> str:
        return self.variant_name_snapshot


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

    # Cancellation info so every client can show who/why (None unless CANCELLED)
    cancelled_at: Any | None = None
    cancelled_by_role: str | None = None
    cancellation_reason: str | None = None

    # Only set while status == PENDING_CONFIRMATION: when the request auto-cancels.
    confirmation_expires_at: Any | None = None
    # True when a QR request was rejected/expired/withdrawn before any waiter confirmed it,
    # i.e. the kitchen never saw this order.
    never_confirmed: bool = False


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
    # True when the order is parked until a waiter confirms guests are seated (threat T-01).
    requires_confirmation: bool = False
    confirmation_expires_at: Any | None = None


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
    custom_unit_price: Decimal | None = Field(
        default=None,
        ge=Decimal("0.00"),
        description="Staff-only updated unit price.",
    )
    custom_portion_name: str | None = Field(
        default=None,
        max_length=80,
        description="Staff-only updated custom portion label.",
    )
    extra_pieces: int | None = Field(
        default=None,
        ge=0,
        le=50,
        description="Updated extra pieces count.",
    )
    adjustment_type: str | None = Field(default=None)
    adjustment_amount: Decimal | None = Field(default=None, ge=Decimal("0.00"))


class OrderItemAdjustmentRequest(StrictRequestModel):
    """Payload to adjust price, portion, extra pieces, or discount on an order line."""

    expected_version: int = Field(..., ge=1, description="Order version for concurrency check.")
    adjustment_type: str = Field(
        ...,
        description=(
            "CUSTOM_PRICE, CUSTOM_PORTION, EXTRA_PIECES, DISCOUNT_FIXED, "
            "DISCOUNT_PERCENT, SURCHARGE_FIXED, SURCHARGE_PERCENT"
        ),
    )
    custom_unit_price: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    custom_portion_name: str | None = Field(default=None, max_length=80)
    extra_pieces: int = Field(default=0, ge=0, le=50)
    discount_amount: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    discount_percent: Decimal | None = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    surcharge_amount: Decimal | None = Field(default=None, ge=Decimal("0.00"))
    surcharge_percent: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), le=Decimal("100.00")
    )
    reason: str = Field(
        ..., min_length=2, max_length=255, description="Mandatory audit explanation."
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
    force: bool = Field(
        default=False,
        description=(
            "Staff-only (WAITER/ADMIN). Required to REDUCE or REMOVE items while the kitchen "
            "is already PREPARING. Kitchen is always notified. Needs a reason of 3+ chars."
        ),
    )

    @model_validator(mode="after")
    def force_needs_real_reason(self) -> OrderModifyRequest:
        if self.force and len(self.reason.strip()) < 3:
            raise ValueError("A forced modification needs a reason of at least 3 characters.")
        return self


class OrderCancelRequest(StrictRequestModel):
    """Payload to cancel an order."""

    expected_version: int = Field(..., ge=1, description="Optimistic concurrency control version.")
    cancellation_reason: str = Field(
        ..., min_length=3, max_length=255, description="Mandatory reason for cancellation."
    )
    force: bool = Field(
        default=False,
        description=(
            "Staff-only (WAITER/ADMIN) FORCE cancellation. Needed once the kitchen is "
            "PREPARING or the order is READY. Kitchen is notified to stop / discard."
        ),
    )


class CustomerOrderItemChange(StrictRequestModel):
    """One edit a customer makes to a line of their own order.

    Exactly ONE of the two modes per line:
      * quantity mode  -> `new_quantity` (absolute active quantity, 0 removes the line)
      * portion mode   -> `switch_to_variant_id` (+ `switch_quantity`) moves units to a
                          CHEAPER variant of the same dish (e.g. Full -> Half biryani).
    """

    order_item_id: uuid.UUID
    new_quantity: int | None = Field(default=None, ge=0, le=20)
    switch_to_variant_id: uuid.UUID | None = None
    switch_quantity: int | None = Field(default=None, ge=1, le=20)

    @model_validator(mode="after")
    def exactly_one_mode(self) -> CustomerOrderItemChange:
        quantity_mode = self.new_quantity is not None
        switch_mode = self.switch_to_variant_id is not None
        if quantity_mode == switch_mode:
            raise ValueError("Provide either new_quantity or switch_to_variant_id (not both).")
        if self.switch_quantity is not None and not switch_mode:
            raise ValueError("switch_quantity is only valid with switch_to_variant_id.")
        return self


class CustomerOrderModifyRequest(StrictRequestModel):
    """Customer self-service edit of an order that is not READY/SERVED yet."""

    expected_version: int = Field(..., ge=1, description="Optimistic concurrency control version.")
    changes: list[CustomerOrderItemChange] = Field(..., min_length=1, max_length=30)
    reason: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def no_duplicate_lines(self) -> CustomerOrderModifyRequest:
        ids = [c.order_item_id for c in self.changes]
        if len(ids) != len(set(ids)):
            raise ValueError("Each order line may appear only once per request.")
        return self


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


class PendingConfirmationItem(StrictRequestModel):
    """A QR order waiting for a waiter to confirm that guests are seated."""

    order: WaiterOrderResponse
    expires_at: Any
    seconds_remaining: int


class PendingConfirmationList(StrictRequestModel):
    """Waiter inbox of unconfirmed QR orders (oldest first)."""

    items: list[PendingConfirmationItem] = []
    total: int = 0
    timeout_seconds: int = 180


class PendingOrderRejectRequest(StrictRequestModel):
    """Optional note when a waiter rejects an unconfirmed QR order."""

    reason: str | None = Field(default=None, max_length=200)
