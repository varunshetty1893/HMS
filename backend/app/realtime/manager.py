"""In-process WebSocket connection manager with room isolation and heartbeat tracking.

Follows `docs/08-realtime-and-event-specification.md` (Sections 4 & 5),
`docs/06-security-specification.md` (Section 16), and
`docs/10-deployment-and-devops-specification.md`.
Enforces server-authoritative room assignment and protects against cross-role message leakage.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

from app.core.logging import get_logger
from app.models.enums import UserRole

logger = get_logger(__name__)

# Close codes defined in docs/06 and docs/08:
CLOSE_POLICY_VIOLATION = 1008
CLOSE_MESSAGE_TOO_BIG = 1009
CLOSE_ACCOUNT_DISABLED = 4003
CLOSE_SESSION_REVOKED = 4001
CLOSE_RATE_LIMITED = 4008

# docs/08 Section 4 — max 4 KB per frame from any client
MAX_CLIENT_FRAME_BYTES = 4 * 1024

# docs/08 Section 4 — max 5 concurrent sockets per staff user
MAX_STAFF_CONNECTIONS_PER_USER = 5

# docs/08 Section 4 — max 2 concurrent sockets per customer session
MAX_CUSTOMER_CONNECTIONS_PER_SESSION = 2


@dataclass
class ConnectionMeta:
    """Metadata for an active in-process WebSocket connection."""

    websocket: WebSocket
    user_id: uuid.UUID | None = None
    customer_session_id: uuid.UUID | None = None
    table_session_id: uuid.UUID | None = None
    role: str = "ANONYMOUS"
    rooms: set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # Per-socket monotonically-increasing sequence counter (docs/08 Section 3.2)
    sequence: int = 0


class WebSocketManager:
    """In-memory, single-worker WebSocket manager with role-based room registries.

    Room taxonomy (docs/08 Section 4.2):
        channel:kitchen   — Kitchen staff only
        channel:waiters   — Waiter staff only
        channel:admin     — Admin staff only
        channel:tables    — Table availability events (waiters + admin)
        channel:menu      — Menu availability events (all staff + kitchen)
        table_session:{uuid} — Per-session customer socket room
        user:{uuid}       — Per-staff-user personal delivery room
    """

    def __init__(self) -> None:
        self._connections: dict[WebSocket, ConnectionMeta] = {}
        self._rooms: dict[str, set[WebSocket]] = {}
        self._user_connections: dict[uuid.UUID, set[WebSocket]] = {}
        self._customer_connections: dict[uuid.UUID, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    @property
    def total_connections(self) -> int:
        """Total active WebSocket connections."""
        return len(self._connections)

    def get_room_connections_count(self, room: str) -> int:
        """Count of active connections in a specific room."""
        return len(self._rooms.get(room, set()))

    async def connect_staff(
        self,
        websocket: WebSocket,
        *,
        user_id: uuid.UUID,
        role: str,
        already_accepted: bool = False,
    ) -> bool:
        """Accept an authenticated staff WebSocket and assign server-authoritative rooms.

        ``already_accepted`` is True when the handshake was accepted earlier so the client
        could send its first-message auth frame (the socket is then NOT accepted again).

        Returns True if accepted, or False if max connection limit is exceeded.
        """
        async with self._lock:
            # Enforce max 5 concurrent sockets per staff user (docs/06 Section 16)
            existing = self._user_connections.get(user_id, set())
            if len(existing) >= MAX_STAFF_CONNECTIONS_PER_USER:
                logger.warning(
                    "Staff user %s exceeded max concurrent WebSocket limit (%d)",
                    user_id,
                    MAX_STAFF_CONNECTIONS_PER_USER,
                )
                await websocket.close(
                    code=CLOSE_POLICY_VIOLATION, reason="MAX_CONNECTIONS_EXCEEDED"
                )
                return False

            if not already_accepted:
                await websocket.accept()

            meta = ConnectionMeta(
                websocket=websocket,
                user_id=user_id,
                role=role,
            )
            self._connections[websocket] = meta
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(websocket)

            # Server-authoritative room subscription based strictly on role (docs/06 Section 16.2)
            assigned_rooms: set[str] = {f"user:{user_id}"}
            if role == UserRole.ADMIN.value:
                assigned_rooms.update(
                    {
                        "channel:admin",
                        "channel:kitchen",
                        "channel:waiters",
                        "channel:tables",
                        "channel:menu",
                    }
                )
            elif role == UserRole.WAITER.value:
                assigned_rooms.update({"channel:waiters", "channel:tables", "channel:menu"})
            elif role == UserRole.KITCHEN.value:
                assigned_rooms.update({"channel:kitchen", "channel:menu"})

            for room in assigned_rooms:
                self._add_to_room_locked(websocket, room)
                meta.rooms.add(room)

            logger.info(
                "Staff WebSocket connected (user_id=%s, role=%s, rooms=%s)",
                user_id,
                role,
                sorted(assigned_rooms),
            )
            return True

    async def connect_customer(
        self,
        websocket: WebSocket,
        *,
        customer_session_id: uuid.UUID,
        table_session_id: uuid.UUID,
        already_accepted: bool = False,
    ) -> bool:
        """Accept an authenticated customer WebSocket scoped to a single table session.

        ``already_accepted``: see :meth:`connect_staff`.

        Returns True if accepted, False if connection cap exceeded (docs/06 Section 16.3).
        """
        async with self._lock:
            # Enforce max 2 concurrent sockets per customer session
            existing = self._customer_connections.get(customer_session_id, set())
            if len(existing) >= MAX_CUSTOMER_CONNECTIONS_PER_SESSION:
                logger.warning(
                    "Customer session %s exceeded max concurrent WebSocket limit (%d)",
                    customer_session_id,
                    MAX_CUSTOMER_CONNECTIONS_PER_SESSION,
                )
                await websocket.close(
                    code=CLOSE_POLICY_VIOLATION, reason="MAX_CONNECTIONS_EXCEEDED"
                )
                return False

            if not already_accepted:
                await websocket.accept()

            # Customers are scoped strictly to their own table_session room — no cross-table leakage
            room = f"table_session:{table_session_id}"
            meta = ConnectionMeta(
                websocket=websocket,
                customer_session_id=customer_session_id,
                table_session_id=table_session_id,
                role="CUSTOMER",
                rooms={room},
            )
            self._connections[websocket] = meta
            if customer_session_id not in self._customer_connections:
                self._customer_connections[customer_session_id] = set()
            self._customer_connections[customer_session_id].add(websocket)
            self._add_to_room_locked(websocket, room)

            logger.info(
                "Customer WebSocket connected (customer_session_id=%s, table_session_id=%s)",
                customer_session_id,
                table_session_id,
            )
            return True

    def _add_to_room_locked(self, websocket: WebSocket, room: str) -> None:
        if room not in self._rooms:
            self._rooms[room] = set()
        self._rooms[room].add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        """Cleanly unregister a disconnected WebSocket from all internal indexes."""
        async with self._lock:
            meta = self._connections.pop(websocket, None)
            if not meta:
                return

            for room in meta.rooms:
                if room in self._rooms:
                    self._rooms[room].discard(websocket)
                    if not self._rooms[room]:
                        del self._rooms[room]

            if meta.user_id and meta.user_id in self._user_connections:
                self._user_connections[meta.user_id].discard(websocket)
                if not self._user_connections[meta.user_id]:
                    del self._user_connections[meta.user_id]

            if meta.customer_session_id and meta.customer_session_id in self._customer_connections:
                self._customer_connections[meta.customer_session_id].discard(websocket)
                if not self._customer_connections[meta.customer_session_id]:
                    del self._customer_connections[meta.customer_session_id]

            logger.info("WebSocket disconnected (user_id=%s, role=%s)", meta.user_id, meta.role)

    async def disconnect_user(
        self,
        user_id: uuid.UUID,
        close_code: int = CLOSE_ACCOUNT_DISABLED,
        reason: str = "SESSION_TERMINATED",
    ) -> None:
        """Force-disconnect all active WebSockets for a staff user.

        Invoked on logout, account deactivation, or token compromise.
        """
        async with self._lock:
            sockets = list(self._user_connections.get(user_id, set()))

        for ws in sockets:
            try:
                await ws.close(code=close_code, reason=reason)
            except Exception:
                pass
            await self.disconnect(ws)

    async def disconnect_customer_session(
        self,
        customer_session_id: uuid.UUID,
        close_code: int = CLOSE_SESSION_REVOKED,
        reason: str = "SESSION_CLOSED",
    ) -> None:
        """Force-disconnect all WebSockets for a customer session.

        Invoked on QR revocation, table session payment/close, or admin session unlock.
        """
        async with self._lock:
            sockets = list(self._customer_connections.get(customer_session_id, set()))

        for ws in sockets:
            try:
                await ws.close(code=close_code, reason=reason)
            except Exception:
                pass
            await self.disconnect(ws)

    async def disconnect_table_session(
        self,
        table_session_id: uuid.UUID,
        close_code: int = CLOSE_SESSION_REVOKED,
        reason: str = "TABLE_SESSION_CLOSED",
    ) -> None:
        """Force-disconnect all customer sockets bound to a specific table session room.

        Invoked on bill payment to atomically evict all customers from the closed session.
        """
        room = f"table_session:{table_session_id}"
        async with self._lock:
            sockets = list(self._rooms.get(room, set()))

        for ws in sockets:
            try:
                await ws.close(code=close_code, reason=reason)
            except Exception:
                pass
            await self.disconnect(ws)

    async def send_personal(self, websocket: WebSocket, message: dict[str, Any]) -> None:
        """Send a JSON message to a single specific connection.

        Injects a globally-unique ``event_id`` so the client can deduplicate
        reliably across reconnects (sequence numbers reset on each new socket,
        but event IDs are universally unique).
        """
        payload = {"event_id": uuid.uuid4().hex, **message}
        try:
            await websocket.send_json(payload)
        except Exception as exc:
            logger.warning("Failed to send personal WS message: %s", exc)
            await self.disconnect(websocket)

    async def broadcast_to_room(self, room: str, message: dict[str, Any]) -> None:
        """Broadcast a JSON message to all active sockets subscribed to a room.

        Injects:
        - ``event_id``: a globally-unique UUID hex string, stable per logical
          event across all recipients.  Clients MUST use this for deduplication
          because per-socket ``sequence`` counters reset on every reconnect,
          causing previously-seen sequence numbers to appear as duplicates of
          legitimate new events.
        - ``sequence``: per-socket monotonically-increasing counter (docs/08
          Section 3.2) for ordering and gap detection.  NOT suitable for
          cross-reconnect deduplication.

        Never raises; safely cleans up broken sockets without interrupting other
        deliveries.
        """
        # Generate one event_id shared across all recipients of this broadcast
        # so clients can correlate the same event if they receive it in multiple
        # rooms (e.g. admin is in channel:admin AND channel:kitchen).
        event_id = uuid.uuid4().hex

        async with self._lock:
            sockets = list(self._rooms.get(room, set()))

        async def _send_one(ws: WebSocket) -> None:
            meta = self._connections.get(ws)
            if meta:
                meta.sequence += 1
                payload = {"event_id": event_id, **message, "sequence": meta.sequence}
            else:
                payload = {"event_id": event_id, **message}
            try:
                await asyncio.wait_for(ws.send_json(payload), timeout=0.8)
            except Exception:
                await self.disconnect(ws)

        if sockets:
            await asyncio.gather(*[_send_one(ws) for ws in sockets], return_exceptions=True)


    def get_connection_meta(self, websocket: WebSocket) -> ConnectionMeta | None:
        """Return metadata for the given WebSocket if it is still registered."""
        return self._connections.get(websocket)


# Global singleton instance (in-memory modular monolith)
ws_manager = WebSocketManager()
