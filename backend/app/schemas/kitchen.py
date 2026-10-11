"""Kitchen Display System (KDS) Pydantic schemas — Phase 7.

Strict RBAC / Data-scrubbing Rule:
Tickets delivered to Kitchen contain ZERO financial fields:
`unit_price`, `price_delta`, `line_subtotal`, and `order_subtotal`
are strictly omitted.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KitchenItemTicket(BaseModel):
    """Line item on a kitchen ticket with zero financial data."""

    model_config = ConfigDict(from_attributes=True)

    order_item_id: uuid.UUID
    item_code: str
    item_name: str
    variant_name: str
    original_quantity: int
    active_quantity: int
    item_status: str
    item_notes: str | None = None


class KitchenModificationEventResponse(BaseModel):
    """Diff alert banner item on the kitchen ticket."""

    model_config = ConfigDict(from_attributes=True)

    modification_event_id: uuid.UUID
    modification_type: str
    item_name: str
    previous_quantity: int
    new_quantity: int
    reason: str
    modified_by_name: str | None = None
    created_at: datetime


class KitchenOrderTicket(BaseModel):
    """Full ticket on the KDS board."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    table_id: uuid.UUID
    table_number: int
    table_display_name: str
    source: str
    waiter_name: str | None = None
    status: str
    placed_at: datetime
    accepted_at: datetime | None = None
    preparing_at: datetime | None = None
    ready_at: datetime | None = None
    elapsed_seconds: int = 0
    version: int
    special_instructions: str | None = None
    has_unacknowledged_mods: bool = False
    items: list[KitchenItemTicket]
    unacknowledged_modifications: list[KitchenModificationEventResponse] = Field(
        default_factory=list
    )


class KitchenCounts(BaseModel):
    placed: int = 0
    accepted: int = 0
    preparing: int = 0
    ready: int = 0
    unacknowledged_modifications: int = 0


class KitchenDashboardResponse(BaseModel):
    counts: KitchenCounts
    orders: list[KitchenOrderTicket]


class OrderTransitionRequest(BaseModel):
    expected_version: int = Field(ge=1, description="Optimistic concurrency version")


class OrderRejectRequest(BaseModel):
    expected_version: int = Field(ge=1, description="Optimistic concurrency version")
    reason: str = Field(min_length=1, max_length=255, description="Mandatory rejection reason")


class AcknowledgeModificationsRequest(BaseModel):
    modification_event_ids: list[uuid.UUID] | None = None


class KitchenAvailabilityToggleRequest(BaseModel):
    is_available: bool
