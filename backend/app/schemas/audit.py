"""Audit log schemas for security and operational trace viewer."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.common import PaginationMeta


class AuditLogResponse(BaseModel):
    """Single immutable audit log entry."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_user_id: uuid.UUID | None = None
    actor_username: str | None = None
    actor_customer_session_id: uuid.UUID | None = None
    actor_role: str
    action_type: str
    entity_type: str
    entity_id: str
    reason: str | None = None
    old_value_json: Any | None = None
    new_value_json: Any | None = None
    metadata_json: Any | None = None
    ip_hash: str | None = None
    created_at: datetime


class AuditLogFacets(BaseModel):
    """Distinct values present in the audit trail, used to populate filter dropdowns."""

    action_types: list[str]
    entity_types: list[str]
    actor_roles: list[str]


class AuditLogPageResponse(BaseModel):
    """Paginated list of audit records."""

    items: list[AuditLogResponse]
    pagination: PaginationMeta
