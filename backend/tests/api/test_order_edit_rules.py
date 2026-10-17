"""Business-rule tests for order edits / cancellations (customer + waiter FORCE).

Rules under test
----------------
Customer
  * PLACED / ACCEPTED : may increase, reduce, remove, or switch to a cheaper portion
  * PREPARING         : may ONLY increase (and correct Full -> Half); never reduce/remove
  * READY and later   : not editable
Waiter / Admin
  * PREPARING         : may ADD freely; reduce/remove/cancel needs FORCE (kitchen notified)
  * READY             : only FORCE cancel
  * Kitchen / customer can never force-cancel
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.core.exceptions import (
    AuthorizationError,
    DomainValidationError,
    StateConflictError,
)
from app.models.enums import OrderStatus, UserRole
from app.schemas.order import (
    CustomerOrderItemChange,
    CustomerOrderModifyRequest,
    OrderCancelRequest,
    OrderItemModification,
    OrderModifyRequest,
)
from app.services.order_service import OrderService

SVC = "app.services.order_service"


# ── builders ────────────────────────────────────────────────────────────────────────
def _item(*, qty: int = 2, price: str = "100.00", status: str = "ACTIVE", variant_id=None):
    it = MagicMock()
    it.id = uuid.uuid4()
    it.menu_item_id = uuid.uuid4()
    it.menu_price_variant_id = variant_id or uuid.uuid4()
    it.item_name_snapshot = "Chicken Biryani"
    it.variant_name_snapshot = "Full"
    it.unit_price_snapshot = Decimal(price)
    it.original_quantity = qty
    it.active_quantity = qty
    it.cancelled_quantity = 0
    it.line_subtotal = Decimal(price) * qty
    it.item_status = status
    it.item_notes = None
    return it


def _order(status: str, items: list, *, cust_sess) -> MagicMock:
    o = MagicMock()
    o.id = uuid.uuid4()
    o.order_number = "ORD-1"
    o.status = status
    o.version = 3
    o.customer_session_id = cust_sess.id
    o.table_session_id = uuid.uuid4()
    o.table_id = uuid.uuid4()
    o.items = items
    o.modification_events = []
    o.order_subtotal = sum((i.line_subtotal for i in items), Decimal("0.00"))
    o.has_unacknowledged_mods = False
    return o


def _cust_sess() -> MagicMock:
    s = MagicMock()
    s.id = uuid.uuid4()
    s.table_session_id = None
    return s


def _table_session(outstanding: str = "400.00", limit: str = "5000.00") -> MagicMock:
    ts = MagicMock()
    ts.current_outstanding_amount = Decimal(outstanding)
    ts.custom_outstanding_limit = Decimal(limit)
    return ts


def _db(*scalars) -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    db.scalar.side_effect = list(scalars)
    return db


def _patches():
    """Common patches: no bill, no real session-closing queries, no websocket."""
    return (
        patch(f"{SVC}._ensure_no_issued_bill", AsyncMock()),
        patch(f"{SVC}._close_session_if_no_active_orders", AsyncMock(return_value=False)),
        patch(f"{SVC}._build_order_response", return_value=MagicMock()),
        patch(f"{SVC}.ws_manager.broadcast_to_room", AsyncMock()),
    )


def _req(order, *changes: CustomerOrderItemChange) -> CustomerOrderModifyRequest:
    return CustomerOrderModifyRequest(expected_version=order.version, changes=list(changes))


# ── schema validation ───────────────────────────────────────────────────────────────
def test_change_needs_exactly_one_mode() -> None:
    with pytest.raises(ValidationError):
        CustomerOrderItemChange(order_item_id=uuid.uuid4())
    with pytest.raises(ValidationError):
        CustomerOrderItemChange(
            order_item_id=uuid.uuid4(), new_quantity=1, switch_to_variant_id=uuid.uuid4()
        )


def test_duplicate_lines_rejected() -> None:
    iid = uuid.uuid4()
    with pytest.raises(ValidationError):
        CustomerOrderModifyRequest(
            expected_version=1,
            changes=[
                CustomerOrderItemChange(order_item_id=iid, new_quantity=1),
                CustomerOrderItemChange(order_item_id=iid, new_quantity=2),
            ],
        )


def test_forced_modify_needs_real_reason() -> None:
    with pytest.raises(ValidationError):
        OrderModifyRequest(
            expected_version=1,
            items=[OrderItemModification(order_item_id=uuid.uuid4(), new_quantity=0)],
            reason="x",
            force=True,
        )


# ── customer: modify ────────────────────────────────────────────────────────────────
class TestCustomerModify:
    @pytest.mark.asyncio
    async def test_preparing_cannot_reduce(self) -> None:
        cs, item = _cust_sess(), _item(qty=2)
        order = _order(OrderStatus.PREPARING.value, [item], cust_sess=cs)
        db = _db(order, _table_session())
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            with pytest.raises(StateConflictError) as exc:
                await OrderService.modify_customer_order(
                    db,
                    order_id=order.id,
                    payload=_req(
                        order, CustomerOrderItemChange(order_item_id=item.id, new_quantity=1)
                    ),
                    customer_session=cs,
                )
        assert exc.value.code == "REDUCTION_NOT_ALLOWED_AFTER_COOKING"
        assert item.active_quantity == 2  # untouched

    @pytest.mark.asyncio
    async def test_preparing_cannot_remove_line(self) -> None:
        cs, item = _cust_sess(), _item(qty=2)
        order = _order(OrderStatus.PREPARING.value, [item], cust_sess=cs)
        db = _db(order, _table_session())
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            with pytest.raises(StateConflictError) as exc:
                await OrderService.modify_customer_order(
                    db,
                    order_id=order.id,
                    payload=_req(
                        order, CustomerOrderItemChange(order_item_id=item.id, new_quantity=0)
                    ),
                    customer_session=cs,
                )
        assert exc.value.code == "REDUCTION_NOT_ALLOWED_AFTER_COOKING"

    @pytest.mark.asyncio
    async def test_preparing_can_increase_and_kitchen_must_ack(self) -> None:
        cs, item = _cust_sess(), _item(qty=2, price="60.00")
        order = _order(OrderStatus.PREPARING.value, [item], cust_sess=cs)
        ts = _table_session("120.00")
        variant = MagicMock(is_active=True, is_available=True)
        variant.item = MagicMock(is_active=True, is_available=True)
        db = _db(order, ts, variant)
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            await OrderService.modify_customer_order(
                db,
                order_id=order.id,
                payload=_req(order, CustomerOrderItemChange(order_item_id=item.id, new_quantity=4)),
                customer_session=cs,
            )
        assert item.active_quantity == 4
        assert item.line_subtotal == Decimal("240.00")
        assert ts.current_outstanding_amount == Decimal("240.00")
        assert order.has_unacknowledged_mods is True
        assert order.version == 4
        ev = order.modification_events[0]
        assert ev.modification_type == "QUANTITY_INCREASED"
        assert ev.kitchen_ack_required is True
        assert ev.modified_by_user_id is None
        assert ev.modified_by_customer_session_id == cs.id
        assert ev.modified_by_role == "CUSTOMER"

    @pytest.mark.asyncio
    async def test_increase_blocked_when_item_sold_out(self) -> None:
        cs, item = _cust_sess(), _item(qty=1)
        order = _order(OrderStatus.PREPARING.value, [item], cust_sess=cs)
        variant = MagicMock(is_active=True, is_available=True)
        variant.item = MagicMock(is_active=True, is_available=False)
        db = _db(order, _table_session(), variant)
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            with pytest.raises(DomainValidationError) as exc:
                await OrderService.modify_customer_order(
                    db,
                    order_id=order.id,
                    payload=_req(
                        order, CustomerOrderItemChange(order_item_id=item.id, new_quantity=2)
                    ),
                    customer_session=cs,
                )
        assert exc.value.code == "ITEM_NOT_AVAILABLE"

    @pytest.mark.asyncio
    async def test_increase_respects_table_limit(self) -> None:
        cs, item = _cust_sess(), _item(qty=1, price="1000.00")
        order = _order(OrderStatus.ACCEPTED.value, [item], cust_sess=cs)
        variant = MagicMock(is_active=True, is_available=True)
        variant.item = MagicMock(is_active=True, is_available=True)
        db = _db(order, _table_session("4500.00", "5000.00"), variant)
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            with pytest.raises(DomainValidationError) as exc:
                await OrderService.modify_customer_order(
                    db,
                    order_id=order.id,
                    payload=_req(
                        order, CustomerOrderItemChange(order_item_id=item.id, new_quantity=2)
                    ),
                    customer_session=cs,
                )
        assert exc.value.code == "LIMIT_EXCEEDED"

    @pytest.mark.asyncio
    async def test_placed_can_reduce_without_kitchen_ack(self) -> None:
        cs, item = _cust_sess(), _item(qty=3, price="50.00")
        order = _order(OrderStatus.PLACED.value, [item], cust_sess=cs)
        ts = _table_session("150.00")
        db = _db(order, ts)
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            await OrderService.modify_customer_order(
                db,
                order_id=order.id,
                payload=_req(order, CustomerOrderItemChange(order_item_id=item.id, new_quantity=1)),
                customer_session=cs,
            )
        assert item.active_quantity == 1
        assert item.cancelled_quantity == 2
        assert ts.current_outstanding_amount == Decimal("50.00")
        assert order.has_unacknowledged_mods is False
        assert order.modification_events[0].modification_type == "QUANTITY_DECREASED"

    @pytest.mark.asyncio
    async def test_removing_every_line_before_cooking_cancels_order(self) -> None:
        cs, item = _cust_sess(), _item(qty=1, price="80.00")
        order = _order(OrderStatus.ACCEPTED.value, [item], cust_sess=cs)
        db = _db(order, _table_session("80.00"))
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            await OrderService.modify_customer_order(
                db,
                order_id=order.id,
                payload=_req(order, CustomerOrderItemChange(order_item_id=item.id, new_quantity=0)),
                customer_session=cs,
            )
        assert order.status == OrderStatus.CANCELLED.value
        assert order.cancelled_by_role == "CUSTOMER"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", ["READY", "SERVED", "CANCELLED", "REJECTED"])
    async def test_late_statuses_not_editable(self, status: str) -> None:
        cs, item = _cust_sess(), _item()
        order = _order(status, [item], cust_sess=cs)
        db = _db(order)
        with pytest.raises(StateConflictError) as exc:
            await OrderService.modify_customer_order(
                db,
                order_id=order.id,
                payload=_req(order, CustomerOrderItemChange(order_item_id=item.id, new_quantity=3)),
                customer_session=cs,
            )
        assert exc.value.code == "ORDER_NOT_EDITABLE"

    @pytest.mark.asyncio
    async def test_version_conflict(self) -> None:
        cs, item = _cust_sess(), _item()
        order = _order(OrderStatus.PLACED.value, [item], cust_sess=cs)
        db = _db(order)
        req = CustomerOrderModifyRequest(
            expected_version=order.version - 1,
            changes=[CustomerOrderItemChange(order_item_id=item.id, new_quantity=3)],
        )
        with pytest.raises(StateConflictError) as exc:
            await OrderService.modify_customer_order(
                db, order_id=order.id, payload=req, customer_session=cs
            )
        assert exc.value.code == "ORDER_VERSION_CONFLICT"

    @pytest.mark.asyncio
    async def test_other_table_cannot_edit(self) -> None:
        cs, item = _cust_sess(), _item()
        order = _order(OrderStatus.PLACED.value, [item], cust_sess=cs)
        order.customer_session_id = uuid.uuid4()
        cs.table_session_id = uuid.uuid4()
        db = _db(order)
        with pytest.raises(StateConflictError) as exc:
            await OrderService.modify_customer_order(
                db,
                order_id=order.id,
                payload=_req(order, CustomerOrderItemChange(order_item_id=item.id, new_quantity=3)),
                customer_session=cs,
            )
        assert exc.value.code == "FORBIDDEN"


# ── customer: portion switch (Full -> Half) ─────────────────────────────────────────
def _half_variant(item, price: str = "60.00") -> MagicMock:
    v = MagicMock()
    v.id = uuid.uuid4()
    v.menu_item_id = item.menu_item_id
    v.is_active = True
    v.is_available = True
    v.variant_code = "H"
    v.variant_name = "Half"
    v.quantity_value = Decimal("1.00")
    v.unit = "PORTION"
    v.price = Decimal(price)
    v.item = MagicMock(is_active=True, is_available=True, tax_rate_override=None)
    v.item.id = item.menu_item_id
    v.item.item_code = "CB"
    v.item.name = "Chicken Biryani"
    return v


class TestPortionSwitch:
    @pytest.mark.asyncio
    async def test_full_to_half_allowed_even_while_preparing(self) -> None:
        cs, item = _cust_sess(), _item(qty=1, price="120.00")
        order = _order(OrderStatus.PREPARING.value, [item], cust_sess=cs)
        ts = _table_session("120.00")
        half = _half_variant(item, "70.00")
        db = _db(order, ts, half)
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            await OrderService.modify_customer_order(
                db,
                order_id=order.id,
                payload=_req(
                    order,
                    CustomerOrderItemChange(
                        order_item_id=item.id, switch_to_variant_id=half.id, switch_quantity=1
                    ),
                ),
                customer_session=cs,
            )
        assert item.active_quantity == 0
        assert item.item_status == "CANCELLED"
        assert ts.current_outstanding_amount == Decimal("70.00")  # 120 -> 70
        assert len(order.items) == 2  # a new Half line was opened
        assert order.items[1].variant_name_snapshot == "Half"
        assert order.has_unacknowledged_mods is True  # kitchen is alerted
        assert {e.modification_type for e in order.modification_events} == {
            "ITEM_CANCELLED",
            "ITEM_ADDED",
        }

    @pytest.mark.asyncio
    async def test_switch_to_bigger_portion_rejected(self) -> None:
        cs, item = _cust_sess(), _item(qty=1, price="70.00")
        order = _order(OrderStatus.PLACED.value, [item], cust_sess=cs)
        big = _half_variant(item, "120.00")
        db = _db(order, _table_session(), big)
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            with pytest.raises(DomainValidationError) as exc:
                await OrderService.modify_customer_order(
                    db,
                    order_id=order.id,
                    payload=_req(
                        order,
                        CustomerOrderItemChange(order_item_id=item.id, switch_to_variant_id=big.id),
                    ),
                    customer_session=cs,
                )
        assert exc.value.code == "PORTION_UPGRADE_NOT_ALLOWED"

    @pytest.mark.asyncio
    async def test_switch_to_other_dish_rejected(self) -> None:
        cs, item = _cust_sess(), _item(qty=1, price="120.00")
        order = _order(OrderStatus.PLACED.value, [item], cust_sess=cs)
        other = _half_variant(item)
        other.menu_item_id = uuid.uuid4()
        db = _db(order, _table_session(), other)
        p = _patches()
        with p[0], p[1], p[2], p[3]:
            with pytest.raises(DomainValidationError) as exc:
                await OrderService.modify_customer_order(
                    db,
                    order_id=order.id,
                    payload=_req(
                        order,
                        CustomerOrderItemChange(
                            order_item_id=item.id, switch_to_variant_id=other.id
                        ),
                    ),
                    customer_session=cs,
                )
        assert exc.value.code == "INVALID_PORTION_CHANGE"

    @pytest.mark.asyncio
    async def test_downgrade_blocked_while_preparing_when_flag_off(self) -> None:
        cs, item = _cust_sess(), _item(qty=1, price="120.00")
        order = _order(OrderStatus.PREPARING.value, [item], cust_sess=cs)
        half = _half_variant(item)
        db = _db(order, _table_session(), half)
        p = _patches()
        with (
            p[0],
            p[1],
            p[2],
            p[3],
            patch(f"{SVC}._CUSTOMER_PORTION_DOWNGRADE_WHILE_PREPARING", False),
        ):
            with pytest.raises(StateConflictError) as exc:
                await OrderService.modify_customer_order(
                    db,
                    order_id=order.id,
                    payload=_req(
                        order,
                        CustomerOrderItemChange(
                            order_item_id=item.id, switch_to_variant_id=half.id
                        ),
                    ),
                    customer_session=cs,
                )
        assert exc.value.code == "REDUCTION_NOT_ALLOWED_AFTER_COOKING"


# ── waiter / admin: force cancel + modify ───────────────────────────────────────────
def _staff(role: UserRole) -> MagicMock:
    u = MagicMock()
    u.id = uuid.uuid4()
    u.role = role
    return u


def _w_order(status: str, *, qty: int = 2) -> tuple[MagicMock, MagicMock]:
    cs = _cust_sess()
    item = _item(qty=qty)
    return _order(status, [item], cust_sess=cs), item


class TestWaiterForceCancel:
    @pytest.mark.asyncio
    async def test_preparing_without_force_succeeds_and_alerts_kitchen(self) -> None:
        order, item = _w_order(OrderStatus.PREPARING.value)
        ts = _table_session("200.00")
        db = _db(order, ts)
        payload = OrderCancelRequest(
            expected_version=order.version, cancellation_reason="Guest left", force=False
        )
        bc = AsyncMock()
        with (
            patch(f"{SVC}._ensure_no_issued_bill", AsyncMock()),
            patch(f"{SVC}._close_session_if_no_active_orders", AsyncMock(return_value=False)),
            patch(f"{SVC}._build_waiter_order_response", return_value=MagicMock()),
            patch(f"{SVC}.ws_manager.broadcast_to_room", bc),
        ):
            await OrderService.cancel_order(
                db, order_id=order.id, payload=payload, staff_user=_staff(UserRole.WAITER)
            )
        assert order.status == OrderStatus.CANCELLED.value
        assert item.active_quantity == 0
        assert ts.current_outstanding_amount == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_waiter_force_cancel_preparing_notifies_kitchen(self) -> None:
        order, item = _w_order(OrderStatus.PREPARING.value)
        ts = _table_session("200.00")
        db = _db(order, ts)
        payload = OrderCancelRequest(
            expected_version=order.version, cancellation_reason="Guest left the table", force=True
        )
        bc = AsyncMock()
        with (
            patch(f"{SVC}._ensure_no_issued_bill", AsyncMock()),
            patch(f"{SVC}._close_session_if_no_active_orders", AsyncMock(return_value=False)),
            patch(f"{SVC}._build_waiter_order_response", return_value=MagicMock()),
            patch(f"{SVC}.ws_manager.broadcast_to_room", bc),
        ):
            await OrderService.cancel_order(
                db, order_id=order.id, payload=payload, staff_user=_staff(UserRole.WAITER)
            )
        assert order.status == OrderStatus.CANCELLED.value
        assert item.active_quantity == 0
        assert ts.current_outstanding_amount == Decimal("0.00")
        kitchen_calls = [c for c in bc.await_args_list if c.args[0] == "channel:kitchen"]
        assert kitchen_calls, "kitchen must be notified"
        evt = kitchen_calls[0].args[1]
        assert evt["event"] == "order.cancelled"
        assert evt["forced"] is True
        assert evt["kitchen_action"] == "STOP_COOKING"
        assert evt["cancelled_by_role"] == "WAITER"

    @pytest.mark.asyncio
    async def test_ready_order_needs_force_and_discards(self) -> None:
        order2, _ = _w_order(OrderStatus.READY.value)
        db2 = _db(order2, _table_session("200.00"))
        forced = OrderCancelRequest(
            expected_version=order2.version, cancellation_reason="Wrong table", force=True
        )
        bc = AsyncMock()
        with (
            patch(f"{SVC}._ensure_no_issued_bill", AsyncMock()),
            patch(f"{SVC}._close_session_if_no_active_orders", AsyncMock(return_value=False)),
            patch(f"{SVC}._build_waiter_order_response", return_value=MagicMock()),
            patch(f"{SVC}.ws_manager.broadcast_to_room", bc),
        ):
            await OrderService.cancel_order(
                db2, order_id=order2.id, payload=forced, staff_user=_staff(UserRole.WAITER)
            )
        evt = [c for c in bc.await_args_list if c.args[0] == "channel:kitchen"][0].args[1]
        assert evt["kitchen_action"] == "DISCARD_READY_FOOD"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", ["SERVED", "COMPLETED", "CANCELLED", "REJECTED"])
    async def test_served_or_closed_can_never_be_cancelled(self, status: str) -> None:
        order, _ = _w_order(status)
        db = _db(order)
        payload = OrderCancelRequest(
            expected_version=order.version, cancellation_reason="Oops", force=True
        )
        with pytest.raises(StateConflictError) as exc:
            await OrderService.cancel_order(
                db, order_id=order.id, payload=payload, staff_user=_staff(UserRole.WAITER)
            )
        assert exc.value.code == "INVALID_STATE_TRANSITION"

    @pytest.mark.asyncio
    async def test_kitchen_role_cannot_cancel(self) -> None:
        order, _ = _w_order(OrderStatus.PLACED.value)
        db = _db(order)
        payload = OrderCancelRequest(
            expected_version=order.version, cancellation_reason="nope", force=True
        )
        with pytest.raises(AuthorizationError):
            await OrderService.cancel_order(
                db, order_id=order.id, payload=payload, staff_user=_staff(UserRole.KITCHEN)
            )


class TestWaiterModifyWhilePreparing:
    @pytest.mark.asyncio
    async def test_waiter_can_increase_while_preparing(self) -> None:
        """Regression: adding quantity used to fail with PREPARING_MODIFICATION_BLOCKED."""
        order, item = _w_order(OrderStatus.PREPARING.value, qty=2)
        ts = _table_session("200.00")
        cfg_result = MagicMock()
        cfg_result.scalar_one_or_none.return_value = None
        db = _db(order, ts)  # order, session
        db.execute = AsyncMock(return_value=cfg_result)
        payload = OrderModifyRequest(
            expected_version=order.version,
            items=[OrderItemModification(order_item_id=item.id, new_quantity=3)],
            reason="Guest wants one more",
        )
        with (
            patch(f"{SVC}._ensure_no_issued_bill", AsyncMock()),
            patch(f"{SVC}._build_waiter_order_response", return_value=MagicMock()),
            patch(f"{SVC}.ws_manager.broadcast_to_room", AsyncMock()),
        ):
            await OrderService.modify_order(
                db, order_id=order.id, payload=payload, staff_user=_staff(UserRole.WAITER)
            )
        assert item.active_quantity == 3
        assert order.has_unacknowledged_mods is True

    @pytest.mark.asyncio
    async def test_waiter_reduce_while_preparing_needs_force(self) -> None:
        order, item = _w_order(OrderStatus.PREPARING.value, qty=2)
        # scalars: order, settings (allow_waiter_cancel_preparing_item=False)
        db = _db(order, MagicMock(allow_waiter_cancel_preparing_item=False))
        payload = OrderModifyRequest(
            expected_version=order.version,
            items=[OrderItemModification(order_item_id=item.id, new_quantity=1)],
            reason="Guest wants fewer",
        )
        with patch(f"{SVC}._ensure_no_issued_bill", AsyncMock()):
            with pytest.raises(DomainValidationError) as exc:
                await OrderService.modify_order(
                    db, order_id=order.id, payload=payload, staff_user=_staff(UserRole.WAITER)
                )
        assert exc.value.code == "FORCE_REQUIRED_FOR_REDUCTION"
        assert item.active_quantity == 2
