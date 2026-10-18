"""Notification recovery endpoints for reconnecting devices.

Follows `docs/04-database-design.md` (Table 17) and `docs/05-api-specification.md`.

GET  /api/v1/notifications/unread   -- pull missed notifications after reconnect
POST /api/v1/notifications/ack      -- mark notifications as delivered/read

Role-based access:
- Staff (waiter, kitchen, admin) authenticate with JWT.
- Customer sessions use X-Customer-Session-Token header.
- Kitchen channel rows never contain billing data.
- Customer channel is scoped to the caller's table_session_id.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles, get_current_customer_session
from app.models.enums import NotificationChannel, UserRole
from app.models.identity import User
from app.models.qr_sessions import CustomerSession
from app.schemas.notifications import (
    NotificationAckRequest,
    NotificationAckResponse,
    NotificationItem,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notification Recovery"])

StaffUser = Annotated[User, Depends(require_roles(UserRole.WAITER, UserRole.ADMIN, UserRole.KITCHEN))]
AdminOrWaiter = Annotated[User, Depends(require_roles(UserRole.WAITER, UserRole.ADMIN))]


# ---------------------------------------------------------------------------
# Staff recovery (kitchen, waiters, admin)
# ---------------------------------------------------------------------------

@router.get("/unread", response_model=list[NotificationItem], summary="Fetch unread notifications (staff)")
async def get_unread_staff(
    staff: StaffUser,
    db: AsyncSession = Depends(get_db),
    channel: str = Query(description="Channel to fetch: KITCHEN_ALL, WAITERS_ALL, ADMIN_ALL"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[NotificationItem]:
    """Return unacknowledged notifications for a staff channel (called on reconnect)."""
    # Enforce role-channel binding
    allowed: dict[str, list[str]] = {
        UserRole.KITCHEN.value: [NotificationChannel.KITCHEN_ALL.value],
        UserRole.WAITER.value: [NotificationChannel.WAITERS_ALL.value, NotificationChannel.ADMIN_ALL.value],
        UserRole.ADMIN.value: [NotificationChannel.KITCHEN_ALL.value, NotificationChannel.WAITERS_ALL.value, NotificationChannel.ADMIN_ALL.value],
    }
    if channel not in allowed.get(staff.role, []):
        return []

    rows = await NotificationService.get_unacknowledged(db, channel=channel, limit=limit)
    return [NotificationItem.from_orm(r) for r in rows]


@router.post("/ack", response_model=NotificationAckResponse, summary="Acknowledge notifications (staff)")
async def ack_notifications_staff(
    payload: NotificationAckRequest,
    staff: AdminOrWaiter,
    db: AsyncSession = Depends(get_db),
) -> NotificationAckResponse:
    """Mark a batch of notifications as acknowledged."""
    count = await NotificationService.acknowledge(
        db,
        notification_ids=payload.notification_ids,
        acknowledged_by_user_id=staff.id,
    )
    await db.commit()
    return NotificationAckResponse(acknowledged=count)


# ---------------------------------------------------------------------------
# Customer recovery (table_session scoped)
# ---------------------------------------------------------------------------

@router.get("/customer/unread", response_model=list[NotificationItem], summary="Fetch unread notifications (customer)")
async def get_unread_customer(
    session: CustomerSession = Depends(get_current_customer_session),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=100),
) -> list[NotificationItem]:
    """Return unacknowledged notifications for this customer's table session."""
    rows = await NotificationService.get_unacknowledged(
        db,
        channel=NotificationChannel.TABLE_SESSION.value,
        table_session_id=session.table_session_id,
        limit=limit,
    )
    return [NotificationItem.from_orm(r) for r in rows]
