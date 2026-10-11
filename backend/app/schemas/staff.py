"""Staff management schemas for Admin Web."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole, UserStatus
from app.schemas.common import StrictRequestModel


class StaffUserCreate(StrictRequestModel):
    """Payload to create a new staff member (WAITER, KITCHEN, or ADMIN)."""

    username: str = Field(min_length=3, max_length=64, description="Unique username")
    full_name: str = Field(min_length=1, max_length=120, description="Full display name")
    password: str = Field(min_length=6, max_length=128, description="Initial staff password")
    role: UserRole = Field(description="Assigned role: ADMIN, WAITER, or KITCHEN")


class StaffUserUpdate(StrictRequestModel):
    """Payload to update staff details or status."""

    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    role: UserRole | None = Field(default=None)
    status: UserStatus | None = Field(default=None)
    is_active: bool | None = Field(default=None)


class StaffPasswordResetRequest(StrictRequestModel):
    """Payload to reset a staff user's password."""

    new_password: str = Field(min_length=6, max_length=128)


class StaffUserAdminResponse(BaseModel):
    """Comprehensive staff details returned to Admin."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str
    role: str
    status: str
    is_active: bool
    failed_login_attempts: int
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
