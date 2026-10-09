"""Pydantic v2 request and response schemas package."""

from app.schemas.common import (
    ErrorDetailPayload,
    ErrorResponseEnvelope,
    HealthLiveResponse,
    HealthReadyResponse,
    PaginationMeta,
    ResponseMeta,
    StrictRequestModel,
)

__all__ = [
    "ErrorDetailPayload",
    "ErrorResponseEnvelope",
    "HealthLiveResponse",
    "HealthReadyResponse",
    "PaginationMeta",
    "ResponseMeta",
    "StrictRequestModel",
]
