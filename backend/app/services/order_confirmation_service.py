"""Waiter confirmation for the first QR order on an empty table (threat T-01).

Problem: a QR code can be photographed and used from outside the restaurant. Without a
check, the first remote order opens a table session, flips the table to OCCUPIED and lands in
the kitchen as PLACED.

Fix: when the table has no ACTIVE session and the setting
`require_waiter_confirmation_for_first_qr_order` is on, the order is *held*:

- the order is saved as `PENDING_CONFIRMATION` on a table session that is also
  `PENDING_CONFIRMATION` (so the table stays AVAILABLE, the kitchen sees nothing, and billing
  ignores it);
- waiters get `order.confirmation_requested` and tap **Confirm** (guests really are seated) or
  **Reject**;
- Confirm turns the order into `PLACED` and the session into `ACTIVE` (same session id, so the
  customer's links stay valid) -> the normal kitchen flow takes over;
- no answer within `qr_confirmation_timeout_seconds` -> the order is auto-cancelled and the
  guest is told to ask a waiter.

Limits: one held request per table (unique partial index) and a restaurant-wide ceiling
`max_pending_qr_confirmations`, so the confirmation queue itself cannot be flooded.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    DomainValidationError,
    ResourceNotFoundError,
    StateConflictError,
)
from app.core.logging import get_logger
from app.core.time_utils import utc_now
from app.models.enums import (
    ActorRole,
    CustomerSessionStatus,
    OrderSource,
    OrderStatus,
    TableSessionStatus,
)
from app.models.identity import User
from app.models.orders import Order, OrderStatusHistory
from app.models.qr_sessions import CustomerSession, TableSession
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.realtime.manager import ws_manager
from app.schemas.order import (
    OrderCreate,
    OrderCreateResponse,
    OrderResponse,
    PendingConfirmationItem,
    PendingConfirmationList,
    WaiterOrderResponse,
)
from app.services.audit_service import AuditService
from app.services.order_service import (
    OrderService,
    _build_order_response,
    _build_session_info,
    _build_waiter_order_response,
    _cap_remaining,
    _exposure_amount,
    _generate_session_code,
    _two_dp,
)

logger = get_logger(__name__)

DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_MAX_PENDING = 15
_ORDER_ENDPOINT = "/api/v1/customer/orders"
_EXPIRY_BATCH = 50

PENDING = OrderStatus.PENDING_CONFIRMATION.value
PENDING_SESSION = TableSessionStatus.PENDING_CONFIRMATION.value


def _int_setting(cfg: RestaurantSettings | None, name: str, default: int) -> int:
    value = getattr(cfg, name, None) if cfg is not None else None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return default
    return value


def timeout_seconds(cfg: RestaurantSettings | None) -> int:
    return _int_setting(cfg, "qr_confirmation_timeout_seconds", DEFAULT_TIMEOUT_SECONDS)


def max_pending(cfg: RestaurantSettings | None) -> int:
    return _int_setting(cfg, "max_pending_qr_confirmations", DEFAULT_MAX_PENDING)


def is_required(cfg: RestaurantSettings | None) -> bool:
    """Secure by default: a missing settings row behaves like the default (ON)."""
    if cfg is None:
        return True
    return cfg.require_waiter_confirmation_for_first_qr_order is True


def expires_at_for(order: Order, cfg: RestaurantSettings | None) -> datetime:
    return order.placed_at + timedelta(seconds=timeout_seconds(cfg))


def _is_expired(order: Order, cfg: RestaurantSettings | None, now: datetime) -> bool:
    return expires_at_for(order, cfg) <= now


class OrderConfirmationService:
    """Hold, confirm, reject, withdraw and expire unconfirmed QR orders."""

    # ────────────────────────────────────────────────────────────────────
    # Customer side: hold the first order
    # ────────────────────────────────────────────────────────────────────

    @classmethod
    async def hold_first_order(
        cls,
        db: AsyncSession,
        *,
        customer_session: CustomerSession,
        resolved_lines: list[dict[str, Any]],
        order_subtotal: Decimal,
        payload: OrderCreate,
        cfg: RestaurantSettings | None,
        idempotency_key: str | None,
        client_ip: str | None,
    ) -> OrderCreateResponse | None:
        """Park the order for waiter confirmation.

        Returns ``None`` when the table already has an ACTIVE session (guests are seated and
        a waiter already opened it), in which case the caller continues the normal flow.
        """
        now = utc_now()
        table_id = customer_session.table_id

        # Serialise against other first-orders and waiter-opened sessions for this table.
        table = await db.scalar(
            select(RestaurantTable).where(RestaurantTable.id == table_id).with_for_update()
        )
        if table is None:
            raise ResourceNotFoundError(
                code="TABLE_NOT_FOUND",
                message="The table associated with your session no longer exists.",
            )

        active_id = await db.scalar(
            select(TableSession.id).where(
                TableSession.table_id == table_id,
                TableSession.status == TableSessionStatus.ACTIVE.value,
            )
        )
        if active_id is not None:
            return None

        if not table.is_active:
            raise StateConflictError(
                code="TABLE_INACTIVE",
                message="This table is no longer active and cannot accept orders.",
            )

        # A stale request must not block a retry: clear it inside this transaction.
        expired = await cls._expire_stale(db, cfg=cfg, now=now, table_id=table_id)
        await db.flush()

        already_pending = await db.scalar(
            select(func.count(TableSession.id)).where(
                TableSession.table_id == table_id,
                TableSession.status == PENDING_SESSION,
            )
        )
        if already_pending:
            raise StateConflictError(
                code="ORDER_AWAITING_CONFIRMATION",
                message=(
                    "Your order is already waiting for a waiter to confirm. "
                    "Please wait a moment or call a waiter."
                ),
            )

        cutoff = now - timedelta(seconds=timeout_seconds(cfg))
        total_pending = (
            await db.scalar(
                select(func.count(Order.id)).where(
                    Order.status == PENDING, Order.placed_at > cutoff
                )
            )
            or 0
        )
        if total_pending >= max_pending(cfg):
            raise StateConflictError(
                code="CONFIRMATION_QUEUE_FULL",
                message="We are very busy right now. Please call a waiter to take your order.",
            )

        limit = (
            cfg.default_session_outstanding_limit
            if cfg is not None and isinstance(cfg.default_session_outstanding_limit, Decimal)
            else Decimal("5000.00")
        )
        if _exposure_amount(order_subtotal, cfg) > limit:
            remaining = _cap_remaining(limit, Decimal("0.00"), cfg)
            raise DomainValidationError(
                code="LIMIT_EXCEEDED",
                message=(
                    f"This order would exceed the ₹{limit} unpaid table limit. "
                    f"You have ₹{remaining} remaining."
                ),
                details={
                    "outstanding_limit": str(limit),
                    "current_outstanding": "0.00",
                    "order_subtotal": str(order_subtotal),
                    "remaining": str(remaining),
                },
            )

        held_session = TableSession(
            session_code=_generate_session_code(),
            table_id=table_id,
            status=PENDING_SESSION,
            opened_by_source=OrderSource.CUSTOMER_QR.value,
            opened_by_customer_session_id=customer_session.id,
            current_outstanding_amount=Decimal("0.00"),
            custom_outstanding_limit=limit,
        )
        db.add(held_session)
        await db.flush()

        order = await OrderService._persist_order(
            db,
            table_session=held_session,
            customer_session=customer_session,
            resolved_lines=resolved_lines,
            order_subtotal=order_subtotal,
            payload=payload,
            is_first_order=True,
            initial_status=OrderStatus.PENDING_CONFIRMATION,
        )
        customer_session.table_session_id = held_session.id

        await AuditService.record_event(
            db,
            action_type="ORDER_CONFIRMATION_REQUESTED",
            entity_type="order",
            entity_id=str(order.id),
            actor_role=ActorRole.CUSTOMER,
            actor_customer_session_id=customer_session.id,
            new_value={"order_number": order.order_number, "subtotal": str(order_subtotal)},
            client_ip=client_ip,
        )
        await db.commit()

        order = await cls._reload(db, order.id)
        order_response = _build_order_response(order)
        order_response.confirmation_expires_at = expires_at_for(order, cfg)
        response = OrderCreateResponse(
            order=order_response,
            table_session=_build_session_info(held_session, is_first_order=True),
            is_replay=False,
            requires_confirmation=True,
            confirmation_expires_at=expires_at_for(order, cfg),
        )

        if idempotency_key:
            await OrderService._store_idempotency(
                db,
                key=idempotency_key,
                actor_scope=str(customer_session.id),
                endpoint_path=_ORDER_ENDPOINT,
                payload=payload,
                response=response,
                status_code=201,
            )
            await db.commit()

        await cls._broadcast_requested(order, cfg)
        await cls._broadcast_resolved_many(expired, cfg, outcome="EXPIRED")
        return response

    # ────────────────────────────────────────────────────────────────────
    # Waiter side
    # ────────────────────────────────────────────────────────────────────

    @classmethod
    async def list_pending(cls, db: AsyncSession) -> PendingConfirmationList:
        """Waiter inbox, oldest first. Stale requests are expired on the way."""
        now = utc_now()
        cfg = await db.get(RestaurantSettings, 1)
        expired = await cls._expire_stale(db, cfg=cfg, now=now)
        if expired:
            await db.commit()
            await cls._broadcast_resolved_many(expired, cfg, outcome="EXPIRED")

        rows = (
            (
                await db.execute(
                    select(Order)
                    .options(
                        selectinload(Order.items),
                        selectinload(Order.table),
                        selectinload(Order.modification_events),
                    )
                    .where(Order.status == PENDING)
                    .order_by(Order.placed_at.asc())
                )
            )
            .scalars()
            .all()
        )
        items = [
            PendingConfirmationItem(
                order=_build_waiter_order_response(o),
                expires_at=expires_at_for(o, cfg),
                seconds_remaining=max(0, int((expires_at_for(o, cfg) - now).total_seconds())),
            )
            for o in rows
        ]
        return PendingConfirmationList(
            items=items, total=len(items), timeout_seconds=timeout_seconds(cfg)
        )

    @classmethod
    async def confirm(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        staff_user: User,
        client_ip: str | None = None,
    ) -> WaiterOrderResponse:
        """Waiter confirms guests are seated: PENDING_CONFIRMATION -> PLACED."""
        now = utc_now()
        cfg = await db.get(RestaurantSettings, 1)
        order = await cls._lock_pending_order(db, order_id)

        table = await db.scalar(
            select(RestaurantTable).where(RestaurantTable.id == order.table_id).with_for_update()
        )
        held_session = await db.scalar(
            select(TableSession).where(TableSession.id == order.table_session_id).with_for_update()
        )
        if held_session is None:
            raise ResourceNotFoundError(
                code="TABLE_SESSION_NOT_FOUND", message="The table session no longer exists."
            )

        if _is_expired(order, cfg, now):
            await cls._finalize(
                db,
                order,
                held_session,
                now=now,
                new_status=OrderStatus.CANCELLED,
                actor_role=ActorRole.SYSTEM,
                reason="Not confirmed by a waiter in time",
            )
            await cls._audit_resolution(db, order, "ORDER_CONFIRMATION_EXPIRED", None, None)
            await db.commit()
            await cls._broadcast_resolved(order, cfg, outcome="EXPIRED")
            raise StateConflictError(
                code="CONFIRMATION_EXPIRED",
                message="This request expired. Ask the guests to place the order again.",
            )

        active = await db.scalar(
            select(TableSession)
            .where(
                TableSession.table_id == order.table_id,
                TableSession.status == TableSessionStatus.ACTIVE.value,
            )
            .with_for_update()
        )

        if active is not None:
            # A waiter already opened the table: merge the held order into that session.
            new_outstanding = active.current_outstanding_amount + order.order_subtotal
            if _exposure_amount(new_outstanding, cfg) > active.custom_outstanding_limit:
                raise DomainValidationError(
                    code="LIMIT_EXCEEDED",
                    message=(
                        f"Confirming would exceed the ₹{active.custom_outstanding_limit} "
                        "unpaid table limit. Reject it or settle the table first."
                    ),
                )
            active.current_outstanding_amount = _two_dp(new_outstanding)
            target = active
            is_first = False
            held_session.status = TableSessionStatus.CLOSED_CANCELLED.value
            held_session.closed_at = now
            held_session.closed_reason = "Merged into the already-open table session"
            await db.execute(
                update(CustomerSession)
                .where(CustomerSession.table_session_id == held_session.id)
                .values(table_session_id=active.id)
            )
            order.table_session_id = active.id
            order.is_first_qr_order_of_session = False
        else:
            held_session.status = TableSessionStatus.ACTIVE.value
            held_session.started_at = now
            held_session.current_outstanding_amount = _two_dp(order.order_subtotal)
            target = held_session
            is_first = True

        order.status = OrderStatus.PLACED.value
        order.placed_at = now  # kitchen queue and SLA clocks start at confirmation
        order.version += 1
        db.add(
            OrderStatusHistory(
                order_id=order.id,
                previous_status=PENDING,
                new_status=OrderStatus.PLACED.value,
                changed_by_role=_role_of(staff_user),
                changed_by_user_id=staff_user.id,
                reason="Waiter confirmed guests are seated",
                changed_at=now,
            )
        )
        await AuditService.record_event(
            db,
            action_type="ORDER_CONFIRMATION_APPROVED",
            entity_type="order",
            entity_id=str(order.id),
            actor_role=_role_of(staff_user),
            actor_user_id=staff_user.id,
            old_value={"status": PENDING},
            new_value={"status": OrderStatus.PLACED.value},
            client_ip=client_ip,
        )
        await db.commit()

        order = await cls._reload(db, order.id)
        await OrderService._broadcast_order_events(
            order=order,
            table_session=target,
            table_id=order.table_id,
            is_first_order=is_first,
        )
        await cls._broadcast_resolved(order, cfg, outcome="CONFIRMED")
        _ = table  # row lock only
        return _build_waiter_order_response(order)

    @classmethod
    async def reject(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        staff_user: User,
        reason: str | None = None,
        client_ip: str | None = None,
    ) -> WaiterOrderResponse:
        """Waiter rejects the request (nobody is at the table): PENDING_CONFIRMATION -> REJECTED."""
        now = utc_now()
        cfg = await db.get(RestaurantSettings, 1)
        order = await cls._lock_pending_order(db, order_id)
        await db.scalar(
            select(RestaurantTable).where(RestaurantTable.id == order.table_id).with_for_update()
        )
        held_session = await db.scalar(
            select(TableSession).where(TableSession.id == order.table_session_id).with_for_update()
        )
        note = (reason or "").strip() or "No guests at the table"
        await cls._finalize(
            db,
            order,
            held_session,
            now=now,
            new_status=OrderStatus.REJECTED,
            actor_role=_role_of(staff_user),
            actor_user_id=staff_user.id,
            reason=note[:200],
        )
        await cls._audit_resolution(
            db, order, "ORDER_CONFIRMATION_REJECTED", staff_user, note[:200], client_ip=client_ip
        )
        await db.commit()

        order = await cls._reload(db, order.id)
        await cls._broadcast_resolved(order, cfg, outcome="REJECTED")
        return _build_waiter_order_response(order)

    # ────────────────────────────────────────────────────────────────────
    # Customer withdraws / system expiry
    # ────────────────────────────────────────────────────────────────────

    @classmethod
    async def withdraw(
        cls,
        db: AsyncSession,
        *,
        order: Order,
        customer_session: CustomerSession,
    ) -> OrderResponse:
        """Customer cancels their own unconfirmed request (nothing was cooked, so always allowed).

        ``order`` must already be loaded ``FOR UPDATE`` by the caller.
        """
        now = utc_now()
        cfg = await db.get(RestaurantSettings, 1)
        held_session = await db.scalar(
            select(TableSession).where(TableSession.id == order.table_session_id).with_for_update()
        )
        await cls._finalize(
            db,
            order,
            held_session,
            now=now,
            new_status=OrderStatus.CANCELLED,
            actor_role=ActorRole.CUSTOMER,
            customer_session_id=customer_session.id,
            reason="Withdrawn by customer before waiter confirmation",
        )
        await AuditService.record_event(
            db,
            action_type="ORDER_CONFIRMATION_WITHDRAWN",
            entity_type="order",
            entity_id=str(order.id),
            actor_role=ActorRole.CUSTOMER,
            actor_customer_session_id=customer_session.id,
            old_value={"status": PENDING},
            new_value={"status": OrderStatus.CANCELLED.value},
        )
        await db.commit()
        order = await cls._reload(db, order.id)
        await cls._broadcast_resolved(order, cfg, outcome="WITHDRAWN")
        response = _build_order_response(order)
        response.never_confirmed = True
        return response

    @classmethod
    async def prepare_customer_view(
        cls, db: AsyncSession, *, table_id: uuid.UUID
    ) -> RestaurantSettings | None:
        """Called before a guest lists orders: expire this table's stale request on the spot."""
        cfg = await db.get(RestaurantSettings, 1)
        expired = await cls._expire_stale(db, cfg=cfg, now=utc_now(), table_id=table_id)
        if expired:
            await db.commit()
            await cls._broadcast_resolved_many(expired, cfg, outcome="EXPIRED")
        return cfg

    @classmethod
    async def annotate_orders(
        cls,
        db: AsyncSession,
        orders: list[Order],
        responses: list[OrderResponse],
        cfg: RestaurantSettings | None,
    ) -> list[OrderResponse]:
        """Fill `confirmation_expires_at` / `never_confirmed` so the guest UI can explain itself."""
        closed_ids = [
            o.id
            for o in orders
            if o.is_first_qr_order_of_session
            and o.status in (OrderStatus.REJECTED.value, OrderStatus.CANCELLED.value)
        ]
        never_confirmed: set[uuid.UUID] = set()
        if closed_ids:
            never_confirmed = set(
                (
                    await db.execute(
                        select(OrderStatusHistory.order_id).where(
                            OrderStatusHistory.order_id.in_(closed_ids),
                            OrderStatusHistory.previous_status == PENDING,
                            OrderStatusHistory.new_status.in_(
                                [OrderStatus.REJECTED.value, OrderStatus.CANCELLED.value]
                            ),
                        )
                    )
                )
                .scalars()
                .all()
            )
        for order, response in zip(orders, responses, strict=True):
            if order.status == PENDING:
                response.confirmation_expires_at = expires_at_for(order, cfg)
            elif order.id in never_confirmed:
                response.never_confirmed = True
        return responses

    @classmethod
    async def expire_stale(cls, db: AsyncSession) -> int:
        """Cancel every request nobody answered in time. Safe to run from many workers."""
        cfg = await db.get(RestaurantSettings, 1)
        expired = await cls._expire_stale(db, cfg=cfg, now=utc_now())
        if not expired:
            return 0
        await db.commit()
        await cls._broadcast_resolved_many(expired, cfg, outcome="EXPIRED")
        return len(expired)

    # ────────────────────────────────────────────────────────────────────
    # Internals
    # ────────────────────────────────────────────────────────────────────

    @classmethod
    async def _lock_pending_order(cls, db: AsyncSession, order_id: uuid.UUID) -> Order:
        order = await db.scalar(
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        if order is None:
            raise ResourceNotFoundError(code="ORDER_NOT_FOUND", message="Order not found.")
        if order.status != PENDING:
            raise StateConflictError(
                code="ORDER_NOT_PENDING_CONFIRMATION",
                message=(
                    f"This request was already handled (status: {order.status}). Refresh the list."
                ),
            )
        return order

    @classmethod
    async def _reload(cls, db: AsyncSession, order_id: uuid.UUID) -> Order:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .execution_options(populate_existing=True)
        )
        return (await db.execute(stmt)).scalar_one()

    @classmethod
    async def _expire_stale(
        cls,
        db: AsyncSession,
        *,
        cfg: RestaurantSettings | None,
        now: datetime,
        table_id: uuid.UUID | None = None,
    ) -> list[Order]:
        cutoff = now - timedelta(seconds=timeout_seconds(cfg))
        stmt = (
            select(Order)
            .options(selectinload(Order.table))
            .where(Order.status == PENDING, Order.placed_at <= cutoff)
            .order_by(Order.placed_at.asc())
            .limit(_EXPIRY_BATCH)
            .with_for_update(skip_locked=True)
        )
        if table_id is not None:
            stmt = stmt.where(Order.table_id == table_id)
        orders = list((await db.execute(stmt)).scalars().all())
        for order in orders:
            held_session = await db.scalar(
                select(TableSession)
                .where(TableSession.id == order.table_session_id)
                .with_for_update()
            )
            await cls._finalize(
                db,
                order,
                held_session,
                now=now,
                new_status=OrderStatus.CANCELLED,
                actor_role=ActorRole.SYSTEM,
                reason="Not confirmed by a waiter in time",
            )
            await cls._audit_resolution(db, order, "ORDER_CONFIRMATION_EXPIRED", None, None)
        return orders

    @classmethod
    async def _finalize(
        cls,
        db: AsyncSession,
        order: Order,
        held_session: TableSession | None,
        *,
        now: datetime,
        new_status: OrderStatus,
        actor_role: ActorRole,
        reason: str,
        actor_user_id: uuid.UUID | None = None,
        customer_session_id: uuid.UUID | None = None,
    ) -> None:
        """Move a held order to REJECTED/CANCELLED and release its held table session."""
        order.status = new_status.value
        order.version += 1
        if new_status is OrderStatus.REJECTED:
            order.rejected_at = now
            order.rejected_by_user_id = actor_user_id
            order.rejection_reason = reason
        else:
            order.cancelled_at = now
            order.cancelled_by_user_id = actor_user_id
            order.cancelled_by_role = actor_role.value
            order.cancellation_reason = reason

        db.add(
            OrderStatusHistory(
                order_id=order.id,
                previous_status=PENDING,
                new_status=new_status.value,
                changed_by_role=actor_role.value,
                changed_by_user_id=actor_user_id,
                changed_by_customer_session_id=customer_session_id,
                reason=reason,
                changed_at=now,
            )
        )
        if held_session is not None and held_session.status == PENDING_SESSION:
            held_session.status = TableSessionStatus.CLOSED_CANCELLED.value
            held_session.closed_at = now
            held_session.closed_reason = reason[:255]
            # Phones that were pointed at the held session go back to "no session yet".
            await db.execute(
                update(CustomerSession)
                .where(
                    CustomerSession.table_session_id == held_session.id,
                    CustomerSession.status == CustomerSessionStatus.ACTIVE.value,
                )
                .values(table_session_id=None)
            )
        await db.flush()

    @classmethod
    async def _audit_resolution(
        cls,
        db: AsyncSession,
        order: Order,
        action_type: str,
        staff_user: User | None,
        reason: str | None,
        *,
        client_ip: str | None = None,
    ) -> None:
        await AuditService.record_event(
            db,
            action_type=action_type,
            entity_type="order",
            entity_id=str(order.id),
            actor_role=_role_of(staff_user) if staff_user else ActorRole.SYSTEM,
            actor_user_id=staff_user.id if staff_user else None,
            reason=reason,
            old_value={"status": PENDING},
            new_value={"status": order.status},
            client_ip=client_ip,
        )

    # ── realtime ────────────────────────────────────────────────────────────

    @classmethod
    async def _broadcast_requested(cls, order: Order, cfg: RestaurantSettings | None) -> None:
        """Alert waiters/admin only. The kitchen is deliberately NOT told."""
        now = utc_now()
        payload = {
            "event": "order.confirmation_requested",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "table_id": str(order.table_id),
            "table_number": order.table.table_number if order.table else None,
            "table_code": order.table.display_name if order.table else "",
            "table_session_id": str(order.table_session_id),
            "order_subtotal": str(order.order_subtotal),
            "item_count": sum(i.active_quantity for i in (order.items or [])),
            "expires_at": expires_at_for(order, cfg).isoformat(),
            "timeout_seconds": timeout_seconds(cfg),
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:waiters", payload)
            await ws_manager.broadcast_to_room("channel:admin", payload)
            await ws_manager.broadcast_to_room(f"table_session:{order.table_session_id}", payload)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after confirmation_requested: %s", exc)

    @classmethod
    async def _broadcast_resolved(
        cls, order: Order, cfg: RestaurantSettings | None, *, outcome: str
    ) -> None:
        now = utc_now()
        payload = {
            "event": "order.confirmation_resolved",
            "outcome": outcome,
            "order_id": str(order.id),
            "order_number": order.order_number,
            "table_id": str(order.table_id),
            "table_code": order.table.display_name if order.table else "",
            "status": order.status,
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:waiters", payload)
            await ws_manager.broadcast_to_room("channel:admin", payload)
            await ws_manager.broadcast_to_room(f"table_session:{order.table_session_id}", payload)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after confirmation_resolved: %s", exc)

    @classmethod
    async def _broadcast_resolved_many(
        cls, orders: list[Order], cfg: RestaurantSettings | None, *, outcome: str
    ) -> None:
        for order in orders:
            await cls._broadcast_resolved(order, cfg, outcome=outcome)


def _role_of(user: User) -> ActorRole:
    try:
        return ActorRole(str(user.role))
    except ValueError:  # pragma: no cover - roles are validated at the DB layer
        return ActorRole.ADMIN
