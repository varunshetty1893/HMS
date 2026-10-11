"""Pydantic schemas for staff authentication, tokens, and profiles.

Follows `docs/05-api-specification.md` (Section 3) and
`docs/06-security-specification.md` (Sections 3–5).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class StaffLoginRequest(StrictRequestModel):
    """Staff login payload (`POST /api/v1/auth/login`)."""

    username: str = Field(min_length=3, max_length=64, description="Staff username")
    password: str = Field(min_length=8, max_length=128, description="Staff plaintext password")
    client_type: Literal["ADMIN_WEB", "WAITER_APP", "KITCHEN_APP"] | None = Field(
        default=None, description="Client form factor requesting authentication"
    )
    device_label: str | None = Field(
        default=None, max_length=100, description="Optional label for the physical device"
    )


class StaffRefreshTokenRequest(StrictRequestModel):
    """Token refresh payload (`POST /api/v1/auth/refresh`)."""

    refresh_token: str = Field(
        min_length=1, max_length=256, description="High-entropy raw refresh token"
    )


class StaffLogoutRequest(StrictRequestModel):
    """Optional payload for logout (`POST /api/v1/auth/logout`)."""

    refresh_token: str | None = Field(
        default=None, max_length=256, description="Specific refresh token to revoke"
    )


class StaffUserResponse(BaseModel):
    """Public staff profile representation returned inside auth responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str
    role: str
    status: str
    last_login_at: datetime | None = None


class StaffTokenResponse(BaseModel):
    """Canonical authentication response returned upon login or token rotation."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in_seconds: int = 900
    user: StaffUserResponse


class StaffMeResponse(BaseModel):
    """Staff profile representation for `GET /api/v1/auth/me`."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    full_name: str
    role: str
    status: str
    last_login_at: datetime | None = None
    permissions: list[str] = Field(default_factory=list)


class StatusSuccessResponse(BaseModel):
    """Generic status response (e.g., logout)."""

    status: str
