"""Opt-in httpOnly refresh-token cookie for browser clients (admin web).

Why: a refresh token in `localStorage` is readable by any injected script (XSS). In an httpOnly
cookie JavaScript can never read it. Native clients (Flutter staff app) are unchanged: they keep
sending/receiving the refresh token in the JSON body.

A client opts in per request with the header ``X-Auth-Transport: cookie``. In that mode:
- `/auth/login` and `/auth/refresh` set the cookie and return ``refresh_token: ""`` in the body;
- `/auth/refresh` and `/auth/logout` read the token from the cookie when the body has none.

CSRF: the cookie is only sent to ``<api prefix>/auth`` and every cookie-mode request must carry the
custom header ``X-Requested-With: hms-admin-web`` (which forces a CORS preflight, so other sites
cannot send it) and, when an ``Origin`` header is present, an origin from ``CORS_ALLOWED_ORIGINS``.
"""

from __future__ import annotations

from fastapi import Request, Response

from app.config import get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError

TRANSPORT_HEADER = "X-Auth-Transport"
TRANSPORT_COOKIE = "cookie"
CSRF_HEADER = "X-Requested-With"
CSRF_VALUE = "hms-admin-web"


def wants_cookie_transport(request: Request) -> bool:
    return request.headers.get(TRANSPORT_HEADER, "").strip().lower() == TRANSPORT_COOKIE


def enforce_cookie_csrf(request: Request) -> None:
    """Reject cookie-mode calls that do not prove they come from our own web app."""
    if request.headers.get(CSRF_HEADER, "") != CSRF_VALUE:
        raise AuthorizationError(
            code="CSRF_CHECK_FAILED",
            message="Missing or invalid anti-CSRF header.",
        )
    origin = request.headers.get("origin")
    if origin and origin not in get_settings().cors_allowed_origins:
        raise AuthorizationError(
            code="CSRF_ORIGIN_NOT_ALLOWED",
            message="Request origin is not allowed.",
        )


def _cookie_path() -> str:
    return f"{get_settings().api_v1_prefix.rstrip('/')}/auth"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path=_cookie_path(),
        httponly=True,
        secure=settings.auth_cookie_is_secure,
        samesite=settings.auth_cookie_samesite,
    )


def clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.auth_cookie_name,
        path=_cookie_path(),
        httponly=True,
        secure=settings.auth_cookie_is_secure,
        samesite=settings.auth_cookie_samesite,
    )


def read_refresh_cookie(request: Request) -> str | None:
    value = request.cookies.get(get_settings().auth_cookie_name)
    return value or None


def require_refresh_cookie(request: Request) -> str:
    token = read_refresh_cookie(request)
    if token is None:
        raise AuthenticationError(
            code="REFRESH_TOKEN_MISSING",
            message="No refresh token provided. Please log in again.",
        )
    return token
