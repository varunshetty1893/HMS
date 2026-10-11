"""Pydantic v2 common response, health, pagination, and error schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.sanitizer import sanitize_text


class StrictRequestModel(BaseModel):
    """Base schema for all incoming client requests.

    Enforces:
    - `extra='forbid'` — rejects any undocumented client-supplied fields.
    - `str_strip_whitespace=True` — trims leading/trailing whitespace.
    - XSS sanitization — all `str | None` fields are checked for HTML tags
      and dangerous URI schemes (docs/06 Section 24).
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def _sanitize_string_fields(cls, value: object) -> object:
        """Reject HTML tags and dangerous URI schemes on all string fields."""
        if isinstance(value, str):
            return sanitize_text(value)
        return value


class ErrorDetailPayload(BaseModel):
    """Inner error structure in the canonical error response envelope."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str
    timestamp: str


class ResponseMeta(BaseModel):
    """Metadata attached to API responses."""

    request_id: str
    timestamp: str


class ErrorResponseEnvelope(BaseModel):
    """Canonical non-2xx JSON error envelope (`docs/05` Section 24 & `docs/11` Section 18)."""

    success: bool = False
    error: ErrorDetailPayload
    meta: ResponseMeta


class PaginationMeta(BaseModel):
    """Standard pagination metadata (`docs/05` Section 25)."""

    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total_items: int = Field(ge=0)
    total_pages: int = Field(ge=0)
    has_next: bool
    has_prev: bool


class HealthLiveResponse(BaseModel):
    """Response model for `GET /api/v1/health` and `GET /api/v1/health/live`."""

    status: str
    service: str
    environment: str
    version: str
    timestamp: str


class HealthReadyResponse(BaseModel):
    """Response model for `GET /api/v1/health/ready` and `GET /api/v1/health/db`."""

    status: str
    database: str
    service: str
    environment: str
    timestamp: str
