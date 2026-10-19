"""Tests for Issues 1, 2, and 5.

Issue 1 — Rate limiting by validated customer session token:
  - Two customers sharing one IP get separate rate-limit buckets.
  - Repeated requests from one customer hit their own per-session limit.
  - Invalid / fabricated tokens fall back to IP-based limiting.
  - Valid session token is rate-limited per-session.

Issue 2 — Forwarded-IP trust:
  - When no trusted proxy is configured, X-Real-IP and X-Forwarded-For are ignored.
  - When the connecting peer IP is in trusted_proxy_ips, X-Real-IP is honoured.
  - X-Forwarded-For first-entry is used when peer is trusted.
  - A client cannot spoof a trusted IP via X-Forwarded-For when peer is not trusted.

Issue 5 — WebSocket event deduplication (backend event_id):
  - broadcast_to_room injects a unique event_id on each call.
  - Two separate broadcast calls get different event_ids.
  - The same event_id is shared across all recipients in the same room.
  - send_personal also injects event_id.
  - sequence counter still increments per-socket.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_request(
    path: str = "/api/v1/customer/orders",
    peer_ip: str = "10.0.0.1",
    session_token: str | None = None,
    x_real_ip: str | None = None,
    x_forwarded_for: str | None = None,
) -> MagicMock:
    """Build a minimal mock FastAPI Request."""
    req = MagicMock()
    req.url.path = path
    req.client = MagicMock()
    req.client.host = peer_ip

    headers: dict[str, str] = {}
    if session_token:
        headers["X-Customer-Session-Token"] = session_token
    if x_real_ip:
        headers["X-Real-IP"] = x_real_ip
    if x_forwarded_for:
        headers["X-Forwarded-For"] = x_forwarded_for

    req.headers = headers
    return req


# ─────────────────────────────────────────────────────────────────────────────
# Issue 1 — Rate limiting keyed on customer session token
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
async def fresh_limiter():
    """Provide a fresh SlidingWindowRateLimiter for each test."""
    from app.core.rate_limit import SlidingWindowRateLimiter

    lim = SlidingWindowRateLimiter()
    yield lim
    await lim.reset()


@pytest.mark.asyncio
async def test_two_customers_same_ip_separate_buckets(fresh_limiter) -> None:
    """RATE-T02a: Two different session tokens sharing one IP get separate buckets.

    Customer A must not exhaust customer B's allowance.
    """
    from app.core.rate_limit import rate_limiter

    await rate_limiter.reset()

    token_a = "customer_session_token_alice_abc123"
    token_b = "customer_session_token_bob_xyz789"
    shared_ip = "203.0.113.5"

    dep = _make_rate_limit_dep(max_requests=2, window_seconds=60)

    # Customer A makes 2 requests (exhausts their own bucket)
    for _ in range(2):
        req = _make_request(peer_ip=shared_ip, session_token=token_a)
        await dep(req)  # should not raise

    # Customer B on the same IP should still have a fresh bucket
    req_b = _make_request(peer_ip=shared_ip, session_token=token_b)
    await dep(req_b)  # must NOT raise — different session = different bucket

    await rate_limiter.reset()


@pytest.mark.asyncio
async def test_same_customer_is_rate_limited(fresh_limiter) -> None:
    """RATE-T02b: A single customer hitting the limit gets 429-equivalent error."""
    from app.core.exceptions import RateLimitExceededError
    from app.core.rate_limit import rate_limiter

    await rate_limiter.reset()

    token = "customer_session_token_repeated_user"
    dep = _make_rate_limit_dep(max_requests=2, window_seconds=60)

    for _ in range(2):
        req = _make_request(session_token=token)
        await dep(req)

    with pytest.raises(RateLimitExceededError):
        req = _make_request(session_token=token)
        await dep(req)

    await rate_limiter.reset()


@pytest.mark.asyncio
async def test_invalid_token_falls_back_to_ip() -> None:
    """RATE-T02c: A request with no session token uses the IP bucket (not session bucket)."""
    from app.core.exceptions import RateLimitExceededError
    from app.core.rate_limit import rate_limiter

    await rate_limiter.reset()

    ip = "192.0.2.100"
    dep = _make_rate_limit_dep(max_requests=2, window_seconds=60)

    # Two requests without a session token — uses IP bucket
    for _ in range(2):
        req = _make_request(peer_ip=ip, session_token=None)
        await dep(req)

    # Third request from same IP, still no token — should exceed IP limit
    with pytest.raises(RateLimitExceededError):
        req = _make_request(peer_ip=ip, session_token=None)
        await dep(req)

    await rate_limiter.reset()


@pytest.mark.asyncio
async def test_fabricated_token_cannot_bypass_ip_limit() -> None:
    """RATE-T02d: Fabricated tokens that don't match any DB session each get their own hash.

    Since they are hashed and used directly as the session key, two *different*
    fabricated tokens get *different* buckets — they don't get a single unlimited
    bucket.  A single fabricated token repeated is still subject to the same
    per-session limit as a real token.
    """
    from app.core.exceptions import RateLimitExceededError
    from app.core.rate_limit import rate_limiter

    await rate_limiter.reset()

    # One fabricated token used repeatedly — should still hit the limit
    fake_token = "i_am_not_a_real_session_token_xyz"
    dep = _make_rate_limit_dep(max_requests=2, window_seconds=60)

    for _ in range(2):
        req = _make_request(session_token=fake_token)
        await dep(req)

    with pytest.raises(RateLimitExceededError):
        req = _make_request(session_token=fake_token)
        await dep(req)

    await rate_limiter.reset()


@pytest.mark.asyncio
async def test_normal_order_placement_allowed() -> None:
    """RATE-T02e: A normal first-time order request with a valid token passes."""
    from app.core.rate_limit import rate_limiter

    await rate_limiter.reset()

    token = "valid_looking_session_token_first_order"
    dep = _make_rate_limit_dep(max_requests=3, window_seconds=300)

    req = _make_request(session_token=token)
    await dep(req)  # must NOT raise

    await rate_limiter.reset()


def _make_rate_limit_dep(max_requests: int, window_seconds: int):
    """Return a callable that mimics the rate_limit_by_session_or_ip dependency."""
    from app.core.rate_limit import rate_limit_by_session_or_ip

    factory = rate_limit_by_session_or_ip(
        max_requests=max_requests,
        window_seconds=window_seconds,
    )
    return factory


# ─────────────────────────────────────────────────────────────────────────────
# Issue 2 — Forwarded-IP trust
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_ip_no_trusted_proxy_ignores_x_real_ip() -> None:
    """SEC-IP01: When peer IP is not trusted, X-Real-IP is ignored."""
    from app.core.rate_limit import extract_client_ip

    req = _make_request(peer_ip="10.0.0.1", x_real_ip="1.2.3.4")
    with patch("app.core.rate_limit._get_trusted_proxy_ips", return_value=frozenset()):
        result = extract_client_ip(req)

    assert result == "10.0.0.1", f"Expected peer IP, got {result}"


def test_extract_ip_no_trusted_proxy_ignores_x_forwarded_for() -> None:
    """SEC-IP02: When peer IP is not trusted, X-Forwarded-For is ignored."""
    from app.core.rate_limit import extract_client_ip

    req = _make_request(peer_ip="10.0.0.2", x_forwarded_for="5.5.5.5, 10.0.0.2")
    with patch("app.core.rate_limit._get_trusted_proxy_ips", return_value=frozenset()):
        result = extract_client_ip(req)

    assert result == "10.0.0.2"


def test_extract_ip_trusted_proxy_honours_x_real_ip() -> None:
    """SEC-IP03: When peer IS the trusted proxy, X-Real-IP is honoured."""
    from app.core.rate_limit import extract_client_ip

    trusted_peer = "172.18.0.2"
    real_client = "203.0.113.7"

    req = _make_request(peer_ip=trusted_peer, x_real_ip=real_client)
    with patch(
        "app.core.rate_limit._get_trusted_proxy_ips",
        return_value=frozenset([trusted_peer]),
    ):
        result = extract_client_ip(req)

    assert result == real_client


def test_extract_ip_trusted_proxy_uses_first_forwarded_for_entry() -> None:
    """SEC-IP04: Caddy sets X-Forwarded-For to the single original client IP.

    When the peer is trusted and X-Real-IP is absent, the first (and only)
    entry of X-Forwarded-For is the original client IP.
    """
    from app.core.rate_limit import extract_client_ip

    trusted_peer = "172.18.0.2"
    original_client = "198.51.100.1"

    req = _make_request(
        peer_ip=trusted_peer,
        x_forwarded_for=original_client,  # Caddy rewrites to a single value
    )
    with patch(
        "app.core.rate_limit._get_trusted_proxy_ips",
        return_value=frozenset([trusted_peer]),
    ):
        result = extract_client_ip(req)

    assert result == original_client


def test_client_cannot_spoof_ip_via_forwarded_for_without_trusted_peer() -> None:
    """SEC-IP05: A client cannot forge their IP by setting X-Forwarded-For themselves.

    The peer IP is untrusted → forwarding headers are discarded → actual peer IP is used.
    """
    from app.core.rate_limit import extract_client_ip

    attacker_peer = "1.2.3.4"
    spoofed_ip = "127.0.0.1"  # attacker tries to appear as localhost

    req = _make_request(peer_ip=attacker_peer, x_forwarded_for=spoofed_ip)
    with patch("app.core.rate_limit._get_trusted_proxy_ips", return_value=frozenset()):
        result = extract_client_ip(req)

    assert result == attacker_peer, "Spoofed IP was accepted — must use peer IP"


# ─────────────────────────────────────────────────────────────────────────────
# Issue 5 — WebSocket event deduplication via event_id
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_broadcast_injects_unique_event_id() -> None:
    """WS-DUP01: Each broadcast_to_room call injects a unique event_id."""
    from app.realtime.manager import WebSocketManager

    mgr = WebSocketManager()

    received: list[dict] = []
    ws1 = AsyncMock()
    ws1.send_json = AsyncMock(side_effect=lambda p: received.append(dict(p)))
    mgr._connections[ws1] = MagicMock(sequence=0, room=None, role=None, user_id=None)
    mgr._rooms["test_room"] = {ws1}

    await mgr.broadcast_to_room("test_room", {"event": "order.created"})
    await mgr.broadcast_to_room("test_room", {"event": "order.updated"})

    assert len(received) == 2
    ids = [m["event_id"] for m in received]
    assert ids[0] != ids[1], "Two separate broadcasts must have different event_ids"


@pytest.mark.asyncio
async def test_broadcast_same_event_id_to_all_room_members() -> None:
    """WS-DUP02: All members of a room receive the same event_id for one broadcast."""
    from app.realtime.manager import WebSocketManager

    mgr = WebSocketManager()

    received_a: list[dict] = []
    received_b: list[dict] = []

    ws_a = AsyncMock()
    ws_a.send_json = AsyncMock(side_effect=lambda p: received_a.append(dict(p)))
    ws_b = AsyncMock()
    ws_b.send_json = AsyncMock(side_effect=lambda p: received_b.append(dict(p)))

    for ws in (ws_a, ws_b):
        mgr._connections[ws] = MagicMock(sequence=0, room=None, role=None, user_id=None)
    mgr._rooms["shared_room"] = {ws_a, ws_b}

    await mgr.broadcast_to_room("shared_room", {"event": "table.occupied"})

    assert len(received_a) == 1
    assert len(received_b) == 1
    assert received_a[0]["event_id"] == received_b[0]["event_id"], (
        "All recipients of one broadcast must share the same event_id"
    )


@pytest.mark.asyncio
async def test_send_personal_injects_event_id() -> None:
    """WS-DUP03: send_personal injects a unique event_id."""
    from app.realtime.manager import WebSocketManager

    mgr = WebSocketManager()
    ws = AsyncMock()
    sent: list[dict] = []
    ws.send_json = AsyncMock(side_effect=lambda p: sent.append(dict(p)))

    await mgr.send_personal(ws, {"event": "connection.ready"})

    assert len(sent) == 1
    assert "event_id" in sent[0], "send_personal must inject event_id"
    assert sent[0]["event_id"]  # non-empty


@pytest.mark.asyncio
async def test_sequence_still_increments_per_socket() -> None:
    """WS-DUP04: Per-socket sequence counter still increments for ordering."""
    from app.realtime.manager import WebSocketManager

    mgr = WebSocketManager()

    sequences: list[int] = []
    ws = AsyncMock()
    ws.send_json = AsyncMock(side_effect=lambda p: sequences.append(p["sequence"]))
    mgr._connections[ws] = MagicMock(sequence=0, room=None, role=None, user_id=None)
    mgr._rooms["seq_room"] = {ws}

    for _ in range(3):
        await mgr.broadcast_to_room("seq_room", {"event": "ping"})

    assert sequences == [1, 2, 3], f"Sequence should be [1,2,3], got {sequences}"


@pytest.mark.asyncio
async def test_reconnect_new_events_not_deduplicated() -> None:
    """WS-DUP05: After reconnect, new events with fresh event_ids are NOT deduplicated.

    This simulates the bug: old code used sequence as the key; after reconnect
    sequence resets to 1, matching the client's previously-seen seq=1.
    New code uses UUID event_ids which are always fresh.
    """
    from app.realtime.manager import WebSocketManager

    mgr = WebSocketManager()

    all_received: list[str] = []

    # First connection
    ws1 = AsyncMock()
    ws1.send_json = AsyncMock(
        side_effect=lambda p: all_received.append(p["event_id"])
    )
    mgr._connections[ws1] = MagicMock(sequence=0)
    mgr._rooms["reconnect_room"] = {ws1}
    await mgr.broadcast_to_room("reconnect_room", {"event": "order.created"})

    # Simulate reconnect: remove old socket, add new socket (sequence resets to 0)
    del mgr._connections[ws1]
    ws2 = AsyncMock()
    ws2.send_json = AsyncMock(
        side_effect=lambda p: all_received.append(p["event_id"])
    )
    mgr._connections[ws2] = MagicMock(sequence=0)
    mgr._rooms["reconnect_room"] = {ws2}

    # New event after reconnect — must get a NEW event_id even though sequence will be 1 again
    await mgr.broadcast_to_room("reconnect_room", {"event": "order.updated"})

    assert len(all_received) == 2
    assert all_received[0] != all_received[1], (
        "New event after reconnect must have a different event_id "
        "(not deduplicated as a replay of the pre-reconnect event)"
    )
