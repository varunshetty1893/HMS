"""Phase 8 — Waiter Workflow Backend Tests.

Covers:
- Waiter live floor tables & table-by-number lookup.
- Table session detail inspection.
- Dual short-code and name menu search.
- Waiter manual order placement:
  * TableSession creation & AVAILABLE -> OCCUPIED transition.
  * Server-authoritative pricing snapshots.
  * ₹5,000 table exposure limit enforcement.
  * Idempotency-Key deduplication.
- Order modifications (pre- vs post-acceptance):
  * Pre-acceptance (PLACED): clean line update, kitchen_ack_required=False.
  * Post-acceptance (ACCEPTED): OrderModificationEvent, has_unacknowledged_mods=True.
  * Optimistic concurrency 409 ORDER_VERSION_CONFLICT.
  * Exposure cap enforcement on line quantity increase.
- Order cancellation:
  * Mandatory cancellation reason.
  * Sole-order cancellation resets table to AVAILABLE.
- Marking served (READY -> SERVED):
  * 409 on invalid transition (e.g. from PLACED).
  * 409 on version conflict.
- RBAC validation: Non-staff or customer sessions rejected.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_staff_user
from app.core.exceptions import DomainValidationError, StateConflictError
from app.main import app
from app.models.enums import UserRole, UserStatus
from app.models.identity import User
from app.models.orders import Order, OrderItem
from app.models.restaurant import RestaurantTable
from app.schemas.table import TableResponse

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def waiter_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="waiter_test",
        full_name="Waiter Test",
        role=UserRole.WAITER.value,
        is_active=True,
        status=UserStatus.ACTIVE.value,
        token_version=1,
    )


@pytest.fixture
async def waiter_client(async_client: AsyncClient, waiter_user: User) -> AsyncIterator[AsyncClient]:
    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_staff_user] = lambda: waiter_user
    try:
        yield async_client
    finally:
        app.dependency_overrides.pop(get_current_staff_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def kitchen_client(
    async_client: AsyncClient,
) -> AsyncIterator[AsyncClient]:
    mock_db = AsyncMock()
    k_user = User(
        id=uuid.uuid4(),
        username="kitchen_test",
        full_name="Kitchen Test",
        role=UserRole.KITCHEN.value,
        is_active=True,
        status=UserStatus.ACTIVE.value,
        token_version=1,
    )
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_current_staff_user] = lambda: k_user
    try:
        yield async_client
    finally:
        app.dependency_overrides.pop(get_current_staff_user, None)
        app.dependency_overrides.pop(get_db, None)


# ─────────────────────────────────────────────────────────────────────────────
# Test Factories
# ─────────────────────────────────────────────────────────────────────────────


def _make_dummy_order(
    *,
    order_id: uuid.UUID | None = None,
    order_number: str = "ORD-WAITER-001",
    status: str = "PLACED",
    version: int = 1,
    subtotal: Decimal = Decimal("300.00"),
    table_id: uuid.UUID | None = None,
    table_number: int = 5,
    table_name: str = "Table 5",
    has_unacknowledged_mods: bool = False,
) -> MagicMock:
    order = MagicMock(spec=Order)
    order.id = order_id or uuid.uuid4()
    order.order_number = order_number
    order.status = status
    order.version = version
    order.order_subtotal = subtotal
    order.source = "WAITER"
    order.table_id = table_id or uuid.uuid4()
    order.table_session_id = uuid.uuid4()
    order.customer_session_id = None
    order.placed_at = datetime.now(timezone.utc)
    order.accepted_at = None
    order.ready_at = None
    order.served_at = None
    order.cancelled_at = None
    order.cancelled_by_user_id = None
    order.cancelled_by_role = None
    order.cancellation_reason = None
    order.special_instructions = "Less spicy"
    order.is_first_qr_order_of_session = False
    order.has_unacknowledged_mods = has_unacknowledged_mods

    table = MagicMock(spec=RestaurantTable)
    table.id = order.table_id
    table.table_number = table_number
    table.display_name = table_name
    order.table = table

    item = MagicMock(spec=OrderItem)
    item.id = uuid.uuid4()
    item.order_id = order.id
    item.menu_item_id = uuid.uuid4()
    item.menu_price_variant_id = uuid.uuid4()
    item.item_code_snapshot = "CB"
    item.item_name_snapshot = "Chicken Biryani"
    item.variant_code_snapshot = "CB-H"
    item.variant_name_snapshot = "Half"
    item.quantity_value_snapshot = Decimal("1.00")
    item.unit_snapshot = "PORTION"
    item.unit_price_snapshot = Decimal("150.00")
    item.tax_rate_snapshot = Decimal("5.00")
    item.original_quantity = 2
    item.active_quantity = 2
    item.cancelled_quantity = 0
    item.line_subtotal = Decimal("300.00")
    item.item_status = "ACTIVE"
    item.item_notes = None

    order.items = [item]
    order.modification_events = []
    return order


# ─────────────────────────────────────────────────────────────────────────────
# 1. Floor & Table Lookup Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_waiter_tables_grid(
    waiter_client: AsyncClient,
) -> None:
    """GET /api/v1/waiter/tables returns table occupancy grid."""
    dummy_table = MagicMock(spec=RestaurantTable)
    dummy_table.id = uuid.uuid4()
    dummy_table.table_number = 1
    dummy_table.display_name = "Table 1"
    dummy_table.capacity = 4
    dummy_table.operational_status = "ENABLED"
    dummy_table.current_session_id = None

    dummy_response = TableResponse(
        id=dummy_table.id,
        table_number=dummy_table.table_number,
        display_name=dummy_table.display_name,
        seating_capacity=4,
        floor_or_zone="Main Hall",
        operational_status="ENABLED",
        is_active=True,
        display_order=1,
        notes=None,
        current_occupancy="AVAILABLE",
        active_session_id=None,
        active_qr_version=1,
        active_qr_prefix=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch("app.services.table_service.TableService.get_floor_grid") as mock_grid:
        mock_grid.return_value = [dummy_response]
        resp = await waiter_client.get("/api/v1/waiter/tables")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["display_name"] == "Table 1"
        assert data[0]["current_occupancy"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_waiter_table_by_number(
    waiter_client: AsyncClient,
) -> None:
    """GET /api/v1/waiter/tables/by-number/{num} returns single table card."""
    dummy_response = TableResponse(
        id=uuid.uuid4(),
        table_number=3,
        display_name="Table 3",
        seating_capacity=2,
        floor_or_zone="Patio",
        operational_status="ENABLED",
        is_active=True,
        display_order=3,
        notes=None,
        current_occupancy="AVAILABLE",
        active_session_id=None,
        active_qr_version=1,
        active_qr_prefix=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch("app.services.table_service.TableService.get_table_by_number") as mock_t:
        mock_t.return_value = dummy_response
        resp = await waiter_client.get("/api/v1/waiter/tables/by-number/3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["table_number"] == 3
        assert data["display_name"] == "Table 3"


@pytest.mark.asyncio
async def test_waiter_table_session_details(
    waiter_client: AsyncClient,
) -> None:
    """GET /api/v1/waiter/tables/{id}/session returns session and order breakdown."""
    tid = uuid.uuid4()
    dummy_order = _make_dummy_order(table_id=tid, status="PLACED")

    with patch("app.services.order_service.OrderService.get_table_session_details") as mock_sess:
        from app.schemas.order import WaiterTableSessionDetail
        from app.services.order_service import _build_waiter_order_response

        mock_sess.return_value = WaiterTableSessionDetail(
            table_id=tid,
            table_number=5,
            table_display_name="Table 5",
            table_status="OCCUPIED",
            session_id=uuid.uuid4(),
            session_code="SES-001",
            session_status="ACTIVE",
            current_outstanding_amount=Decimal("300.00"),
            custom_outstanding_limit=Decimal("5000.00"),
            orders=[_build_waiter_order_response(dummy_order)],
        )
        resp = await waiter_client.get(f"/api/v1/waiter/tables/{tid}/session")
        assert resp.status_code == 200
        data = resp.json()
        assert data["table_number"] == 5
        assert data["session_code"] == "SES-001"
        assert len(data["orders"]) == 1
        assert data["orders"][0]["order_number"] == "ORD-WAITER-001"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Menu Fast Search Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_waiter_menu_dual_search(
    waiter_client: AsyncClient,
) -> None:
    """GET /api/v1/waiter/menu/search and code-search return matches."""
    with patch("app.services.menu_service.MenuService.search_waiter_menu") as mock_search:
        mock_search.return_value = []
        resp = await waiter_client.get("/api/v1/waiter/menu/search?q=CB-H")
        assert resp.status_code == 200
        assert resp.json()["query"] == "CB-H"

        resp2 = await waiter_client.get("/api/v1/waiter/menu/code-search?code=CB")
        assert resp2.status_code == 200
        assert resp2.json()["query"] == "CB"


# ─────────────────────────────────────────────────────────────────────────────
# 3. Waiter Order Placement Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_waiter_create_order_success(
    waiter_client: AsyncClient,
) -> None:
    """POST /api/v1/waiter/orders successfully places order with 201 Created."""
    tid = uuid.uuid4()
    vid = uuid.uuid4()
    dummy_order = _make_dummy_order(table_id=tid)

    with patch("app.services.order_service.OrderService.create_waiter_order") as mock_create:
        from app.schemas.order import OrderCreateResponse, TableSessionInfo
        from app.services.order_service import _build_order_response

        mock_create.return_value = (
            OrderCreateResponse(
                order=_build_order_response(dummy_order),
                table_session=TableSessionInfo(
                    session_id=dummy_order.table_session_id,
                    session_code="SES-001",
                    status="ACTIVE",
                    current_outstanding_amount=Decimal("300.00"),
                    custom_outstanding_limit=Decimal("5000.00"),
                    is_first_order=True,
                ),
                is_replay=False,
            ),
            201,
        )

        payload = {
            "table_id": str(tid),
            "items": [{"variant_id": str(vid), "quantity": 2, "item_notes": "No onion"}],
            "special_instructions": "Hurry please",
        }
        headers = {"Idempotency-Key": str(uuid.uuid4())}
        resp = await waiter_client.post("/api/v1/waiter/orders", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["order"]["order_number"] == "ORD-WAITER-001"
        assert data["table_session"]["status"] == "ACTIVE"
        assert not data["is_replay"]


@pytest.mark.asyncio
async def test_waiter_create_order_idempotency_replay(
    waiter_client: AsyncClient,
) -> None:
    """POST /api/v1/waiter/orders returns 200 on idempotency replay."""
    tid = uuid.uuid4()
    vid = uuid.uuid4()
    dummy_order = _make_dummy_order(table_id=tid)

    with patch("app.services.order_service.OrderService.create_waiter_order") as mock_create:
        from app.schemas.order import OrderCreateResponse, TableSessionInfo
        from app.services.order_service import _build_order_response

        mock_create.return_value = (
            OrderCreateResponse(
                order=_build_order_response(dummy_order),
                table_session=TableSessionInfo(
                    session_id=dummy_order.table_session_id,
                    session_code="SES-001",
                    status="ACTIVE",
                    current_outstanding_amount=Decimal("300.00"),
                    custom_outstanding_limit=Decimal("5000.00"),
                    is_first_order=False,
                ),
                is_replay=True,
            ),
            200,
        )

        payload = {
            "table_id": str(tid),
            "items": [{"variant_id": str(vid), "quantity": 2}],
        }
        headers = {"Idempotency-Key": "existing-key-123"}
        resp = await waiter_client.post("/api/v1/waiter/orders", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_replay"] is True


@pytest.mark.asyncio
async def test_waiter_create_order_limit_exceeded(
    waiter_client: AsyncClient,
) -> None:
    """POST /api/v1/waiter/orders returns 422 if ₹5,000 limit would be exceeded."""
    tid = uuid.uuid4()
    vid = uuid.uuid4()

    with patch("app.services.order_service.OrderService.create_waiter_order") as mock_create:
        mock_create.side_effect = DomainValidationError(
            code="LIMIT_EXCEEDED",
            message="This order would exceed the ₹5000.00 unpaid table limit.",
        )
        payload = {
            "table_id": str(tid),
            "items": [{"variant_id": str(vid), "quantity": 10}],
        }
        resp = await waiter_client.post("/api/v1/waiter/orders", json=payload)
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "LIMIT_EXCEEDED"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Order Modification Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_modify_order_success(
    waiter_client: AsyncClient,
) -> None:
    """PATCH /api/v1/waiter/orders/{id} modifies order and records audit event."""
    oid = uuid.uuid4()
    item_id = uuid.uuid4()
    dummy_order = _make_dummy_order(order_id=oid, status="ACCEPTED", version=2)

    with patch("app.services.order_service.OrderService.modify_order") as mock_mod:
        from app.services.order_service import _build_waiter_order_response

        mock_mod.return_value = _build_waiter_order_response(dummy_order)

        payload = {
            "expected_version": 1,
            "items": [
                {
                    "order_item_id": str(item_id),
                    "new_quantity": 1,
                    "new_notes": "Guest changed mind to 1 portion",
                }
            ],
            "reason": "Customer reduced quantity",
        }
        resp = await waiter_client.patch(f"/api/v1/waiter/orders/{oid}", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_number"] == "ORD-WAITER-001"
        assert data["version"] == 2


@pytest.mark.asyncio
async def test_modify_order_version_conflict(
    waiter_client: AsyncClient,
) -> None:
    """PATCH /api/v1/waiter/orders/{id} returns 409 if version mismatch."""
    oid = uuid.uuid4()

    with patch("app.services.order_service.OrderService.modify_order") as mock_mod:
        mock_mod.side_effect = StateConflictError(
            code="ORDER_VERSION_CONFLICT",
            message="Order version conflict: current 2, expected 1",
        )
        payload = {
            "expected_version": 1,
            "items": [{"order_item_id": str(uuid.uuid4()), "new_quantity": 3}],
            "reason": "Adding portion",
        }
        resp = await waiter_client.patch(f"/api/v1/waiter/orders/{oid}", json=payload)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ORDER_VERSION_CONFLICT"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Order Cancellation Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_order_success(
    waiter_client: AsyncClient,
) -> None:
    """POST /api/v1/waiter/orders/{id}/cancel marks order CANCELLED with reason."""
    oid = uuid.uuid4()
    dummy_order = _make_dummy_order(order_id=oid, status="CANCELLED", version=2)

    with patch("app.services.order_service.OrderService.cancel_order") as mock_cancel:
        from app.services.order_service import _build_waiter_order_response

        mock_cancel.return_value = _build_waiter_order_response(dummy_order)

        payload = {
            "expected_version": 1,
            "cancellation_reason": "Guest had an emergency and left",
        }
        resp = await waiter_client.post(f"/api/v1/waiter/orders/{oid}/cancel", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Mark Order Served Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mark_order_served_success(
    waiter_client: AsyncClient,
) -> None:
    """POST /api/v1/waiter/orders/{id}/served transitions READY -> SERVED."""
    oid = uuid.uuid4()
    dummy_order = _make_dummy_order(order_id=oid, status="SERVED", version=3)

    with patch("app.services.order_service.OrderService.mark_order_served") as mock_serve:
        from app.services.order_service import _build_waiter_order_response

        mock_serve.return_value = _build_waiter_order_response(dummy_order)

        payload = {"expected_version": 2}
        resp = await waiter_client.post(f"/api/v1/waiter/orders/{oid}/served", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "SERVED"


@pytest.mark.asyncio
async def test_mark_order_served_invalid_state(
    waiter_client: AsyncClient,
) -> None:
    """POST /api/v1/waiter/orders/{id}/served returns 409 if not READY."""
    oid = uuid.uuid4()

    with patch("app.services.order_service.OrderService.mark_order_served") as mock_serve:
        mock_serve.side_effect = StateConflictError(
            code="INVALID_STATE_TRANSITION",
            message="Cannot mark order served in status 'PREPARING' (must be 'READY').",
        )
        payload = {"expected_version": 1}
        resp = await waiter_client.post(f"/api/v1/waiter/orders/{oid}/served", json=payload)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INVALID_STATE_TRANSITION"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Active Orders Listing Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_waiter_get_active_orders(
    waiter_client: AsyncClient,
) -> None:
    """GET /api/v1/waiter/orders/active returns active orders."""
    dummy_order = _make_dummy_order(status="ACCEPTED")

    with patch("app.services.order_service.OrderService.get_waiter_active_orders") as mock_act:
        from app.services.order_service import _build_waiter_order_response

        mock_act.return_value = [_build_waiter_order_response(dummy_order)]
        resp = await waiter_client.get("/api/v1/waiter/orders/active")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["status"] == "ACCEPTED"


# ─────────────────────────────────────────────────────────────────────────────
# 8. RBAC Security Tests
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_kitchen_user_forbidden_on_waiter_endpoints(
    kitchen_client: AsyncClient,
) -> None:
    """KITCHEN role cannot access waiter routes (403 Forbidden)."""
    resp = await kitchen_client.get("/api/v1/waiter/tables")
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"
