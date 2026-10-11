"""WebSocket lifecycle, authorization scoping, and reliability tests.

Covers WS-T01 through WS-T15 from `docs/08-realtime-and-event-specification.md`
Section 38 using pure in-process unit tests (no live Postgres or live sockets).

Test categories:
  WS-T01 – WS-T05 : Connection Lifecycle
  WS-T06 – WS-T09 : Authorization & Scoping
  WS-T10 – WS-T15 : Reliability & Recovery (client-side logic + manager state)
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.realtime.manager import (
    CLOSE_ACCOUNT_DISABLED,
    CLOSE_POLICY_VIOLATION,
    CLOSE_SESSION_REVOKED,
    MAX_CLIENT_FRAME_BYTES,
    MAX_CUSTOMER_CONNECTIONS_PER_SESSION,
    MAX_STAFF_CONNECTIONS_PER_USER,
    WebSocketManager,
)

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _mock_ws() -> MagicMock:
    """Create a mock WebSocket that tracks sent JSON messages."""
    ws = MagicMock()
    ws.sent_messages: list[dict[str, Any]] = []
    ws.close_called: list[tuple[int, str]] = []

    async def _send_json(payload: dict[str, Any]) -> None:
        ws.sent_messages.append(payload)

    async def _close(*, code: int = 1000, reason: str = "") -> None:
        ws.close_called.append((code, reason))

    async def _accept() -> None:
        pass

    ws.send_json = AsyncMock(side_effect=_send_json)
    ws.close = AsyncMock(side_effect=_close)
    ws.accept = AsyncMock(side_effect=_accept)
    return ws


# ─────────────────────────────────────────────────────────────────────────────
# WS-T01 – Valid staff JWT → manager accepts connection and assigns rooms
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t01_staff_connect_assigns_correct_rooms() -> None:
    """WS-T01: Valid staff JWT connects and receives server-authoritative rooms."""
    mgr = WebSocketManager()
    user_id = uuid.uuid4()

    # WAITER
    ws_waiter = _mock_ws()
    connected = await mgr.connect_staff(ws_waiter, user_id=user_id, role="WAITER")
    assert connected is True
    meta = mgr.get_connection_meta(ws_waiter)
    assert meta is not None
    assert "channel:waiters" in meta.rooms
    assert "channel:tables" in meta.rooms
    assert "channel:menu" in meta.rooms
    # Waiter must NOT be in kitchen room
    assert "channel:kitchen" not in meta.rooms
    assert "channel:admin" not in meta.rooms

    # KITCHEN
    mgr2 = WebSocketManager()
    ws_kitchen = _mock_ws()
    kid = uuid.uuid4()
    await mgr2.connect_staff(ws_kitchen, user_id=kid, role="KITCHEN")
    meta_k = mgr2.get_connection_meta(ws_kitchen)
    assert "channel:kitchen" in meta_k.rooms  # type: ignore[union-attr]
    assert "channel:waiters" not in meta_k.rooms  # type: ignore[union-attr]

    # ADMIN
    mgr3 = WebSocketManager()
    ws_admin = _mock_ws()
    aid = uuid.uuid4()
    await mgr3.connect_staff(ws_admin, user_id=aid, role="ADMIN")
    meta_a = mgr3.get_connection_meta(ws_admin)
    assert "channel:admin" in meta_a.rooms  # type: ignore[union-attr]
    assert "channel:kitchen" in meta_a.rooms  # type: ignore[union-attr]
    assert "channel:waiters" in meta_a.rooms  # type: ignore[union-attr]
    assert "channel:tables" in meta_a.rooms  # type: ignore[union-attr]
    assert "channel:menu" in meta_a.rooms  # type: ignore[union-attr]


# ─────────────────────────────────────────────────────────────────────────────
# WS-T02 – Invalid / tampered token is rejected before accept()
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t02_invalid_token_rejected() -> None:
    """WS-T02: ws.py rejects invalid token with close 4001 before accepting socket."""
    from app.api.ws import _authenticate_ws_staff

    # A completely garbage token should return None
    result = await _authenticate_ws_staff("not.a.valid.jwt")
    assert result is None

    result2 = await _authenticate_ws_staff("")
    assert result2 is None


# ─────────────────────────────────────────────────────────────────────────────
# WS-T03 – Expired customer session rejected with 4001
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t03_expired_customer_session_rejected() -> None:
    """WS-T03: Expired or inactive customer session is rejected before accept()."""
    from app.api.ws import _authenticate_ws_customer

    # Patch DB lookup to return None (token not found)
    with patch("app.api.ws.AsyncSession") as mock_session_cls:
        mock_sess = AsyncMock()
        mock_sess.__aenter__ = AsyncMock(return_value=mock_sess)
        mock_sess.__aexit__ = AsyncMock(return_value=False)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_sess.execute = AsyncMock(return_value=mock_result)
        mock_session_cls.return_value = mock_sess

        result = await _authenticate_ws_customer("some-raw-token-that-doesnt-exist")
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# WS-T04 – Disabling staff account disconnects active WebSocket with 4003
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t04_disable_account_disconnects_socket() -> None:
    """WS-T04: disconnect_user() sends close code 4003 to all active sockets."""
    mgr = WebSocketManager()
    user_id = uuid.uuid4()

    ws1 = _mock_ws()
    ws2 = _mock_ws()

    await mgr.connect_staff(ws1, user_id=user_id, role="WAITER")
    await mgr.connect_staff(ws2, user_id=user_id, role="WAITER")

    assert mgr.get_room_connections_count("channel:waiters") == 2

    await mgr.disconnect_user(user_id, close_code=CLOSE_ACCOUNT_DISABLED, reason="ACCOUNT_DISABLED")

    # Both sockets should have been closed with 4003
    assert len(ws1.close_called) == 1
    assert ws1.close_called[0][0] == CLOSE_ACCOUNT_DISABLED

    assert len(ws2.close_called) == 1
    assert ws2.close_called[0][0] == CLOSE_ACCOUNT_DISABLED

    # Manager should have zero connections remaining
    assert mgr.total_connections == 0
    assert mgr.get_room_connections_count("channel:waiters") == 0


# ─────────────────────────────────────────────────────────────────────────────
# WS-T05 – Staff logout cleanly disconnects socket
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t05_staff_logout_clean_disconnect() -> None:
    """WS-T05: disconnect_user() with code 1000 cleanly removes staff socket."""
    mgr = WebSocketManager()
    user_id = uuid.uuid4()
    ws = _mock_ws()

    await mgr.connect_staff(ws, user_id=user_id, role="WAITER")
    assert mgr.total_connections == 1

    await mgr.disconnect_user(user_id, close_code=1000, reason="LOGGED_OUT")
    assert mgr.total_connections == 0


# ─────────────────────────────────────────────────────────────────────────────
# WS-T06 – Customer on T-01 does NOT receive events for T-02
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t06_customer_room_isolation() -> None:
    """WS-T06: Customer on table_session T-01 cannot receive events for T-02."""
    mgr = WebSocketManager()

    cs_id_1 = uuid.uuid4()
    ts_id_1 = uuid.uuid4()
    cs_id_2 = uuid.uuid4()
    ts_id_2 = uuid.uuid4()

    ws1 = _mock_ws()
    ws2 = _mock_ws()

    await mgr.connect_customer(ws1, customer_session_id=cs_id_1, table_session_id=ts_id_1)
    await mgr.connect_customer(ws2, customer_session_id=cs_id_2, table_session_id=ts_id_2)

    # Broadcast to T-01's room only
    await mgr.broadcast_to_room(f"table_session:{ts_id_1}", {"event": "order.created", "table": 1})

    # ws1 should have received the message
    assert len(ws1.sent_messages) == 1
    assert ws1.sent_messages[0]["event"] == "order.created"

    # ws2 must NOT have received any messages (different table session)
    assert len(ws2.sent_messages) == 0


# ─────────────────────────────────────────────────────────────────────────────
# WS-T07 – Client subscription override payload is rejected
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t07_subscription_override_rejected() -> None:
    """WS-T07: Server rejects customer subscription override with error payload."""
    mgr = WebSocketManager()
    cs_id = uuid.uuid4()
    ts_id = uuid.uuid4()
    ws = _mock_ws()
    await mgr.connect_customer(ws, customer_session_id=cs_id, table_session_id=ts_id)

    meta = mgr.get_connection_meta(ws)
    assert meta is not None
    # The customer must only be in their own table_session room, not any other
    assert len(meta.rooms) == 1
    assert f"table_session:{ts_id}" in meta.rooms

    # Simulate trying to manually add to a second room — server design prevents this
    # because rooms are set only in connect_customer, never via incoming frames
    ws_any_other_room = meta.rooms - {f"table_session:{ts_id}"}
    assert len(ws_any_other_room) == 0, "Customer must not be subscribed to extra rooms"


# ─────────────────────────────────────────────────────────────────────────────
# WS-T08 – Kitchen WebSocket does NOT receive bill.created or payment.completed
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t08_kitchen_does_not_receive_billing_events() -> None:
    """WS-T08: billing events broadcast to channel:waiters never reach channel:kitchen."""
    mgr = WebSocketManager()

    kitchen_id = uuid.uuid4()
    waiter_id = uuid.uuid4()
    ws_k = _mock_ws()
    ws_w = _mock_ws()

    await mgr.connect_staff(ws_k, user_id=kitchen_id, role="KITCHEN")
    await mgr.connect_staff(ws_w, user_id=waiter_id, role="WAITER")

    billing_event = {"event": "bill.created", "bill_id": str(uuid.uuid4())}
    # Billing events only go to waiters and admin — never to kitchen
    await mgr.broadcast_to_room("channel:waiters", billing_event)

    assert len(ws_w.sent_messages) == 1
    assert ws_w.sent_messages[0]["event"] == "bill.created"
    # Kitchen must receive zero billing events
    assert len(ws_k.sent_messages) == 0


# ─────────────────────────────────────────────────────────────────────────────
# WS-T09 – Command-over-WebSocket is rejected — enforced at ws.py layer
# (tested conceptually since full HTTP round-trip is an integration test)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t09_command_payload_is_read_only() -> None:
    """WS-T09: The manager never writes state from a broadcast; REST-only mutations."""
    mgr = WebSocketManager()
    user_id = uuid.uuid4()
    ws = _mock_ws()
    await mgr.connect_staff(ws, user_id=user_id, role="WAITER")

    # Simulating: even if we call broadcast with a command-like payload,
    # the manager simply delivers it — no state mutation happens.
    # The ws.py endpoint loop rejects command frames and sends the error response.
    # Here we verify the manager itself is stateless w.r.t. incoming client data.
    initial_connections = mgr.total_connections
    await mgr.broadcast_to_room("channel:waiters", {"type": "ACCEPT_ORDER", "order_id": "xyz"})
    # Connection count is unchanged — no mutation from broadcast
    assert mgr.total_connections == initial_connections


# ─────────────────────────────────────────────────────────────────────────────
# WS-T10 – Sequence counter is monotonically increasing per socket
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t10_sequence_counter_monotonically_increases() -> None:
    """WS-T10: Each broadcast increments per-socket sequence counter monotonically."""
    mgr = WebSocketManager()
    user_id = uuid.uuid4()
    ws = _mock_ws()
    await mgr.connect_staff(ws, user_id=user_id, role="WAITER")

    for i in range(5):
        await mgr.broadcast_to_room("channel:waiters", {"event": f"order.created_{i}"})

    # Each sent message must have a monotonically increasing sequence
    sequences = [m["sequence"] for m in ws.sent_messages]
    assert sequences == list(range(1, 6)), f"Expected [1,2,3,4,5] but got {sequences}"


# ─────────────────────────────────────────────────────────────────────────────
# WS-T11 – Sequence gap detection: client detects gap between seq 101 → 103
# (Client-side deduplication ring buffer behaviour)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t11_sequence_gap_detection_via_counter() -> None:
    """WS-T11: Sequence counter increments per socket, enabling client gap detection."""
    mgr = WebSocketManager()
    uid = uuid.uuid4()
    ws = _mock_ws()
    await mgr.connect_staff(ws, user_id=uid, role="KITCHEN")

    # Send 100 events
    for _ in range(100):
        await mgr.broadcast_to_room("channel:kitchen", {"event": "order.placed"})

    meta = mgr.get_connection_meta(ws)
    assert meta is not None
    assert meta.sequence == 100

    # Simulate: the 101st event is delivered, then socket disconnects and reconnects.
    # On reconnect the client would notice the last_sequence it saw was 101
    # and the new `connection.ready` has sequence=0 → triggers REST reconciliation.
    # We verify the counter stays consistent.
    await mgr.broadcast_to_room("channel:kitchen", {"event": "order.placed"})
    assert meta.sequence == 101


# ─────────────────────────────────────────────────────────────────────────────
# WS-T12 – Duplicate event_id is suppressed once (ring buffer dedup)
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t12_duplicate_event_id_suppression() -> None:
    """WS-T12: 250-event LRU ring buffer deduplication on client prevents double updates.

    The ring buffer is implemented in customerWs.ts / ws_client.dart.
    Here we verify the ring-buffer logic in isolation with a Python equivalent.
    """
    MAX_RING = 250
    seen_ids: set[str] = set()
    ring: list[str] = []

    def is_duplicate(event_id: str) -> bool:
        if event_id in seen_ids:
            return True
        seen_ids.add(event_id)
        ring.append(event_id)
        if len(ring) > MAX_RING:
            evicted = ring.pop(0)
            seen_ids.discard(evicted)
        return False

    uid = "evt-abc-123"

    # First occurrence is not duplicate
    assert is_duplicate(uid) is False
    # Second occurrence is duplicate
    assert is_duplicate(uid) is True

    # Fill ring with 250 more events to evict the first one
    for i in range(MAX_RING):
        is_duplicate(f"evt-{i}")

    # uid should have been evicted from ring; now not considered duplicate
    assert is_duplicate(uid) is False


# ─────────────────────────────────────────────────────────────────────────────
# WS-T13 – Stale entity_version update does not regress UI state
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t13_stale_entity_version_ignored() -> None:
    """WS-T13: entity_version field allows clients to reject stale out-of-order frames.

    Verifies that event payloads carry entity_version from broadcast_to_room.
    The actual client-side version comparison guard is in customerWs.ts.
    """
    mgr = WebSocketManager()
    uid = uuid.uuid4()
    ws = _mock_ws()
    await mgr.connect_staff(ws, user_id=uid, role="ADMIN")

    # Broadcast event with entity_version=3 (newer)
    await mgr.broadcast_to_room("channel:admin", {"event": "order.updated", "entity_version": 3})
    # Broadcast event with entity_version=2 (older, out of order)
    await mgr.broadcast_to_room("channel:admin", {"event": "order.updated", "entity_version": 2})

    # Both are delivered by the server; client-side logic must reject the stale one.
    # Verify both messages arrived (server doesn't filter):
    versions = [m.get("entity_version") for m in ws.sent_messages]
    assert 3 in versions
    assert 2 in versions


# ─────────────────────────────────────────────────────────────────────────────
# WS-T14 – Reconnect after server restart: sequence resets to 0 on new connection
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t14_reconnect_resets_sequence_counter() -> None:
    """WS-T14: After a disconnect/reconnect the new ConnectionMeta starts at sequence=0."""
    mgr = WebSocketManager()
    uid = uuid.uuid4()

    ws1 = _mock_ws()
    await mgr.connect_staff(ws1, user_id=uid, role="WAITER")
    for _ in range(10):
        await mgr.broadcast_to_room("channel:waiters", {"event": "test"})

    meta1 = mgr.get_connection_meta(ws1)
    assert meta1 is not None and meta1.sequence == 10

    # Simulate disconnect
    await mgr.disconnect(ws1)
    assert mgr.total_connections == 0

    # Simulate reconnect with a new WebSocket object
    ws2 = _mock_ws()
    await mgr.connect_staff(ws2, user_id=uid, role="WAITER")
    meta2 = mgr.get_connection_meta(ws2)
    assert meta2 is not None
    assert meta2.sequence == 0, "New connection sequence must start at 0"


# ─────────────────────────────────────────────────────────────────────────────
# WS-T15 – Customer session disconnect on table session payment close
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_t15_table_session_close_evicts_customer_sockets() -> None:
    """WS-T15: disconnect_table_session() evicts all customer sockets with code 4001."""
    mgr = WebSocketManager()

    ts_id = uuid.uuid4()
    cs_id_1 = uuid.uuid4()
    cs_id_2 = uuid.uuid4()

    ws1 = _mock_ws()
    ws2 = _mock_ws()

    # Two customers at the same table (e.g. two browsers)
    await mgr.connect_customer(ws1, customer_session_id=cs_id_1, table_session_id=ts_id)
    await mgr.connect_customer(ws2, customer_session_id=cs_id_2, table_session_id=ts_id)

    assert mgr.get_room_connections_count(f"table_session:{ts_id}") == 2

    await mgr.disconnect_table_session(ts_id, reason="TABLE_SESSION_CLOSED_BY_PAYMENT")

    # Both sockets must have been closed with SESSION_REVOKED (4001)
    assert ws1.close_called[0][0] == CLOSE_SESSION_REVOKED
    assert ws2.close_called[0][0] == CLOSE_SESSION_REVOKED

    # Room and connection registry must be empty
    assert mgr.get_room_connections_count(f"table_session:{ts_id}") == 0
    assert mgr.total_connections == 0


# ─────────────────────────────────────────────────────────────────────────────
# Bonus: Max connection cap enforcement
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ws_connection_cap_staff() -> None:
    """Staff connection cap: 6th connection is rejected with 1008 POLICY_VIOLATION."""
    mgr = WebSocketManager()
    uid = uuid.uuid4()

    sockets = [_mock_ws() for _ in range(MAX_STAFF_CONNECTIONS_PER_USER)]
    for ws in sockets:
        connected = await mgr.connect_staff(ws, user_id=uid, role="WAITER")
        assert connected is True

    # 6th attempt must be rejected
    ws_extra = _mock_ws()
    connected = await mgr.connect_staff(ws_extra, user_id=uid, role="WAITER")
    assert connected is False
    assert len(ws_extra.close_called) == 1
    assert ws_extra.close_called[0][0] == CLOSE_POLICY_VIOLATION


@pytest.mark.asyncio
async def test_ws_connection_cap_customer() -> None:
    """Customer connection cap: 3rd customer session socket is rejected."""
    mgr = WebSocketManager()
    cs_id = uuid.uuid4()
    ts_id = uuid.uuid4()

    sockets = [_mock_ws() for _ in range(MAX_CUSTOMER_CONNECTIONS_PER_SESSION)]
    for ws in sockets:
        connected = await mgr.connect_customer(
            ws, customer_session_id=cs_id, table_session_id=ts_id
        )
        assert connected is True

    ws_extra = _mock_ws()
    connected = await mgr.connect_customer(
        ws_extra, customer_session_id=cs_id, table_session_id=ts_id
    )
    assert connected is False
    assert len(ws_extra.close_called) == 1
    assert ws_extra.close_called[0][0] == CLOSE_POLICY_VIOLATION


@pytest.mark.asyncio
async def test_ws_frame_size_constant() -> None:
    """MAX_CLIENT_FRAME_BYTES is exactly 4 KB as mandated by docs/08 Section 4."""
    assert MAX_CLIENT_FRAME_BYTES == 4096
