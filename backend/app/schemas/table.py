"""Pydantic v2 schemas for Restaurant Table management and floor layout."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import TableOperationalStatus
from app.schemas.common import StrictRequestModel


class TableBase(StrictRequestModel):
    """Base attributes for a physical restaurant table."""

    table_number: int = Field(
        gt=0,
        description="Unique numeric identifier for table",
    )
    display_name: str = Field(
        min_length=1,
        max_length=50,
        description="Display name e.g. 'Table 01'",
    )
    seating_capacity: int | None = Field(
        default=None,
        gt=0,
        description="Number of seats",
    )
    floor_or_zone: str | None = Field(
        default=None,
        max_length=50,
        description="Dining area or zone",
    )
    display_order: int = Field(
        default=0,
        ge=0,
        description="Sorting order for UI grids",
    )
    notes: str | None = Field(
        default=None,
        max_length=255,
        description="Internal staff notes",
    )


class TableCreate(TableBase):
    """Schema for Admin table creation."""

    operational_status: TableOperationalStatus = Field(
        default=TableOperationalStatus.ENABLED,
        description="Physical operational status: ENABLED, MAINTENANCE, DISABLED",
    )
    is_active: bool = Field(default=True, description="Whether table is active")


class TableUpdate(StrictRequestModel):
    """Schema for Admin table update (partial)."""

    display_name: str | None = Field(default=None, min_length=1, max_length=50)
    seating_capacity: int | None = Field(default=None, gt=0)
    floor_or_zone: str | None = Field(default=None, max_length=50)
    operational_status: TableOperationalStatus | None = None
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=255)


class TableResponse(StrictRequestModel):
    """Standard table response payload."""

    id: uuid.UUID
    table_number: int
    display_name: str
    seating_capacity: int | None = None
    floor_or_zone: str | None = None
    operational_status: str
    is_active: bool
    display_order: int
    notes: str | None = None
    current_occupancy: str = Field(
        description="Authoritative derived occupancy: 'AVAILABLE' or 'OCCUPIED'"
    )
    occupancy_status: str | None = Field(
        default=None,
        description="Alias for current_occupancy for frontend clients",
    )
    active_session_id: uuid.UUID | None = None
    active_qr_version: int | None = None
    active_qr_prefix: str | None = None
    created_at: datetime
    updated_at: datetime
