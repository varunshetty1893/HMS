"""Notification persistence service for durable event delivery.

Follows `docs/04-database-design.md` (Table 17 `notifications`).

Design
------
Every important operational event is persisted to `notifications` before/alongside
the WebSocket broadcast.  A broadcast is best-effort; the DB row is durable.

On reconnect, clients call `GET /api/v1/notifications/unread?channel=<CHANNEL>`
to recover events they missed while disconnected, then acknowledge receipt via
`POST /api/v1/notifications/ack` (batch).

Rows expire after `expires_hours` (default 4 h) so the table stays small.

Role-based safety
-----------------
- Kitchen channel rows never contain billing fields (grand_total, bill_id, etc.).
- Customer rows are scoped to `table_session_id`; a customer cannot fetch
  another session's notifications.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time_utils import utc_now
from app.models.enums import NotificationChannel, NotificationSeverity
from app.models.operations import Notification

# ---------------------------------------------------------------------------
# Channel routing helpers
# ---------------------------------------------------------------------------

# Map WebSocket room strings -> NotificationChannel enum values
_CHANNEL_MAP: dict[str, str] = {
    "channel:kitchen": NotificationChannel.KITCHEN_ALL.value,
    "channel:waiters": NotificationChannel.WAITERS_ALL.value,
    "channel:admin": NotificationChannel.ADMIN_ALL.value,
    "channel:tables": NotificationChannel.TABLE_SESSION.value,
}

# Events worth persisting (skip heartbeats and non-actionable metadata)
_PERSIST_EVENT_TYPES: frozenset[str] = frozenset({
    "ORDER_CREATED",
    "ORDER_ACCEPTED",
    "ORDER_PREPARING",
    "ORDER_READY",
    "ORDER_SERVED",
    "ORDER_COMPLETED",
    "ORDER_CANCELLED",
    "ORDER_REJECTED",
    "ORDER_MODIFIED",
    "WAITER_REQUEST",
    "TABLE_SESSION_OPENED",
    "TABLE_SESSION_CLOSED",
    "TABLE_STATUS_CHANGED",
})

# Fields forbidden in kitchen-channel notifications (billing privacy)
_BILLING_FIELDS: frozenset[str] = frozenset({
    "grand_total", "cgst_amount", "sgst_amount",
    "discount_amount", "payment_method", "bill_id",
})


def _strip_billing(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of payload without billing-sensitive fields."""
    return {k: v for k, v in payload.items() if k not in _BILLING_FIELDS}


class NotificationService:
    """Persist operational alerts to the `notifications` table."""

    @classmethod
    async def persist_broadcast(
        cls,
        db: AsyncSession,
        *,
        room: str,
        message: dict[str, Any],
        expires_hours: int = 4,
        table_id: uuid.UUID | None = None,
        table_session_id: uuid.UUID | None = None,
        order_id: uuid.UUID | None = None,
    ) -> Notification | None:
        """Persist a broadcast to `notifications` if its event_type is worth keeping.

        Returns the new row or `None` when the event is not in the whitelist.
        Does NOT commit -- participates in the caller's transaction.
        """
        event_type: str = message.get("event_type", "")
        if event_type not in _PERSIST_EVENT_TYPES:
            return None

        if room.startswith("table_session:"):
            channel_str = NotificationChannel.TABLE_SESSION.value
            # Extract table_session_id from room name if not supplied explicitly
            if not table_session_id:
                try:
                    table_session_id = uuid.UUID(room.split(":", 1)[1])
                except ValueError:
                    pass
        else:
            channel_str = _CHANNEL_MAP.get(room)
            if not channel_str:
                return None  # Unknown room -- skip

        payload = message.copy()
        if channel_str == NotificationChannel.KITCHEN_ALL.value:
            payload = _strip_billing(payload)

        severity = str(message.get("severity", NotificationSeverity.INFO.value))
        if severity not in {s.value for s in NotificationSeverity}:
            severity = NotificationSeverity.INFO.value

        row = Notification(
            event_type=event_type[:40],
            target_channel=channel_str,
            severity=severity,
            title=str(message.get("title", event_type))[:150],
            message=str(message.get("message", ""))[:500],
            payload_json=payload,
            requires_acknowledgment=True,
            is_acknowledged=False,
            table_id=table_id,
            table_session_id=table_session_id,
            order_id=order_id,
            expires_at=utc_now() + timedelta(hours=expires_hours),
        )
        db.add(row)
        await db.flush()
        return row

    @classmethod
    async def get_unacknowledged(
        cls,
        db: AsyncSession,
        *,
        channel: str,
        table_session_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[Notification]:
        """Return unacknowledged, non-expired rows for a channel (newest first).

        For TABLE_SESSION channel, `table_session_id` is required; requests without
        it return an empty list (prevents cross-session data leakage).
        """
        now = utc_now()
        stmt = (
            select(Notification)
            .where(
                Notification.target_channel == channel,
                Notification.is_acknowledged == False,  # noqa: E712
                Notification.expires_at > now,
            )
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        if channel == NotificationChannel.TABLE_SESSION.value:
            if not table_session_id:
                return []
            stmt = stmt.where(Notification.table_session_id == table_session_id)

        return list((await db.execute(stmt)).scalars().all())

    @classmethod
    async def acknowledge(
        cls,
        db: AsyncSession,
        *,
        notification_ids: list[uuid.UUID],
        acknowledged_by_user_id: uuid.UUID | None = None,
    ) -> int:
        """Mark notifications as acknowledged.  Returns count of rows updated."""
        if not notification_ids:
            return 0
        result = await db.execute(
            update(Notification)
            .where(Notification.id.in_(notification_ids))
            .values(
                is_acknowledged=True,
                acknowledged_at=utc_now(),
                acknowledged_by_user_id=acknowledged_by_user_id,
            )
        )
        return result.rowcount
