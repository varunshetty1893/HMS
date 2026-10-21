"""Pydantic schemas for notification recovery endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class NotificationItem(BaseModel):
    """Serialized notification for client recovery."""

    id: uuid.UUID
    event_type: str
    target_channel: str
    severity: str
    title: str
    message: str
    payload_json: dict[str, Any]
    table_id: uuid.UUID | None = None
    table_session_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None
    created_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}


class NotificationAckRequest(BaseModel):
    """Batch acknowledgement request."""

    notification_ids: list[uuid.UUID]


class NotificationAckResponse(BaseModel):
    """Acknowledgement result."""

    acknowledged: int
