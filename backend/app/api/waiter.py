"""Waiter operations API routes.

Follows `docs/05-api-specification.md` (Section 9.4) and
`docs/13-final-implementation-blueprint.md`.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.rate_limit import extract_client_ip
from app.models.enums import UserRole
from app.models.identity import User
from app.schemas.billing import (
    BillGenerateRequest,
    BillResponse,
    TableBillResponse,
)
from app.schemas.menu import WaiterSearchResponse
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreateResponse,
    OrderItemAdjustmentRequest,
    OrderModifyRequest,
    OrderServeRequest,
    WaiterOrderCreate,
    WaiterOrderResponse,
    WaiterTableSessionDetail,
)
from app.schemas.table import TableResponse
from app.schemas.waiter_request import WaiterRequestResponse
from app.services import waiter_request_service as wr_svc
from app.services.billing_service import BillingService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.table_service import TableService

router = APIRouter(prefix="/waiter", tags=["Waiter Operations"])

WaiterOrAdminUser = Annotated[User, Depends(require_roles(UserRole.WAITER, UserRole.ADMIN))]


# ─────────────────────────────────────────────────────────────────────────────
# Tables & Floor Operations
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/tables", response_model=list[TableResponse])
async def get_waiter_tables(
    _staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> list[TableResponse]:
    """Retrieve active floor dining table grid with real-time derived occupancy."""
    return await TableService.get_floor_grid(db)


@router.get("/tables/by-number/{table_number}", response_model=TableResponse)
async def get_waiter_table_by_number(
    table_number: int,
    _staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> TableResponse:
    """Look up a table card by table number."""
    return await TableService.get_table_by_number(db, table_number)


@router.get("/tables/{table_id}/session", response_model=WaiterTableSessionDetail)
async def get_waiter_table_session(
    table_id: uuid.UUID,
    _staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> WaiterTableSessionDetail:
    """Retrieve detailed table session information for Waiter table detail sheet."""
    return await OrderService.get_table_session_details(db, table_id=table_id)


# ─────────────────────────────────────────────────────────────────────────────
# Menu Fast Search
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/menu/search", response_model=WaiterSearchResponse)
async def search_waiter_menu(
    _staff: WaiterOrAdminUser,
    q: str = Query(min_length=1, max_length=60, description="Short code or dish name"),
    category_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> WaiterSearchResponse:
    """Dual Short-Code (CB, CB-H) and Full-Name search for rapid table-side order entry."""
    results = await MenuService.search_waiter_menu(db, q, category_id=category_id)
    return WaiterSearchResponse(query=q, results=results)


@router.get("/menu/code-search", response_model=WaiterSearchResponse)
async def code_search_waiter_menu(
    _staff: WaiterOrAdminUser,
    code: str = Query(min_length=1, max_length=20, description="Short code e.g. CB, CB-H"),
    db: AsyncSession = Depends(get_db),
) -> WaiterSearchResponse:
    """Instant short-code lookup alias."""
    results = await MenuService.search_waiter_menu(db, code)
    return WaiterSearchResponse(query=code, results=results)


# ─────────────────────────────────────────────────────────────────────────────
# Order Placement & Management
# ─────────────────────────────────────────────────────────────────────────────


@router.post(
    "/orders",
    response_model=OrderCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a waiter manual order",
)
async def create_waiter_order(
    request: Request,
    payload: WaiterOrderCreate,
    staff: WaiterOrAdminUser,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=128,
        description="Client idempotency key. Replaying returns HTTP 200 + cached response.",
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Place a waiter manual table-side order.

    - If the table is AVAILABLE, opens a new TableSession and transitions table to OCCUPIED.
    - Server-authoritatively locks prices using menu price snapshots.
    - Enforces ₹5,000 table exposure cap under row lock.
    """
    client_ip = extract_client_ip(request)
    response, http_status = await OrderService.create_waiter_order(
        db,
        payload=payload,
        staff_user=staff,
        idempotency_key=idempotency_key,
        client_ip=client_ip,
    )
    return JSONResponse(
        content=response.model_dump(mode="json"),
        status_code=http_status,
    )


@router.get("/orders/active", response_model=list[WaiterOrderResponse])
async def get_waiter_active_orders(
    _staff: WaiterOrAdminUser,
    table_id: uuid.UUID | None = Query(default=None, description="Optional filter by table"),
    status: str | None = Query(default=None, description="Optional filter by status, e.g. READY"),
    db: AsyncSession = Depends(get_db),
) -> list[WaiterOrderResponse]:
    """Retrieve all active floor dining orders (PLACED, ACCEPTED, PREPARING, READY)."""
    return await OrderService.get_waiter_active_orders(db, table_id=table_id, status=status)


