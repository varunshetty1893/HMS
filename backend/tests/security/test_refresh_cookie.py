"""Opt-in httpOnly refresh-token cookie (`X-Auth-Transport: cookie`) for the admin web."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator, Iterator
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.config import Settings
from app.core.database import get_db
from app.core.dependencies import get_current_staff_user
from app.main import app
from app.schemas.auth import StaffTokenResponse, StaffUserResponse
from app.services.auth_service import AuthService

pytestmark = pytest.mark.asyncio

ORIGIN = "http://localhost:3000"  # in the default CORS_ALLOWED_ORIGINS
COOKIE_HEADERS = {
    "X-Auth-Transport": "cookie",
    "X-Requested-With": "hms-admin-web",
    "Origin": ORIGIN,
}


def _tokens(refresh: str = "raw-refresh-1") -> StaffTokenResponse:
    return StaffTokenResponse(
        access_token="access-1",
        refresh_token=refresh,
        user=StaffUserResponse(
            id=uuid.uuid4(),
            username="admin",
            full_name="Admin",
            role="ADMIN",
            status="ACTIVE",
        ),
    )


@pytest.fixture(autouse=True)
def _overrides() -> Iterator[None]:
    async def fake_db() -> AsyncGenerator[Any, None]:
        yield AsyncMock()

    app.dependency_overrides[get_db] = fake_db
    app.dependency_overrides[get_current_staff_user] = lambda: SimpleNamespace(
        id=uuid.uuid4(), role="ADMIN"
    )
    yield
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff_user, None)


LOGIN = {"username": "admin", "password": "password123", "client_type": "ADMIN_WEB"}


async def test_cookie_login_sets_httponly_cookie_and_hides_token_from_body(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(AuthService, "login", AsyncMock(return_value=_tokens()))
    resp = await async_client.post("/api/v1/auth/login", json=LOGIN, headers=COOKIE_HEADERS)

    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == "access-1"
    assert body["refresh_token"] == ""  # never readable by page scripts
    cookie = resp.headers["set-cookie"]
    assert "hms_refresh=raw-refresh-1" in cookie
    assert "HttpOnly" in cookie
    assert "Path=/api/v1/auth" in cookie
    assert "SameSite=lax" in cookie


async def test_legacy_login_still_returns_token_in_body_and_sets_no_cookie(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(AuthService, "login", AsyncMock(return_value=_tokens()))
    resp = await async_client.post("/api/v1/auth/login", json=LOGIN)  # Flutter apps

    assert resp.status_code == 200
    assert resp.json()["refresh_token"] == "raw-refresh-1"
    assert "set-cookie" not in resp.headers


async def test_cookie_mode_requires_the_anti_csrf_header(async_client: AsyncClient) -> None:
    headers = {k: v for k, v in COOKIE_HEADERS.items() if k != "X-Requested-With"}
    resp = await async_client.post("/api/v1/auth/login", json=LOGIN, headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_CHECK_FAILED"


async def test_cookie_mode_rejects_foreign_origin(async_client: AsyncClient) -> None:
    headers = {**COOKIE_HEADERS, "Origin": "https://evil.example"}
    resp = await async_client.post(
        "/api/v1/auth/refresh", headers=headers, cookies={"hms_refresh": "x"}
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "CSRF_ORIGIN_NOT_ALLOWED"


async def test_refresh_reads_cookie_and_rotates_it(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    refresh = AsyncMock(return_value=_tokens("raw-refresh-2"))
    monkeypatch.setattr(AuthService, "refresh_tokens", refresh)

    resp = await async_client.post(
        "/api/v1/auth/refresh", headers=COOKIE_HEADERS, cookies={"hms_refresh": "raw-refresh-1"}
    )

    assert resp.status_code == 200
    assert refresh.await_args.args[1].refresh_token == "raw-refresh-1"
    assert resp.json()["refresh_token"] == ""
    assert "hms_refresh=raw-refresh-2" in resp.headers["set-cookie"]


async def test_cookie_refresh_without_cookie_is_401(async_client: AsyncClient) -> None:
    resp = await async_client.post("/api/v1/auth/refresh", headers=COOKIE_HEADERS)
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "REFRESH_TOKEN_MISSING"


async def test_legacy_refresh_with_body_token_still_works(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(AuthService, "refresh_tokens", AsyncMock(return_value=_tokens("r2")))
    resp = await async_client.post("/api/v1/auth/refresh", json={"refresh_token": "r1"})
    assert resp.status_code == 200
    assert resp.json()["refresh_token"] == "r2"
    assert "set-cookie" not in resp.headers


async def test_legacy_refresh_without_any_token_is_401(async_client: AsyncClient) -> None:
    resp = await async_client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401


async def test_cookie_logout_revokes_cookie_token_and_clears_cookie(
    async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    logout = AsyncMock(return_value=None)
    monkeypatch.setattr(AuthService, "logout", logout)

    resp = await async_client.post(
        "/api/v1/auth/logout", headers=COOKIE_HEADERS, cookies={"hms_refresh": "raw-refresh-1"}
    )

    assert resp.status_code == 200
    assert logout.await_args.args[2].refresh_token == "raw-refresh-1"
    cleared = resp.headers["set-cookie"]
    assert "hms_refresh=" in cleared and "Max-Age=0" in cleared


def test_cookie_secure_defaults() -> None:
    assert Settings(environment="development").auth_cookie_is_secure is False
    assert Settings(auth_cookie_secure=True).auth_cookie_is_secure is True
    # SameSite=None is only accepted by browsers together with Secure.
    assert Settings(auth_cookie_samesite="none", auth_cookie_secure=False).auth_cookie_is_secure


def test_blank_cookie_secure_env_value_means_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_COOKIE_SECURE", "")
    assert Settings(_env_file=None).auth_cookie_secure is None
