"""Pydantic v2 schemas for QR token lifecycle, customer sessions, and printing."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.schemas.common import StrictRequestModel


class QrResolutionRequest(StrictRequestModel):
    """Payload for resolving a physical QR code."""

    qr_token: str = Field(
        min_length=8, max_length=255, description="Scanned raw QR token or secret"
    )


class QrResolutionResponse(StrictRequestModel):
    """Response returned upon resolving an active table QR code.

    Establishes an anonymous customer session without occupying the table.
    """

    customer_session_token: str = Field(
        description="Bearer token to store in customer sessionStorage/localStorage"
    )
    table_id: uuid.UUID
    table_number: int
    table_display_name: str
    floor_or_zone: str | None = None
    table_status: str = Field(
        description="'AVAILABLE' or 'OCCUPIED' (derived from active sessions)"
    )
    active_session_id: uuid.UUID | None = None
    session_expires_at: datetime
    restaurant_name: str
    currency_symbol: str = "₹"


class CustomerSessionResponse(StrictRequestModel):
    """Customer session inspection payload."""

    session_id: uuid.UUID
    table_id: uuid.UUID
    table_number: int
    table_display_name: str
    table_status: str
    table_session_id: uuid.UUID | None = None
    current_outstanding_amount: Decimal = Decimal("0.00")
    custom_outstanding_limit: Decimal = Decimal("5000.00")
    status: str
    expires_at: datetime


class QrRegenerateRequest(StrictRequestModel):
    """Request payload for Admin QR rotation."""

    reason: str | None = Field(default="ROTATED_BY_ADMIN", max_length=255)


class QrRegenerateResponse(StrictRequestModel):
    """Response returned when an Admin rotates a table's QR token."""

    table_id: uuid.UUID
    table_number: int
    table_display_name: str
    token_version: int
    token_prefix: str
    status: str
    qr_url: str
    raw_token: str


class QrPrintCardResponse(StrictRequestModel):
    """Printable standee card metadata for Admin printing."""

    table_id: uuid.UUID
    table_number: int
    table_display_name: str
    floor_or_zone: str | None = None
    seating_capacity: int | None = None
    token_version: int
    token_prefix: str
    qr_url: str
    raw_token: str
    restaurant_name: str