@router.get("/orders/{order_id}", response_model=WaiterOrderResponse)
async def get_waiter_order_details(
    order_id: uuid.UUID,
    _staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> WaiterOrderResponse:
    """Retrieve full details for an individual order."""
    return await OrderService.get_order_by_id(db, order_id=order_id)


@router.patch("/orders/{order_id}", response_model=WaiterOrderResponse)
@router.post("/orders/{order_id}/modify", response_model=WaiterOrderResponse)
async def modify_waiter_order(
    order_id: uuid.UUID,
    payload: OrderModifyRequest,
    staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> WaiterOrderResponse:
    """Modify an active order (pre- or post-acceptance).

    Pre-acceptance (PLACED): Updates lines and totals.
    Post-acceptance (ACCEPTED/PREPARING): Appends OrderModificationEvent, sets
    has_unacknowledged_mods=True, flags Kitchen KDS, and re-checks ₹5,000 table cap.
    While PREPARING, items can always be ADDED; reducing/removing needs `force=true`
    (kitchen is notified).
    """
    return await OrderService.modify_order(
        db,
        order_id=order_id,
        payload=payload,
        staff_user=staff,
    )


@router.post("/orders/{order_id}/items/{order_item_id}/adjust", response_model=WaiterOrderResponse)
async def adjust_waiter_order_item(
    order_id: uuid.UUID,
    order_item_id: uuid.UUID,
    payload: OrderItemAdjustmentRequest,
    staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> WaiterOrderResponse:
    """Adjust an order line's price, portion, extra pieces, or discount within waiter limits."""
    return await OrderService.adjust_order_item(
        db,
        order_id=order_id,
        order_item_id=order_item_id,
        payload=payload,
        staff_user=staff,
    )


@router.post("/orders/{order_id}/cancel", response_model=WaiterOrderResponse)
async def cancel_waiter_order(
    order_id: uuid.UUID,
    payload: OrderCancelRequest,
    staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> WaiterOrderResponse:
    """Cancel an active order with mandatory cancellation reason.

    PLACED/ACCEPTED: normal cancel. PREPARING/READY: send `force=true` (FORCE cancel) -
    the kitchen gets a STOP_COOKING / DISCARD alert. Deducts amount from table session
    exposure. If sole active order in session, resets table to AVAILABLE.
    """
    return await OrderService.cancel_order(
        db,
        order_id=order_id,
        payload=payload,
        staff_user=staff,
    )


@router.post("/orders/{order_id}/served", response_model=WaiterOrderResponse)
@router.post("/orders/{order_id}/serve", response_model=WaiterOrderResponse)
async def mark_waiter_order_served(
    order_id: uuid.UUID,
    payload: OrderServeRequest,
    staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> WaiterOrderResponse:
    """Waiter marks a READY order as SERVED to the table (READY -> SERVED)."""
    return await OrderService.mark_order_served(
        db,
        order_id=order_id,
        user_id=staff.id,
        expected_version=payload.expected_version,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Table Billing Operations
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/tables/{table_number}/bill",
    response_model=TableBillResponse,
    summary="Retrieve table bill preview or issued bill by table number",
)
async def get_waiter_table_bill_by_number(
    table_number: int,
    _staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> TableBillResponse:
    """Retrieve bill preview or issued bill for active dining session by table number."""
    return await BillingService.get_table_bill(db, table_number=table_number)


@router.get(
    "/tables/{table_id}/bill-by-id",
    response_model=TableBillResponse,
    summary="Retrieve table bill preview or issued bill by table UUID",
)
async def get_waiter_table_bill_by_id(
    table_id: uuid.UUID,
    _staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> TableBillResponse:
    """Retrieve bill preview or issued bill for active dining session by table ID."""
    return await BillingService.get_table_bill(db, table_id=table_id)


@router.post(
    "/tables/{table_id}/bills",
    response_model=BillResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate bill for table UUID",
)
async def generate_waiter_table_bill(
    request: Request,
    table_id: uuid.UUID,
    payload: BillGenerateRequest,
    staff: WaiterOrAdminUser,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=128,
    ),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """Convenience alias: generate bill for specified table ID."""
    client_ip = extract_client_ip(request)
    payload.table_id = table_id
    response_dto, http_status = await BillingService.generate_bill(
        db,
        payload=payload,
        staff_user=staff,
        idempotency_key=idempotency_key,
        client_ip=client_ip,
    )
    return JSONResponse(
        content=response_dto.model_dump(mode="json"),
        status_code=http_status,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Call-Waiter Requests
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/waiter-requests",
    response_model=list[WaiterRequestResponse],
    summary="List all pending call-waiter requests",
)
async def list_waiter_requests(
    _staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> list[WaiterRequestResponse]:
    """Retrieve all PENDING call-waiter requests, oldest-first."""
    return await wr_svc.list_pending_requests(db)


@router.post(
    "/waiter-requests/{request_id}/claim",
    response_model=WaiterRequestResponse,
    summary="Atomically claim a pending call-waiter request",
)
async def claim_waiter_request(
    request_id: uuid.UUID,
    staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> WaiterRequestResponse:
    """Atomically claim a PENDING request.

    Concurrent claims result in exactly one winner (409 for the rest).
    Uses SELECT FOR UPDATE NOWAIT to ensure atomicity without long lock waits.
    """
    return await wr_svc.claim_request(db, request_id=request_id, staff_user=staff)


@router.post(
    "/waiter-requests/{request_id}/complete",
    response_model=WaiterRequestResponse,
    summary="Mark a claimed waiter request as completed",
)
async def complete_waiter_request(
    request_id: uuid.UUID,
    staff: WaiterOrAdminUser,
    db: AsyncSession = Depends(get_db),
) -> WaiterRequestResponse:
    """Mark a CLAIMED (or PENDING) request as COMPLETED.

    Broadcasts `waiter.request.completed` to the customer's table session room.
    """
    return await wr_svc.complete_request(db, request_id=request_id, staff_user=staff)
