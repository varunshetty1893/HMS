"""Billing & Payment Pydantic v2 schemas.

Follows `docs/05-api-specification.md` (Sections 17-18) and
`docs/13-final-implementation-blueprint.md` (Phase 9).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class ResponseModel(BaseModel):
    """Base response model supporting ORM attribute mapping."""

    model_config = ConfigDict(from_attributes=True)

# ─────────────────────────────────────────────────────────────────────────────
# Bill Line Items & Responses
# ─────────────────────────────────────────────────────────────────────────────


class BillItemResponse(ResponseModel):
    """Frozen invoice line snapshot representation."""

    id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    order_number: str
    item_code: str
    item_name: str
    variant_code: str | None = None
    variant_name: str
    unit: str
    quantity_billed: int
    unit_price_snapshot: Decimal
    line_total: Decimal
    base_price_snapshot: Decimal | None = None
    custom_portion_name: str | None = None
    extra_pieces_count: int = 0
    adjustment_type: str | None = None
    adjustment_amount: Decimal | None = None
    adjustment_reason: str | None = None


class BillResponse(ResponseModel):
    """Consolidated Bill representation with full tax and audit detail."""

    id: uuid.UUID
    bill_number: str
    table_session_id: uuid.UUID
    table_id: uuid.UUID
    table_number: int | None = None
    table_display_name: str | None = None
    status: str
    subtotal_amount: Decimal
    discount_amount: Decimal
    discount_reason: str | None = None
    discount_approved_by_user_id: uuid.UUID | None = None
    taxable_amount: Decimal
    cgst_rate_snapshot: Decimal
    cgst_amount: Decimal
    sgst_rate_snapshot: Decimal
    sgst_amount: Decimal
    service_charge_amount: Decimal
    rounding_adjustment: Decimal
    grand_total: Decimal
    generated_by_user_id: uuid.UUID
    generated_by_name: str | None = None
    generated_at: datetime
    paid_at: datetime | None = None
    closed_at: datetime | None = None
    voided_at: datetime | None = None
    void_reason: str | None = None
    line_items: list[BillItemResponse] = Field(default_factory=list)


class TableBillResponse(ResponseModel):
    """Response for GET /api/v1/waiter/tables/{table_number}/bill.

    Returns the existing ISSUED/PAID bill or a live bill preview.
    """

    table_number: int
    table_id: uuid.UUID
    table_display_name: str | None = None
    table_session_id: uuid.UUID
    session_code: str
    has_unaccepted_placed_orders: bool = False
    has_unserved_orders: bool = False
    bill_status: str  # 'NOT_GENERATED', 'ISSUED', 'PAID', 'VOIDED_FOR_REVISION'
    bill: BillResponse | None = None
    preview_line_items: list[BillItemResponse] = Field(default_factory=list)
    preview_subtotal: Decimal | None = None
    preview_taxable: Decimal | None = None
    preview_cgst: Decimal | None = None
    preview_sgst: Decimal | None = None
    preview_grand_total: Decimal | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Bill Actions Requests
# ─────────────────────────────────────────────────────────────────────────────


class BillLinePriceOverride(StrictRequestModel):
    """One deliberate bill-time override of an ordered line's unit price and/or quantity."""

    order_item_id: uuid.UUID
    unit_price: Decimal = Field(ge=Decimal("0.00"), max_digits=12, decimal_places=2)
    quantity_billed: int | None = Field(default=None, ge=0, le=999)
    reason: str = Field(min_length=3, max_length=255)
    custom_portion_name: str | None = Field(default=None, max_length=80)
    extra_pieces_count: int = Field(default=0, ge=0)
    adjustment_type: str | None = None
    adjustment_amount: Decimal | None = None


class BillGenerateRequest(StrictRequestModel):
    """Payload for POST /api/v1/bills/generate."""

    table_number: int | None = Field(default=None, ge=1, le=999)
    table_id: uuid.UUID | None = None
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    discount_reason: str | None = Field(default=None, max_length=255)
    price_overrides: list[BillLinePriceOverride] = Field(default_factory=list, max_length=100)


class BillDiscountRequest(StrictRequestModel):
    """Payload for POST /api/v1/admin/bills/{bill_id}/discount."""

    discount_amount: Decimal = Field(gt=Decimal("0.00"))
    discount_reason: str = Field(min_length=3, max_length=255)


class BillVoidRequest(StrictRequestModel):
    """Payload for POST /api/v1/admin/bills/{bill_id}/void-for-revision."""

    void_reason: str = Field(min_length=3, max_length=255)


# ─────────────────────────────────────────────────────────────────────────────
# Payment Requests & Responses
# ─────────────────────────────────────────────────────────────────────────────


class PaymentCreateRequest(StrictRequestModel):
    """Payload for POST /api/v1/bills/{bill_id}/payments."""

    payment_method: str = Field(description="Must be CASH, UPI, CARD, or OTHER")
    amount_paid: Decimal = Field(gt=Decimal("0.00"))
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=255)


class PaymentResponse(ResponseModel):
    """Payment record representation."""

    id: uuid.UUID
    bill_id: uuid.UUID
    bill_number: str
    table_session_id: uuid.UUID
    table_number: int | None = None
    payment_method: str
    amount_paid: Decimal
    status: str
    reference_number: str | None = None
    notes: str | None = None
    recorded_by_user_id: uuid.UUID
    recorded_by_name: str | None = None
    completed_at: datetime | None = None


class PaymentRecordResult(ResponseModel):
    """Consolidated result returned when a payment is settled."""

    payment: PaymentResponse
    bill_status: str
    table_session_status: str
    table_occupancy_status: str
