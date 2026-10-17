"""WaiterRequest service — business logic for the Call-Waiter feature.

Key design invariants:
- A customer can only create a request for their own ACTIVE table session.
- At most one PENDING or CLAIMED request per table_session_id (DB partial unique index).
- Claim is atomic via SELECT FOR UPDATE NOWAIT; only one waiter wins concurrent races.
- All state transitions broadcast to the relevant WebSocket rooms.
- No simulation: every notification is server-confirmed before informing the customer.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.time_utils import utc_now
from app.models.enums import (
    CustomerSessionStatus,
    TableSessionStatus,
    WaiterRequestStatus,
)
from app.models.identity import User
from app.models.qr_sessions import CustomerSession, TableSession
from app.models.restaurant import RestaurantTable
from app.models.waiter_requests import WaiterRequest
from app.realtime.manager import ws_manager
from app.schemas.waiter_request import WaiterRequestCreate, WaiterRequestResponse

logger = get_logger(__name__)

_REQUEST_TTL_MINUTES = 15


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _to_response(req: WaiterRequest) -> WaiterRequestResponse:
    return WaiterRequestResponse(
        id=req.id,
        customer_session_id=req.customer_session_id,
        table_session_id=req.table_session_id,
        table_id=req.table_id,
        reason=req.reason,
        notes=req.notes,
        status=req.status,
        claimed_by_user_id=req.claimed_by_user_id,
        claimed_at=req.claimed_at,
        completed_at=req.completed_at,
        completed_by_user_id=req.completed_by_user_id,
        cancelled_at=req.cancelled_at,
        expires_at=req.expires_at,
        created_at=req.created_at,
    )


async def _get_table_info(db: AsyncSession, table_id: uuid.UUID) -> tuple[int | None, str | None]:
    """Fetch table_number and display_name for WS broadcast metadata."""
    row = await db.execute(
        select(RestaurantTable.table_number, RestaurantTable.display_name).where(
            RestaurantTable.id == table_id
        )
    )
    r = row.first()
    if r:
        return r.table_number, r.display_name
    return None, None


async def _broadcast_event(
    req: WaiterRequest,
    event: str,
    table_number: int | None,
    table_display_name: str | None,
) -> None:
    payload = {
        "event": event,
        "request_id": str(req.id),
        "table_session_id": str(req.table_session_id),
        "table_id": str(req.table_id),
        "table_number": table_number,
        "table_display_name": table_display_name,
        "reason": req.reason,
        "notes": req.notes,
        "status": req.status,
        "claimed_by_user_id": str(req.claimed_by_user_id) if req.claimed_by_user_id else None,
        "claimed_at": req.claimed_at.isoformat() if req.claimed_at else None,
        "completed_at": req.completed_at.isoformat() if req.completed_at else None,
        "created_at": req.created_at.isoformat(),
    }
    # Notify all waiters
    await ws_manager.broadcast_to_room("channel:waiters", payload)
    # Notify the customer's own table session room
    await ws_manager.broadcast_to_room(f"table_session:{req.table_session_id}", payload)


# ─────────────────────────────────────────────────────────────────────────────
# Customer-facing operations
# ─────────────────────────────────────────────────────────────────────────────


async def create_waiter_request(
    db: AsyncSession,
    *,
    payload: WaiterRequestCreate,
    customer_session: CustomerSession,
) -> WaiterRequestResponse:
    """Create a new call-waiter request for the customer's active table session.

    Raises 409 if a PENDING or CLAIMED request already exists for this session.
    Raises 400 if the customer has no active table session yet (no first order placed).
    """
    # Must have an active customer session
    if customer_session.status != CustomerSessionStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {"code": "SESSION_INVALID", "message": "Customer session is not active."}
            },
        )

    # Ensure active table session is linked; if the customer has not ordered yet,
    # auto-create/link the active TableSession for this table so staff is immediately alerted.
    table_session = None
    if customer_session.table_session_id:
        table_session = await db.get(TableSession, customer_session.table_session_id)
        if not table_session or table_session.status != TableSessionStatus.ACTIVE.value:
            table_session = None

    if not table_session:
        from app.services.order_service import OrderService

        table_session, _ = await OrderService._get_or_create_table_session(
            db,
            table_id=customer_session.table_id,
            customer_session=customer_session,
        )
        customer_session.table_session_id = table_session.id
        await db.flush()

    # Detect existing open request (DB unique index would also catch this, but give a cleaner 409)
    existing = await db.execute(
        select(WaiterRequest).where(
            WaiterRequest.table_session_id == customer_session.table_session_id,
            WaiterRequest.status.in_(
                [WaiterRequestStatus.PENDING.value, WaiterRequestStatus.CLAIMED.value]
            ),
        )
    )
    existing_req = existing.scalar_one_or_none()
    if existing_req:
        # Return the existing request (idempotent for the customer)
        return _to_response(existing_req)

    now = utc_now()
    req = WaiterRequest(
        customer_session_id=customer_session.id,
        table_session_id=customer_session.table_session_id,
        table_id=customer_session.table_id,
        reason=payload.reason,
        notes=payload.notes,
        status=WaiterRequestStatus.PENDING.value,
        expires_at=now + timedelta(minutes=_REQUEST_TTL_MINUTES),
        created_at=now,
    )
    db.add(req)

    try:
        await db.commit()
        await db.refresh(req)
    except Exception:
        await db.rollback()
        # Another concurrent insert won the race; return existing
        existing2 = await db.execute(
            select(WaiterRequest).where(
                WaiterRequest.table_session_id == customer_session.table_session_id,
                WaiterRequest.status.in_(
                    [WaiterRequestStatus.PENDING.value, WaiterRequestStatus.CLAIMED.value]
                ),
            )
        )
        ex2 = existing2.scalar_one_or_none()
        if ex2:
            return _to_response(ex2)
        raise

    table_number, table_display_name = await _get_table_info(db, req.table_id)
    await _broadcast_event(req, "waiter.request.created", table_number, table_display_name)
    logger.info("WaiterRequest created id=%s table_session=%s", req.id, req.table_session_id)
    return _to_response(req)


async def get_active_customer_request(
    db: AsyncSession,
    *,
    customer_session: CustomerSession,
) -> WaiterRequestResponse | None:
    """Return the current PENDING or CLAIMED request for this customer session, if any."""
    if not customer_session.table_session_id:
        return None
    result = await db.execute(
        select(WaiterRequest).where(
            WaiterRequest.table_session_id == customer_session.table_session_id,
            WaiterRequest.status.in_(
                [WaiterRequestStatus.PENDING.value, WaiterRequestStatus.CLAIMED.value]
            ),
        )
    )
    req = result.scalar_one_or_none()
    return _to_response(req) if req else None


async def cancel_customer_request(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    customer_session: CustomerSession,
) -> WaiterRequestResponse:
    """Allow a customer to cancel their own PENDING request."""
    req = await db.get(WaiterRequest, request_id)
    if not req or req.customer_session_id != customer_session.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Waiter request not found."}},
        )
    if req.status != WaiterRequestStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "CANNOT_CANCEL",
                    "message": f"Request is already {req.status} and cannot be cancelled.",
                }
            },
        )
    now = utc_now()
    req.status = WaiterRequestStatus.CANCELLED.value
    req.cancelled_at = now
    await db.commit()
    await db.refresh(req)

    table_number, table_display_name = await _get_table_info(db, req.table_id)
    await _broadcast_event(req, "waiter.request.cancelled", table_number, table_display_name)
    return _to_response(req)


# ─────────────────────────────────────────────────────────────────────────────
# Waiter-facing operations
# ─────────────────────────────────────────────────────────────────────────────


async def list_pending_requests(db: AsyncSession) -> list[WaiterRequestResponse]:
    """Return all PENDING waiter requests, oldest first."""
    result = await db.execute(
        select(WaiterRequest)
        .where(WaiterRequest.status == WaiterRequestStatus.PENDING.value)
        .order_by(WaiterRequest.created_at)
    )
    return [_to_response(r) for r in result.scalars().all()]


async def claim_request(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    staff_user: User,
) -> WaiterRequestResponse:
    """Atomically claim a PENDING request.

    Uses SELECT FOR UPDATE NOWAIT to guarantee that exactly one waiter wins if
    multiple waiters try to claim simultaneously. The loser gets 409 CONFLICT.
    """

    # Lock the row
    result = await db.execute(
        select(WaiterRequest).where(WaiterRequest.id == request_id).with_for_update(nowait=True)
    )
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Waiter request not found."}},
        )
    if req.status == WaiterRequestStatus.CLAIMED.value:
        if req.claimed_by_user_id == staff_user.id:
            # Already claimed by the same waiter — idempotent
            return _to_response(req)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "ALREADY_CLAIMED",
                    "message": "This request was already claimed by another waiter.",
                }
            },
        )
    if req.status != WaiterRequestStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {"code": "CANNOT_CLAIM", "message": f"Request status is {req.status}."}
            },
        )

    now = utc_now()
    req.status = WaiterRequestStatus.CLAIMED.value
    req.claimed_by_user_id = staff_user.id
    req.claimed_at = now
    await db.commit()
    await db.refresh(req)

    table_number, table_display_name = await _get_table_info(db, req.table_id)
    await _broadcast_event(req, "waiter.request.claimed", table_number, table_display_name)
    logger.info("WaiterRequest claimed id=%s by user=%s", req.id, staff_user.id)
    return _to_response(req)


async def complete_request(
    db: AsyncSession,
    *,
    request_id: uuid.UUID,
    staff_user: User,
) -> WaiterRequestResponse:
    """Mark a CLAIMED request as COMPLETED."""
    req = await db.get(WaiterRequest, request_id)
    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Waiter request not found."}},
        )
    if req.status not in (WaiterRequestStatus.CLAIMED.value, WaiterRequestStatus.PENDING.value):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {"code": "CANNOT_COMPLETE", "message": f"Request status is {req.status}."}
            },
        )

    now = utc_now()
    req.status = WaiterRequestStatus.COMPLETED.value
    req.completed_at = now
    req.completed_by_user_id = staff_user.id
    await db.commit()
    await db.refresh(req)

    table_number, table_display_name = await _get_table_info(db, req.table_id)
    await _broadcast_event(req, "waiter.request.completed", table_number, table_display_name)
    return _to_response(req)
