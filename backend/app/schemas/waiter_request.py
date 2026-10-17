"""Pydantic schemas for the Call-Waiter feature.

Follows `docs/05-api-specification.md` conventions and the same strict-request
pattern used throughout the codebase.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel

# ─────────────────────────────────────────────────────────────────────────────
# Customer → Server
# ─────────────────────────────────────────────────────────────────────────────

VALID_REASONS = Literal["ASSISTANCE", "CUTLERY", "WATER", "OTHER"]


class WaiterRequestCreate(StrictRequestModel):
    """Customer payload to create a new call-waiter request."""

    reason: VALID_REASONS = Field(
        description="Why the customer is calling a waiter",
    )
    notes: str | None = Field(
        default=None,
        max_length=200,
        description="Optional free-text note (e.g. 'need fork', 'spilled water')",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Server → Client (shared)
# ─────────────────────────────────────────────────────────────────────────────


class WaiterRequestResponse(BaseModel):
    """Full waiter-request representation returned to both customers and waiters."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    customer_session_id: uuid.UUID
    table_session_id: uuid.UUID
    table_id: uuid.UUID
    reason: str
    notes: str | None
    status: str
    claimed_by_user_id: uuid.UUID | None
    claimed_at: datetime | None
    completed_at: datetime | None
    completed_by_user_id: uuid.UUID | None
    cancelled_at: datetime | None
    expires_at: datetime
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Waiter → Server
# ─────────────────────────────────────────────────────────────────────────────


class WaiterRequestClaimRequest(StrictRequestModel):
    """Waiter payload to atomically claim a pending request."""

    # No fields required; claim is idempotent to the claiming waiter.
    pass


class WaiterRequestCompleteRequest(StrictRequestModel):
    """Waiter payload to mark a claimed request as completed."""

    notes: str | None = Field(
        default=None,
        max_length=200,
        description="Optional completion note",
    )


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket broadcast payloads
# ─────────────────────────────────────────────────────────────────────────────


class WaiterRequestWsPayload(BaseModel):
    """Shape of the WebSocket broadcast for waiter-request lifecycle events."""

    # Event types: waiter.request.{created,claimed,completed,cancelled}
    event: str
    request_id: str
    table_session_id: str
    table_id: str
    table_number: int | None
    table_display_name: str | None
    reason: str
    notes: str | None
    status: str
    claimed_by_user_id: str | None
    claimed_at: str | None
    completed_at: str | None
    created_at: str
