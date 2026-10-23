"""FIX9 — WebSocket first-message auth (tokens out of the URL) + legacy query-token gating."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.api import ws as ws_module
from app.config import Settings
from app.realtime.manager import (
    CLOSE_POLICY_VIOLATION,
    CLOSE_SESSION_REVOKED,
    WebSocketManager,
)


def _settings(allow_query: bool = True, timeout: float = 2.0) -> SimpleNamespace:
    return SimpleNamespace(ws_allow_query_token=allow_query, ws_auth_timeout_seconds=timeout)


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(ws_module.router, prefix="/api/v1")
    return TestClient(app)


def _staff_user(role: str = "WAITER") -> SimpleNamespace:
    return SimpleNamespace(id=uuid.uuid4(), role=role)


def _customer_session() -> tuple[SimpleNamespace, None]:
    return SimpleNamespace(id=uuid.uuid4(), table_session_id=None), None


# ── First-message auth (preferred path) ───────────────────────────────────────


def test_first_message_staff_auth_succeeds() -> None:
    user = _staff_user("WAITER")
    with (
        patch("app.api.ws.get_settings", return_value=_settings()),
        patch("app.api.ws._authenticate_ws_staff", AsyncMock(return_value=user)) as auth,
        _client() as client,
        client.websocket_connect("/api/v1/ws") as ws,
    ):
        ws.send_json({"type": "auth", "token": "jwt-123"})
        ready = ws.receive_json()
    assert ready["event"] == "connection.ready"
    assert ready["role"] == "WAITER"
    auth.assert_awaited_once_with("jwt-123")


def test_first_message_invalid_staff_token_closes_4001() -> None:
    with (
        patch("app.api.ws.get_settings", return_value=_settings()),
        patch("app.api.ws._authenticate_ws_staff", AsyncMock(return_value=None)),
        _client() as client,
        client.websocket_connect("/api/v1/ws") as ws,
    ):
        ws.send_json({"type": "auth", "token": "bad"})
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == CLOSE_SESSION_REVOKED


def test_first_message_customer_auth_succeeds() -> None:
    cs, ts = _customer_session()
    with (
        patch("app.api.ws.get_settings", return_value=_settings()),
        patch("app.api.ws._authenticate_ws_customer", AsyncMock(return_value=(cs, ts))) as auth,
        _client() as client,
        client.websocket_connect("/api/v1/ws") as ws,
    ):
        ws.send_json({"type": "auth", "customer_token": "cust-raw-token"})
        ready = ws.receive_json()
    assert ready["event"] == "connection.ready"
    assert ready["role"] == "CUSTOMER"
    auth.assert_awaited_once_with("cust-raw-token")


def test_first_message_invalid_customer_token_closes_4001() -> None:
    with (
        patch("app.api.ws.get_settings", return_value=_settings()),
        patch("app.api.ws._authenticate_ws_customer", AsyncMock(return_value=None)),
        _client() as client,
        client.websocket_connect("/api/v1/ws") as ws,
    ):
        ws.send_json({"type": "auth", "customer_token": "bad"})
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == CLOSE_SESSION_REVOKED


def test_no_auth_frame_times_out_with_1008() -> None:
    with (
        patch("app.api.ws.get_settings", return_value=_settings(timeout=0.2)),
        _client() as client,
        client.websocket_connect("/api/v1/ws") as ws,
        pytest.raises(WebSocketDisconnect) as exc,
    ):
        ws.receive_json()
    assert exc.value.code == CLOSE_POLICY_VIOLATION


@pytest.mark.parametrize(
    "frame",
    [
        {"type": "ping"},  # first frame is not an auth frame
        {"type": "auth"},  # no credentials
        {"type": "auth", "token": "a", "customer_token": "b"},  # ambiguous
        {"type": "auth", "token": 123},  # wrong type
        {"type": "auth", "token": "a" * 5000},  # exceeds the 4 KB frame limit
    ],
)
def test_bad_first_frame_closes_1008(frame: dict[str, Any]) -> None:
    staff_auth = AsyncMock(return_value=_staff_user())
    with (
        patch("app.api.ws.get_settings", return_value=_settings()),
        patch("app.api.ws._authenticate_ws_staff", staff_auth),
        _client() as client,
        client.websocket_connect("/api/v1/ws") as ws,
    ):
        ws.send_json(frame)
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == CLOSE_POLICY_VIOLATION
    staff_auth.assert_not_awaited()


def test_non_json_first_frame_closes_1008() -> None:
    with (
        patch("app.api.ws.get_settings", return_value=_settings()),
        _client() as client,
        client.websocket_connect("/api/v1/ws") as ws,
    ):
        ws.send_text("this is not json")
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
    assert exc.value.code == CLOSE_POLICY_VIOLATION


def test_pending_pre_auth_cap_rejects_new_sockets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ws_module, "MAX_PENDING_PRE_AUTH", 0)
    with (
        patch("app.api.ws.get_settings", return_value=_settings()),
        _client() as client,
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect("/api/v1/ws"),
    ):
        pass


def test_pending_counter_is_released_after_auth() -> None:
    before = ws_module._pending_pre_auth
    with (
        patch("app.api.ws.get_settings", return_value=_settings()),
        patch("app.api.ws._authenticate_ws_staff", AsyncMock(return_value=_staff_user())),
        _client() as client,
        client.websocket_connect("/api/v1/ws") as ws,
    ):
        ws.send_json({"type": "auth", "token": "jwt"})
        ws.receive_json()
    assert ws_module._pending_pre_auth == before


# ── Header + legacy query token (rollout compatibility) ───────────────────────


def test_authorization_header_still_works() -> None:
    with (
        patch("app.api.ws.get_settings", return_value=_settings(allow_query=False)),
        patch("app.api.ws._authenticate_ws_staff", AsyncMock(return_value=_staff_user())) as auth,
        _client() as client,
        client.websocket_connect("/api/v1/ws", headers={"Authorization": "Bearer hdr-jwt"}) as ws,
    ):
        ready = ws.receive_json()
    assert ready["event"] == "connection.ready"
    auth.assert_awaited_once_with("hdr-jwt")


def test_legacy_query_token_allowed_while_flag_true() -> None:
    with (
        patch("app.api.ws.get_settings", return_value=_settings(allow_query=True)),
        patch("app.api.ws._authenticate_ws_staff", AsyncMock(return_value=_staff_user())) as auth,
        _client() as client,
        client.websocket_connect("/api/v1/ws?token=legacy-jwt") as ws,
    ):
        ready = ws.receive_json()
    assert ready["event"] == "connection.ready"
    auth.assert_awaited_once_with("legacy-jwt")


def test_legacy_customer_query_token_allowed_while_flag_true() -> None:
    cs, ts = _customer_session()
    with (
        patch("app.api.ws.get_settings", return_value=_settings(allow_query=True)),
        patch("app.api.ws._authenticate_ws_customer", AsyncMock(return_value=(cs, ts))),
        _client() as client,
        client.websocket_connect("/api/v1/ws?customer_token=legacy-cust") as ws,
    ):
        assert ws.receive_json()["role"] == "CUSTOMER"


@pytest.mark.parametrize("query", ["token=legacy-jwt", "customer_token=legacy-cust"])
def test_legacy_query_token_rejected_when_flag_false(query: str) -> None:
    staff_auth = AsyncMock(return_value=_staff_user())
    with (
        patch("app.api.ws.get_settings", return_value=_settings(allow_query=False)),
        patch("app.api.ws._authenticate_ws_staff", staff_auth),
        _client() as client,
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/api/v1/ws?{query}"),
    ):
        pass
    staff_auth.assert_not_awaited()


def test_first_message_auth_works_when_query_tokens_disabled() -> None:
    with (
        patch("app.api.ws.get_settings", return_value=_settings(allow_query=False)),
        patch("app.api.ws._authenticate_ws_staff", AsyncMock(return_value=_staff_user())),
        _client() as client,
        client.websocket_connect("/api/v1/ws") as ws,
    ):
        ws.send_json({"type": "auth", "token": "jwt"})
        assert ws.receive_json()["event"] == "connection.ready"


# ── Manager: no double accept ─────────────────────────────────────────────────


def _mock_ws() -> MagicMock:
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.close = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


async def test_manager_skips_accept_when_already_accepted() -> None:
    mgr = WebSocketManager()
    staff_ws = _mock_ws()
    assert await mgr.connect_staff(
        staff_ws, user_id=uuid.uuid4(), role="WAITER", already_accepted=True
    )
    staff_ws.accept.assert_not_awaited()

    cust_ws = _mock_ws()
    assert await mgr.connect_customer(
        cust_ws,
        customer_session_id=uuid.uuid4(),
        table_session_id=uuid.uuid4(),
        already_accepted=True,
    )
    cust_ws.accept.assert_not_awaited()


async def test_manager_still_accepts_by_default() -> None:
    mgr = WebSocketManager()
    ws = _mock_ws()
    assert await mgr.connect_staff(ws, user_id=uuid.uuid4(), role="KITCHEN")
    ws.accept.assert_awaited_once()


# ── Settings ──────────────────────────────────────────────────────────────────


def test_settings_defaults_keep_rollout_compatible() -> None:
    s = Settings()
    assert s.ws_allow_query_token is True
    assert s.ws_auth_timeout_seconds == 5.0


def test_settings_can_disable_query_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WS_ALLOW_QUERY_TOKEN", "false")
    monkeypatch.setenv("WS_AUTH_TIMEOUT_SECONDS", "8")
    s = Settings()
    assert s.ws_allow_query_token is False
    assert s.ws_auth_timeout_seconds == 8.0
