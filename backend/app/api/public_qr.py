"""Public QR code resolution endpoints.

Follows `docs/04-database-design.md` (Sections 5 & 6), `docs/05-api-specification.md` (Section 5),
`docs/06-security-specification.md` (Section 4), and `docs/13` (Phase 5).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import extract_client_ip, rate_limit_by_ip
from app.schemas.qr import QrResolutionRequest, QrResolutionResponse
from app.services.qr_service import QrService

router = APIRouter(prefix="/public/qr", tags=["Public QR Operations"])


@router.get(
    "/{qr_token}",
    response_model=QrResolutionResponse,
    dependencies=[Depends(rate_limit_by_ip(max_requests=15, window_seconds=60))],
)
async def resolve_qr_by_path(
    qr_token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> QrResolutionResponse:
    """Resolve physical table QR code from URL path token and issue customer session."""
    client_ip = extract_client_ip(request)
    user_agent = request.headers.get("user-agent")
    existing_session_token = request.headers.get("x-customer-session-token")
    if not existing_session_token:
        auth_hdr = request.headers.get("authorization", "")
        if auth_hdr.lower().startswith("bearer "):
            existing_session_token = auth_hdr[7:].strip()
    return await QrService.resolve_qr_token(
        db,
        raw_token_input=qr_token,
        client_ip=client_ip,
        user_agent=user_agent,
        existing_session_token=existing_session_token,
        device_id=request.headers.get("x-device-id"),
    )


@router.post(
    "/resolve",
    response_model=QrResolutionResponse,
    dependencies=[Depends(rate_limit_by_ip(max_requests=15, window_seconds=60))],
)
async def resolve_qr_by_body(
    payload: QrResolutionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> QrResolutionResponse:
    """Resolve physical table QR code from JSON payload and issue customer session."""
    client_ip = extract_client_ip(request)
    user_agent = request.headers.get("user-agent")
    existing_session_token = request.headers.get("x-customer-session-token")
    if not existing_session_token:
        auth_hdr = request.headers.get("authorization", "")
        if auth_hdr.lower().startswith("bearer "):
            existing_session_token = auth_hdr[7:].strip()
    return await QrService.resolve_qr_token(
        db,
        raw_token_input=payload.qr_token,
        client_ip=client_ip,
        user_agent=user_agent,
        existing_session_token=existing_session_token,
        device_id=request.headers.get("x-device-id"),
    )
