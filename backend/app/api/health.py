"""Health and database readiness endpoints (`GET /api/v1/health*`).

Follows `docs/10-deployment-and-devops-specification.md` (Section 14) and
`docs/13-final-implementation-blueprint.md` (Section 25).
Never exposes sensitive environment variables, database credentials, or hostnames.
"""

from __future__ import annotations

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.database import check_db_connectivity
from app.core.time_utils import utc_now_iso
from app.schemas.common import HealthLiveResponse, HealthReadyResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=HealthLiveResponse,
    status_code=status.HTTP_200_OK,
    summary="Service health check",
)
async def get_health() -> HealthLiveResponse:
    """Confirm the FastAPI service is running (`GET /api/v1/health`)."""
    settings = get_settings()
    return HealthLiveResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
        version=settings.app_version,
        timestamp=utc_now_iso(),
    )


@router.get(
    "/live",
    response_model=HealthLiveResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
)
async def get_liveness() -> HealthLiveResponse:
    """Zero-DB liveness probe (`GET /api/v1/health/live`)."""
    settings = get_settings()
    return HealthLiveResponse(
        status="alive",
        service=settings.app_name,
        environment=settings.environment,
        version=settings.app_version,
        timestamp=utc_now_iso(),
    )


async def _build_readiness_response() -> JSONResponse:
    """Execute database connectivity check and build a safe 200 or 503 JSONResponse."""
    settings = get_settings()
    db_ok = await check_db_connectivity(timeout_seconds=2.0)
    payload = HealthReadyResponse(
        status="ready" if db_ok else "not_ready",
        database="connected" if db_ok else "unavailable",
        service=settings.app_name,
        environment=settings.environment,
        timestamp=utc_now_iso(),
    )
    http_status = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=http_status,
        content=payload.model_dump(),
    )


@router.get(
    "/ready",
    response_model=HealthReadyResponse,
    responses={
        status.HTTP_200_OK: {"model": HealthReadyResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthReadyResponse},
    },
    summary="Readiness probe (verifies database connectivity)",
)
async def get_readiness() -> JSONResponse:
    """Readiness probe (`GET /api/v1/health/ready`)."""
    return await _build_readiness_response()


@router.get(
    "/db",
    response_model=HealthReadyResponse,
    responses={
        status.HTTP_200_OK: {"model": HealthReadyResponse},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": HealthReadyResponse},
    },
    summary="Database connectivity probe",
)
async def get_db_health() -> JSONResponse:
    """Database connectivity probe (`GET /api/v1/health/db`)."""
    return await _build_readiness_response()
