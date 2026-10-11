"""Staff authentication routes (`/api/v1/auth/*`).

Follows `docs/05-api-specification.md` (Section 3) and `docs/06-security-specification.md`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_staff_user
from app.models.enums import UserRole
from app.models.identity import User
from app.schemas.auth import (
    StaffLoginRequest,
    StaffLogoutRequest,
    StaffMeResponse,
    StaffRefreshTokenRequest,
    StaffTokenResponse,
    StatusSuccessResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _extract_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


@router.post(
    "/login",
    response_model=StaffTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Staff authentication (login)",
)
async def login(
    payload: StaffLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StaffTokenResponse:
    """Authenticate a staff member and return access + refresh tokens."""
    client_ip = _extract_client_ip(request)
    return await AuthService.login(db, payload, client_ip=client_ip)


@router.post(
    "/refresh",
    response_model=StaffTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue new access token",
)
async def refresh_tokens(
    payload: StaffRefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> StaffTokenResponse:
    """Exchange a valid refresh token for a new access token and rotated refresh token."""
    client_ip = _extract_client_ip(request)
    return await AuthService.refresh_tokens(db, payload, client_ip=client_ip)


@router.post(
    "/logout",
    response_model=StatusSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke staff session and disconnect WebSockets",
)
async def logout(
    request: Request,
    payload: StaffLogoutRequest | None = None,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db),
) -> StatusSuccessResponse:
    """Revoke staff refresh tokens and terminate active sessions."""
    client_ip = _extract_client_ip(request)
    await AuthService.logout(db, current_user, payload, client_ip=client_ip)
    return StatusSuccessResponse(status="LOGGED_OUT")


@router.get(
    "/me",
    response_model=StaffMeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current staff profile",
)
async def get_me(
    current_user: User = Depends(get_current_staff_user),
) -> StaffMeResponse:
    """Retrieve profile and permissions for the currently authenticated staff member."""
    # Define role permissions matrix based on docs/06 Section 5.1
    permissions = []
    if current_user.role == UserRole.ADMIN.value:
        permissions = [
            "menu:manage",
            "tables:manage",
            "orders:all",
            "bills:manage",
            "reports:view",
            "staff:manage",
        ]
    elif current_user.role == UserRole.WAITER.value:
        permissions = [
            "tables:view",
            "orders:create",
            "orders:modify",
            "orders:serve",
            "bills:generate",
            "payments:record",
        ]
    elif current_user.role == UserRole.KITCHEN.value:
        permissions = [
            "orders:view_queue",
            "orders:accept",
            "orders:reject",
            "orders:prep",
            "orders:ready",
        ]

    return StaffMeResponse(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        status=current_user.status,
        last_login_at=current_user.last_login_at,
        permissions=permissions,
    )
