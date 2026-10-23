"""Staff authentication routes (`/api/v1/auth/*`).

Follows `docs/05-api-specification.md` (Section 3) and `docs/06-security-specification.md`.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth_cookies import (
    clear_refresh_cookie,
    enforce_cookie_csrf,
    read_refresh_cookie,
    require_refresh_cookie,
    set_refresh_cookie,
    wants_cookie_transport,
)
from app.core.database import get_db
from app.core.dependencies import get_current_staff_user
from app.core.exceptions import AuthenticationError
from app.core.rate_limit import extract_client_ip, rate_limit_by_ip
from app.models.enums import UserRole
from app.models.identity import User
from app.schemas.auth import (
    AdminRecoveryResetRequest,
    StaffChangePasswordRequest,
    StaffLoginRequest,
    StaffLogoutRequest,
    StaffMeResponse,
    StaffRefreshTokenRequest,
    StaffTokenResponse,
    StatusSuccessResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

_AUTH_RATE_LIMIT = rate_limit_by_ip(max_requests=10, window_seconds=60)


@router.post(
    "/login",
    response_model=StaffTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Staff authentication (login)",
    dependencies=[Depends(_AUTH_RATE_LIMIT)],
)
async def login(
    payload: StaffLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> StaffTokenResponse:
    """Authenticate a staff member and return access + refresh tokens.

    With `X-Auth-Transport: cookie` the refresh token is set as an httpOnly cookie instead.
    """
    cookie_mode = wants_cookie_transport(request)
    if cookie_mode:
        enforce_cookie_csrf(request)
    client_ip = extract_client_ip(request)
    tokens = await AuthService.login(db, payload, client_ip=client_ip)
    if cookie_mode:
        set_refresh_cookie(response, tokens.refresh_token)
        return tokens.model_copy(update={"refresh_token": ""})
    return tokens


@router.post(
    "/refresh",
    response_model=StaffTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue new access token",
    dependencies=[Depends(_AUTH_RATE_LIMIT)],
)
async def refresh_tokens(
    request: Request,
    response: Response,
    payload: StaffRefreshTokenRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> StaffTokenResponse:
    """Exchange a valid refresh token for a new access token and rotated refresh token.

    Cookie mode (`X-Auth-Transport: cookie`) reads the token from the httpOnly cookie and sets the
    rotated one the same way; the JSON body then carries `refresh_token: ""`.
    """
    client_ip = extract_client_ip(request)
    if wants_cookie_transport(request):
        enforce_cookie_csrf(request)
        cookie_payload = StaffRefreshTokenRequest(refresh_token=require_refresh_cookie(request))
        tokens = await AuthService.refresh_tokens(db, cookie_payload, client_ip=client_ip)
        set_refresh_cookie(response, tokens.refresh_token)
        return tokens.model_copy(update={"refresh_token": ""})
    if payload is None:
        raise AuthenticationError(
            code="REFRESH_TOKEN_MISSING",
            message="No refresh token provided. Please log in again.",
        )
    return await AuthService.refresh_tokens(db, payload, client_ip=client_ip)


@router.post(
    "/logout",
    response_model=StatusSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke staff session and disconnect WebSockets",
)
async def logout(
    request: Request,
    response: Response,
    payload: StaffLogoutRequest | None = None,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db),
) -> StatusSuccessResponse:
    """Revoke staff refresh tokens and terminate active sessions (and clear the cookie)."""
    cookie_mode = wants_cookie_transport(request)
    if cookie_mode:
        enforce_cookie_csrf(request)
        cookie_token = read_refresh_cookie(request)
        if cookie_token and not (payload and payload.refresh_token):
            payload = StaffLogoutRequest(refresh_token=cookie_token)
    client_ip = extract_client_ip(request)
    await AuthService.logout(db, current_user, payload, client_ip=client_ip)
    if cookie_mode:
        clear_refresh_cookie(response)
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


@router.post(
    "/change-password",
    response_model=StatusSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Change own password (signs out all sessions)",
    dependencies=[Depends(rate_limit_by_ip(max_requests=5, window_seconds=60))],
)
async def change_password(
    request: Request,
    response: Response,
    payload: StaffChangePasswordRequest,
    current_user: User = Depends(get_current_staff_user),
    db: AsyncSession = Depends(get_db),
) -> StatusSuccessResponse:
    """Verify the current password, set a new one and revoke every session of this user."""
    cookie_mode = wants_cookie_transport(request)
    if cookie_mode:
        enforce_cookie_csrf(request)
    await AuthService.change_password(
        db, current_user, payload, client_ip=extract_client_ip(request)
    )
    if cookie_mode:
        clear_refresh_cookie(response)
    return StatusSuccessResponse(status="PASSWORD_CHANGED")


@router.post(
    "/admin-recovery-reset",
    response_model=StatusSuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Break-glass admin password reset using the server recovery key",
    dependencies=[Depends(rate_limit_by_ip(max_requests=5, window_seconds=900))],
)
async def admin_recovery_reset(
    request: Request,
    payload: AdminRecoveryResetRequest,
    db: AsyncSession = Depends(get_db),
) -> StatusSuccessResponse:
    """Reset a locked-out admin's password. Requires ADMIN_RECOVERY_KEY to be configured."""
    await AuthService.admin_recovery_reset(db, payload, client_ip=extract_client_ip(request))
    return StatusSuccessResponse(status="PASSWORD_RESET")

