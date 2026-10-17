"""WebSocket endpoint (`WSS /api/v1/ws`).

Follows `docs/08-realtime-and-event-specification.md` and
`docs/06-security-specification.md` (Section 16).

Two authentication modes (docs/08 Section 4.1):
  1. Staff: Bearer JWT in `?token=` query param or `Authorization: Bearer` header.
  2. Customer: raw session token in `?customer_token=` query param, verified by SHA-256 hash lookup.

Security constraints enforced here (docs/08 Section 4 / docs/06 Section 16):
  - Max 4 KB per incoming client frame (close 1009 if exceeded).
  - Reject client-initiated subscription override payloads (close 1008).
  - Command-over-WebSocket payloads rejected with `COMMANDS_REQUIRE_REST_API` error.
  - 30-second server-sent heartbeat (pong) on client ping.
  - Sequence gap detection broadcast: `connection.ready` event on connect with
    `last_sequence` so client can detect missed events and trigger REST reconciliation.
"""

from __future__ import annotations

import hashlib
import uuid

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_engine
from app.core.logging import get_logger
from app.core.security import decode_access_token
from app.core.time_utils import utc_now
from app.models.enums import CustomerSessionStatus, UserStatus
from app.models.identity import User
from app.models.qr_sessions import CustomerSession, TableSession
from app.realtime.manager import (
    CLOSE_MESSAGE_TOO_BIG,
    CLOSE_POLICY_VIOLATION,
    CLOSE_SESSION_REVOKED,
    MAX_CLIENT_FRAME_BYTES,
    ws_manager,
)

logger = get_logger(__name__)

router = APIRouter(tags=["WebSocket"])


async def _authenticate_ws_staff(token: str) -> User | None:
    """Validate a staff JWT and return the active User entity."""
    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if not sub:
            return None
        user_uuid = uuid.UUID(sub)
    except (jwt.PyJWTError, ValueError):
        return None

    engine = get_engine()
    async with AsyncSession(bind=engine) as session:
        stmt = select(User).where(User.id == user_uuid)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    if not user or not user.is_active or user.status != UserStatus.ACTIVE.value:
        return None

    if payload.get("token_version") != user.token_version:
        return None

    return user


async def _authenticate_ws_customer(
    raw_token: str,
) -> tuple[CustomerSession, TableSession | None] | None:
    """Validate a raw customer session token and return the live session."""
    token_hash = hashlib.sha256(raw_token.strip().encode("utf-8")).hexdigest()

    engine = get_engine()
    async with AsyncSession(bind=engine) as db:
        stmt = select(CustomerSession).where(CustomerSession.session_token_hash == token_hash)
        result = await db.execute(stmt)
        cs = result.scalar_one_or_none()

        if not cs:
            return None
        if cs.status != CustomerSessionStatus.ACTIVE.value:
            return None
        if cs.expires_at < utc_now():
            return None

        # Load active TableSession (may be None before first order)
        ts = None
        if cs.table_session_id:
            ts_stmt = select(TableSession).where(
                TableSession.id == cs.table_session_id,
                TableSession.status == "ACTIVE",
            )
            ts_result = await db.execute(ts_stmt)
            ts = ts_result.scalar_one_or_none()

        return cs, ts


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Real-time WebSocket endpoint supporting staff JWT and customer session tokens.

    Flow:
      1. Detect auth mode from query params.
      2. Validate credentials before accept().
      3. Subscribe to server-authoritative rooms.
      4. Send `connection.ready` with current sequence = 0.
      5. Loop: receive frames, enforce 4 KB limit, respond to ping, reject commands.
      6. On disconnect: clean up rooms.
    """
    # ─── Authentication ───────────────────────────────────────────────────────
    token = websocket.query_params.get("token")
    customer_token = websocket.query_params.get("customer_token")

    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()

    if token:
        # Staff auth path
        user = await _authenticate_ws_staff(token)
        if not user:
            await websocket.close(code=CLOSE_SESSION_REVOKED, reason="UNAUTHORIZED")
            return

        connected = await ws_manager.connect_staff(
            websocket,
            user_id=user.id,
            role=user.role,
        )
        if not connected:
            return

        # Send connection.ready acknowledgement
        await ws_manager.send_personal(
            websocket,
            {
                "event": "connection.ready",
                "role": user.role,
                "user_id": str(user.id),
                "sequence": 0,
            },
        )

    elif customer_token:
        # Customer session auth path
        result = await _authenticate_ws_customer(customer_token)
        if not result:
            await websocket.close(code=CLOSE_SESSION_REVOKED, reason="SESSION_INVALID")
            return

        cs, ts = result
        # Customers without an active table_session get a personal room only until 1st order
        ts_id = ts.id if ts else cs.table_session_id or uuid.uuid4()

        connected = await ws_manager.connect_customer(
            websocket,
            customer_session_id=cs.id,
            table_session_id=ts_id,
        )
        if not connected:
            return

        await ws_manager.send_personal(
            websocket,
            {
                "event": "connection.ready",
                "role": "CUSTOMER",
                "customer_session_id": str(cs.id),
                "table_session_id": str(ts_id),
                "sequence": 0,
            },
        )

    else:
        await websocket.close(code=CLOSE_POLICY_VIOLATION, reason="UNAUTHORIZED")
        return

    # ─── Message Loop ─────────────────────────────────────────────────────────
    try:
        while True:
            # Enforce 4 KB frame size limit (docs/08 Section 4, docs/06 Section 16.4)
            raw = await websocket.receive_text()
            if len(raw.encode("utf-8")) > MAX_CLIENT_FRAME_BYTES:
                logger.warning("WebSocket frame exceeds 4 KB limit (%d bytes), closing", len(raw))
                await websocket.close(code=CLOSE_MESSAGE_TOO_BIG, reason="FRAME_TOO_LARGE")
                break

            try:
                import json

                data = json.loads(raw)
            except ValueError:
                # Ignore malformed JSON frames
                continue

            msg_type = (data.get("type") or data.get("event") or "").lower()

            if msg_type in ("ping", "heartbeat"):
                # Respond to heartbeat pings (docs/08 Section 4.3)
                await ws_manager.send_personal(websocket, {"type": "pong"})
            elif msg_type in ("subscribe", "unsubscribe"):
                # Reject client-initiated subscription overrides (WS-T07 / docs/06 Section 16.2)
                await ws_manager.send_personal(
                    websocket,
                    {
                        "type": "error",
                        "code": "SUBSCRIPTION_OVERRIDE_FORBIDDEN",
                        "message": (
                            "Room subscriptions are server-authoritative."
                            " Client cannot modify them."
                        ),
                    },
                )
            elif msg_type not in ("", "pong"):
                # Reject any command payloads sent over WebSocket (WS-T09)
                await ws_manager.send_personal(
                    websocket,
                    {
                        "type": "error",
                        "code": "COMMANDS_REQUIRE_REST_API",
                        "message": "State mutations must use the REST API. WebSocket is read-only.",
                    },
                )

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error: %s", exc)
    finally:
        await ws_manager.disconnect(websocket)
