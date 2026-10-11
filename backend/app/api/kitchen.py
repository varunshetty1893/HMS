"""Kitchen operations and Display System (KDS) API routes.

Follows `docs/05-api-specification.md` (Section 10 & 15),
`docs/08-realtime-and-event-specification.md` (Section 24), and
`docs/13-final-implementation-blueprint.md` (Phase 7).

Security & RBAC:
All routes require Staff JWT with role IN ('KITCHEN', 'ADMIN').
Tickets delivered to kitchen strictly contain ZERO financial fields.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.exceptions import DomainValidationError, ResourceNotFoundError
from app.models.enums import UserRole
from app.models.identity import User
from app.models.menu import MenuItem
from app.models.restaurant import RestaurantSettings
from app.realtime.manager import ws_manager
from app.schemas.kitchen import (
    AcknowledgeModificationsRequest,
    KitchenAvailabilityToggleRequest,
    KitchenDashboardResponse,
    KitchenOrderTicket,
    OrderRejectRequest,
    OrderTransitionRequest,
)
from app.services.order_service import OrderService

router = APIRouter(prefix="/kitchen", tags=["Kitchen KDS Operations"])

KitchenOrAdminUser = Annotated[User, Depends(require_roles(UserRole.KITCHEN, UserRole.ADMIN))]


@router.get("/orders/active", response_model=KitchenDashboardResponse)
@router.get("/dashboard", response_model=KitchenDashboardResponse)
async def get_kitchen_active_queue(
    _staff: KitchenOrAdminUser,
    status: str | None = Query(
        default=None,
        description="Optional comma-separated status filter e.g. PLACED,ACCEPTED,PREPARING,READY",
    ),
    db: AsyncSession = Depends(get_db),
) -> KitchenDashboardResponse:
    """Retrieve active KDS queue ordered FIFO with zero financial fields."""
    status_filter = [s.strip().upper() for s in status.split(",")] if status else None
    return await OrderService.get_kitchen_active_orders(db, status_filter=status_filter)


@router.get("/orders/history", response_model=list[KitchenOrderTicket])
async def get_kitchen_order_history(
    _staff: KitchenOrAdminUser,
    status: str | None = Query(
        default=None,
        description="Comma-separated statuses e.g. READY,SERVED,COMPLETED,REJECTED",
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[KitchenOrderTicket]:
    """Retrieve past orders for kitchen history screen."""
    status_filter = [s.strip().upper() for s in status.split(",")] if status else None
    return await OrderService.get_kitchen_order_history(
        db, statuses=status_filter, page=page, page_size=page_size
    )


@router.get("/orders/{order_id}", response_model=KitchenOrderTicket)
async def get_kitchen_order_details(
    order_id: uuid.UUID,
    _staff: KitchenOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> KitchenOrderTicket:
    """Retrieve ticket details for a single order on the KDS."""
    return await OrderService.get_kitchen_order_by_id(db, order_id=order_id)


@router.post("/orders/{order_id}/accept", response_model=KitchenOrderTicket)
async def accept_kitchen_order(
    order_id: uuid.UUID,
    body: OrderTransitionRequest,
    staff: KitchenOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> KitchenOrderTicket:
    """Kitchen accepts a PLACED order (PLACED -> ACCEPTED)."""
    return await OrderService.accept_order(
        db,
        order_id=order_id,
        user_id=staff.id,
        expected_version=body.expected_version,
    )


@router.post("/orders/{order_id}/reject", response_model=KitchenOrderTicket)
async def reject_kitchen_order(
    order_id: uuid.UUID,
    body: OrderRejectRequest,
    staff: KitchenOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> KitchenOrderTicket:
    """Kitchen rejects a PLACED order (PLACED -> REJECTED). Mandatory plain reason required."""
    return await OrderService.reject_order(
        db,
        order_id=order_id,
        user_id=staff.id,
        expected_version=body.expected_version,
        rejection_reason=body.reason,
    )


@router.post("/orders/{order_id}/preparing", response_model=KitchenOrderTicket)
async def start_preparing_kitchen_order(
    order_id: uuid.UUID,
    body: OrderTransitionRequest,
    staff: KitchenOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> KitchenOrderTicket:
    """Kitchen starts preparation on an ACCEPTED order (ACCEPTED -> PREPARING)."""
    return await OrderService.start_preparing_order(
        db,
        order_id=order_id,
        user_id=staff.id,
        expected_version=body.expected_version,
    )


@router.post("/orders/{order_id}/ready", response_model=KitchenOrderTicket)
async def mark_kitchen_order_ready(
    order_id: uuid.UUID,
    body: OrderTransitionRequest,
    staff: KitchenOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> KitchenOrderTicket:
    """Kitchen marks order READY for pickup (PREPARING -> READY).
    Blocked if unacknowledged modifications exist. Emits order.ready (chimes Waiter).
    """
    return await OrderService.mark_order_ready(
        db,
        order_id=order_id,
        user_id=staff.id,
        expected_version=body.expected_version,
    )


@router.post("/orders/{order_id}/acknowledge-modifications", response_model=KitchenOrderTicket)
@router.post("/orders/{order_id}/acknowledge-modification", response_model=KitchenOrderTicket)
async def acknowledge_order_modifications(
    order_id: uuid.UUID,
    body: AcknowledgeModificationsRequest | None = None,
    staff: KitchenOrAdminUser = None,  # type: ignore[assignment]
    db: AsyncSession = Depends(get_db),
) -> KitchenOrderTicket:
    """Kitchen acknowledges diff alert on modified order, clearing unacknowledged flag."""
    mod_ids = body.modification_event_ids if body else None
    return await OrderService.acknowledge_order_modifications(
        db,
        order_id=order_id,
        user_id=staff.id,
        modification_event_ids=mod_ids,
    )


@router.patch("/menu/items/{item_id}/availability", status_code=status.HTTP_200_OK)
async def toggle_menu_item_availability_kitchen(
    item_id: uuid.UUID,
    body: KitchenAvailabilityToggleRequest,
    staff: KitchenOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> dict[str, bool]:
    """Toggle 86'd dish availability from the KDS screen (if permitted in restaurant_settings)."""
    settings = await db.scalar(select(RestaurantSettings))
    if staff.role != UserRole.ADMIN.value:
        if settings and not settings.kitchen_can_toggle_availability:
            raise DomainValidationError(
                "KITCHEN_TOGGLE_DISABLED",
                "Kitchen staff is not permitted to toggle item availability. Please ask an Admin.",
            )

    item = await db.scalar(select(MenuItem).where(MenuItem.id == item_id))
    if not item:
        raise ResourceNotFoundError("ITEM_NOT_FOUND", f"Menu item {item_id} not found.")

    item.is_available = body.is_available
    await db.commit()

    # Emit real-time notification
    try:
        await ws_manager.broadcast_to_room(
            "channel:menu",
            {
                "event": "menu.availability_changed",
                "item_id": str(item.id),
                "is_available": item.is_available,
            },
        )
    except Exception:
        pass

    return {"is_available": item.is_available}
