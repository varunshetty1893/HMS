"""Customer Web menu catalog and order API routes.

Follows `docs/05-api-specification.md` (Sections 6 & 7) and
`docs/13-final-implementation-blueprint.md` (Phase 6).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_customer_session
from app.core.rate_limit import rate_limit_by_ip
from app.models.qr_sessions import CustomerSession, TableSession
from app.models.restaurant import RestaurantTable
from app.schemas.menu import (
    CustomerCategorySummary,
    CustomerMenuItem,
    CustomerMenuResponse,
)
from app.schemas.order import (
    OrderCreate,
    OrderCreateResponse,
    OrderResponse,
)
from app.schemas.qr import CustomerSessionResponse
from app.services.menu_service import MenuService
from app.services.order_service import OrderService, _build_order_response

router = APIRouter(prefix="/customer", tags=["Customer Operations"])


@router.get("/session", response_model=CustomerSessionResponse)
async def get_customer_session(
    session: CustomerSession = Depends(get_current_customer_session),
    db: AsyncSession = Depends(get_db),
) -> CustomerSessionResponse:
    """Inspect current customer session, bound table number, and active dining state."""
    # Ensure table info is loaded
    table = session.table
    if not table:
        table_stmt = select(RestaurantTable).where(RestaurantTable.id == session.table_id)
        table = (await db.execute(table_stmt)).scalar_one()

    # Derive table status
    active_session = (
        await db.execute(
            select(TableSession.id).where(
                TableSession.table_id == session.table_id,
                TableSession.status == "ACTIVE",
            )
        )
    ).scalar_one_or_none()
    table_status = "OCCUPIED" if active_session else "AVAILABLE"

    return CustomerSessionResponse(
        session_id=session.id,
        table_id=session.table_id,
        table_number=table.table_number,
        table_display_name=table.display_name,
        table_status=table_status,
        status=session.status,
        expires_at=session.expires_at,
    )


@router.get("/menu", response_model=CustomerMenuResponse)
async def get_customer_menu(
    category_id: uuid.UUID | None = Query(default=None),
    dietary_type: str | None = Query(default=None),
    available_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
) -> CustomerMenuResponse:
    """Retrieve full active menu grouped by category with live prices and availability."""
    return await MenuService.get_customer_menu(
        db,
        category_id=category_id,
        dietary_type=dietary_type,
        available_only=available_only,
    )


@router.get("/menu/categories", response_model=list[CustomerCategorySummary])
async def get_customer_categories(
    db: AsyncSession = Depends(get_db),
) -> list[CustomerCategorySummary]:
    """Retrieve active category navigation tabs with item counts."""
    return await MenuService.get_customer_categories(db)


@router.get("/menu/items/{item_id}", response_model=CustomerMenuItem)
async def get_customer_item_details(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CustomerMenuItem:
    """Retrieve single dish details and variants for portion selection dialog."""
    return await MenuService.get_customer_item(db, item_id)


@router.get("/menu/search", response_model=list[CustomerMenuItem])
async def search_customer_menu(
    q: str = Query(min_length=1, max_length=60),
    dietary_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[CustomerMenuItem]:
    """Search active menu items by dish name or short code."""
    return await MenuService.search_customer_menu(db, q, dietary_type=dietary_type)


# ─────────────────────────────────────────────────────────────────────────────
# Order placement (Phase 6)
# Rate limits: 3 orders / 5 min per IP + 10 orders / session (enforced in service)
# ─────────────────────────────────────────────────────────────────────────────

_ORDER_RATE_LIMIT = rate_limit_by_ip(max_requests=3, window_seconds=300)


@router.post(
    "/orders",
    response_model=OrderCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Place a new order",
)
async def place_order(
    request: Request,
    payload: OrderCreate,
    idempotency_key: str | None = Header(
        default=None,
        alias="Idempotency-Key",
        max_length=128,
        description="Client-generated idempotency key (RFC draft). Re-using the same key "
        "with the same payload returns the cached response (HTTP 200 + is_replay=true).",
    ),
    session: CustomerSession = Depends(get_current_customer_session),
    db: AsyncSession = Depends(get_db),
    _rate: None = Depends(_ORDER_RATE_LIMIT),
) -> JSONResponse:
    """Place a customer QR order.

    - Creates a `TableSession` atomically on the first order (table goes `AVAILABLE → OCCUPIED`).
    - Enforces the ₹5,000.00 unpaid table cap using `SELECT … FOR UPDATE`.
    - Prices are always resolved server-side; client-supplied prices are ignored.
    - Returns HTTP 201 on success or HTTP 200 if `Idempotency-Key` matches a previous request.
    """
    client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or (
        request.client.host if request.client else None
    )
    response, http_status = await OrderService.create_order(
        db,
        payload=payload,
        customer_session=session,
        idempotency_key=idempotency_key,
        client_ip=client_ip,
    )
    return JSONResponse(
        content=response.model_dump(mode="json"),
        status_code=http_status,
    )


@router.get(
    "/orders",
    response_model=list[OrderResponse],
    summary="List orders for current session",
)
async def list_orders(
    session: CustomerSession = Depends(get_current_customer_session),
    db: AsyncSession = Depends(get_db),
) -> list[OrderResponse]:
    """Return all orders placed by the current customer session, newest first."""
    orders = await OrderService.list_customer_orders(db, customer_session=session)
    return [_build_order_response(o) for o in orders]
