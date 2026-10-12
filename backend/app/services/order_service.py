"""Unified Order Engine — Phase 6.

Implements `OrderService.create_order` with:
- Atomic first-order `TableSession` creation (`AVAILABLE → OCCUPIED` transition).
- `SELECT ... FOR UPDATE` on `TableSession` to prevent concurrent cap violations.
- Server-authoritative `Decimal` price snapshotting from `menu_price_variants`.
- ₹5,000.00 unpaid-table cap enforcement (configurable via `custom_outstanding_limit`).
- `Idempotency-Key` deduplication (replay returns identical response body, HTTP 200).
- Post-commit WebSocket broadcasts: `table.session_opened`, `table.status_changed`,
  `order.created`.

Follows `docs/05-api-specification.md` Section 7, `docs/06-security-specification.md`
Sections 11 & 13, `docs/13-final-implementation-blueprint.md` Phase 6, and the
concurrency/limit test matrix `LIM-T01..T10` in `docs/09`.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import func, select
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
    ModificationType,
    OrderItemStatus,
    OrderSource,
    OrderStatus,
    TableSessionStatus,
    UserRole,
)
from app.models.identity import User
from app.models.menu import MenuItem, MenuPriceVariant
from app.models.operations import IdempotencyKey
from app.models.orders import Order, OrderItem, OrderModificationEvent, OrderStatusHistory
from app.models.qr_sessions import CustomerSession, TableSession
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.realtime.manager import ws_manager
from app.schemas.kitchen import (
    KitchenCounts,
    KitchenDashboardResponse,
    KitchenItemTicket,
    KitchenModificationEventResponse,
    KitchenOrderTicket,
)
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreate,
    OrderCreateResponse,
    OrderItemResponse,
    OrderModificationEventResponse,
    OrderModifyRequest,
    OrderResponse,
    TableSessionInfo,
    WaiterOrderCreate,
    WaiterOrderResponse,
    WaiterTableSessionDetail,
)
from app.services.audit_service import AuditService

logger = get_logger(__name__)

# Idempotency window: 24 h (matches `docs/04` Section 17)
_IDEMPOTENCY_TTL = timedelta(hours=24)

# Maximum order subtotal on a single submission (individual order safeguard)
_MAX_ORDER_SUBTOTAL = Decimal("25000.00")


def _two_dp(value: Decimal) -> Decimal:
    """Round to 2 decimal places using ROUND_HALF_UP (INR convention)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _generate_order_number() -> str:
    """Generate a unique, human-friendly order number (e.g. 'ORD-A3F9B2')."""
    return "ORD-" + secrets.token_hex(3).upper()


def _generate_session_code() -> str:
    """Generate a short, human-readable table session code (e.g. 'SES-1A2B')."""
    return "SES-" + secrets.token_hex(2).upper()


def _build_order_item_response(item: OrderItem) -> OrderItemResponse:
    return OrderItemResponse(
        id=item.id,
        order_id=item.order_id,
        menu_item_id=item.menu_item_id,
        menu_price_variant_id=item.menu_price_variant_id,
        item_code_snapshot=item.item_code_snapshot,
        item_name_snapshot=item.item_name_snapshot,
        variant_code_snapshot=item.variant_code_snapshot,
        variant_name_snapshot=item.variant_name_snapshot,
        quantity_value_snapshot=item.quantity_value_snapshot,
        unit_snapshot=item.unit_snapshot,
        unit_price_snapshot=item.unit_price_snapshot,
        tax_rate_snapshot=item.tax_rate_snapshot,
        original_quantity=item.original_quantity,
        active_quantity=item.active_quantity,
        cancelled_quantity=item.cancelled_quantity,
        line_subtotal=item.line_subtotal,
        item_status=item.item_status,
        item_notes=item.item_notes,
    )


def _build_order_response(order: Order) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        table_session_id=order.table_session_id,
        table_id=order.table_id,
        source=order.source,
        customer_session_id=order.customer_session_id,
        status=order.status,
        order_subtotal=order.order_subtotal,
        special_instructions=order.special_instructions,
        is_first_qr_order_of_session=order.is_first_qr_order_of_session,
        version=order.version,
        placed_at=order.placed_at,
        accepted_at=order.accepted_at,
        ready_at=order.ready_at,
        served_at=order.served_at,
        has_unacknowledged_mods=order.has_unacknowledged_mods,
        items=[_build_order_item_response(i) for i in (order.items or [])],
    )


def _build_mod_event_response(event: OrderModificationEvent) -> OrderModificationEventResponse:
    return OrderModificationEventResponse(
        id=event.id,
        order_id=event.order_id,
        order_item_id=event.order_item_id,
        modification_type=event.modification_type,
        order_status_at_modification=event.order_status_at_modification,
        previous_quantity=event.previous_quantity,
        new_quantity=event.new_quantity,
        previous_notes=event.previous_notes,
        new_notes=event.new_notes,
        price_delta=event.price_delta,
        reason=event.reason,
        modified_by_role=event.modified_by_role,
        kitchen_ack_required=event.kitchen_ack_required,
        acknowledged_at=event.acknowledged_at,
        created_at=event.created_at,
    )


def _build_waiter_order_response(order: Order) -> WaiterOrderResponse:
    return WaiterOrderResponse(
        id=order.id,
        order_number=order.order_number,
        table_session_id=order.table_session_id,
        table_id=order.table_id,
        table_number=order.table.table_number if order.table else 0,
        table_display_name=order.table.display_name if order.table else "",
        source=order.source,
        customer_session_id=order.customer_session_id,
        status=order.status,
        order_subtotal=order.order_subtotal,
        special_instructions=order.special_instructions,
        is_first_qr_order_of_session=order.is_first_qr_order_of_session,
        has_unacknowledged_mods=order.has_unacknowledged_mods,
        version=order.version,
        placed_at=order.placed_at,
        accepted_at=order.accepted_at,
        ready_at=order.ready_at,
        served_at=order.served_at,
        items=[_build_order_item_response(i) for i in (order.items or [])],
        modification_events=[
            _build_mod_event_response(e) for e in (order.modification_events or [])
        ],
    )


def _build_session_info(table_session: TableSession, *, is_first_order: bool) -> TableSessionInfo:
    return TableSessionInfo(
        session_id=table_session.id,
        session_code=table_session.session_code,
        status=table_session.status,
        current_outstanding_amount=table_session.current_outstanding_amount,
        custom_outstanding_limit=table_session.custom_outstanding_limit,
        is_first_order=is_first_order,
    )


class OrderService:
    """Unified order engine for both `CUSTOMER_QR` and `WAITER` order sources."""

    # ────────────────────────────────────────────────────────────────────
    # Public API
    # ────────────────────────────────────────────────────────────────────

    @classmethod
    async def create_order(
        cls,
        db: AsyncSession,
        *,
        payload: OrderCreate,
        customer_session: CustomerSession,
        idempotency_key: str | None,
        client_ip: str | None = None,
    ) -> tuple[OrderCreateResponse, int]:
        """Place a new customer order, or return a cached response for a replay.

        Returns a ``(response, http_status_code)`` tuple:
        - ``(response, 201)`` for a new order.
        - ``(response, 200)`` for an idempotency replay.

        Steps (all inside a single DB transaction):
        1. Idempotency check — return cached response if already processed.
        2. Validate customer session is still active.
        3. Resolve variant prices server-side (authoritative snapshot).
        4. Compute order subtotal.
        5. Acquire `SELECT ... FOR UPDATE` lock on the `TableSession` row
           (creates a new `TableSession` atomically if the table is `AVAILABLE`).
        6. Enforce ₹5,000 cap.
        7. Persist `Order`, `OrderItem[]`, `OrderStatusHistory`, and update
           `TableSession.current_outstanding_amount`.
        8. Audit log.
        9. Commit, then broadcast WebSocket events.
        """
        # ── 1. Idempotency ────────────────────────────────────────────────
        if idempotency_key:
            cached = await cls._check_idempotency(
                db,
                key=idempotency_key,
                actor_scope=str(customer_session.id),
                endpoint_path="/api/v1/customer/orders",
                payload=payload,
            )
            if cached is not None:
                return cached, 200

        # ── 2. Validate customer session ──────────────────────────────────
        now = utc_now()
        if customer_session.status != CustomerSessionStatus.ACTIVE.value:
            raise StateConflictError(
                code="SESSION_REVOKED",
                message="Your session is no longer active. Please rescan the QR code.",
            )
        if customer_session.expires_at < now:
            raise StateConflictError(
                code="SESSION_EXPIRED",
                message="Your session has expired. Please rescan the table QR code.",
            )

        # ── 3. Resolve variant prices (server-authoritative) ──────────────
        resolved_lines = await cls._resolve_variants(db, payload)

        # ── 4. Compute order subtotal ─────────────────────────────────────
        order_subtotal = _two_dp(
            sum(_two_dp(line["unit_price"] * Decimal(line["quantity"])) for line in resolved_lines)
        )
        if order_subtotal > _MAX_ORDER_SUBTOTAL:
            raise DomainValidationError(
                code="ORDER_SUBTOTAL_LIMIT_EXCEEDED",
                message=f"A single order may not exceed ₹{_MAX_ORDER_SUBTOTAL}.",
            )

        # ── 5. Lock / create TableSession ────────────────────────────────
        table_session, is_first_order = await cls._get_or_create_table_session(
            db,
            table_id=customer_session.table_id,
            customer_session=customer_session,
        )

        # ── 6. ₹5,000 cap enforcement ─────────────────────────────────────
        new_outstanding = table_session.current_outstanding_amount + order_subtotal
        if new_outstanding > table_session.custom_outstanding_limit:
            remaining = _two_dp(
                table_session.custom_outstanding_limit - table_session.current_outstanding_amount
            )
            raise DomainValidationError(
                code="LIMIT_EXCEEDED",
                message=(
                    f"This order would exceed the ₹{table_session.custom_outstanding_limit} "
                    f"unpaid table limit. You have ₹{remaining} remaining."
                ),
                details={
                    "outstanding_limit": str(table_session.custom_outstanding_limit),
                    "current_outstanding": str(table_session.current_outstanding_amount),
                    "order_subtotal": str(order_subtotal),
                    "remaining": str(remaining),
                },
            )

        # ── 7. Persist ────────────────────────────────────────────────────
        order = await cls._persist_order(
            db,
            table_session=table_session,
            customer_session=customer_session,
            resolved_lines=resolved_lines,
            order_subtotal=order_subtotal,
            payload=payload,
            is_first_order=is_first_order,
        )

        # Update outstanding amount on the locked row
        table_session.current_outstanding_amount = _two_dp(new_outstanding)

        # Link customer_session → table_session (if first order opened the session)
        if is_first_order:
            customer_session.table_session_id = table_session.id

        # ── 8. Audit ──────────────────────────────────────────────────────
        await AuditService.record_event(
            db,
            action_type="ORDER_PLACED",
            entity_type="order",
            entity_id=str(order.id),
            actor_role=ActorRole.CUSTOMER,
            actor_customer_session_id=customer_session.id,
            new_value={"order_number": order.order_number, "subtotal": str(order_subtotal)},
            client_ip=client_ip,
        )

        # ── 9. Commit + broadcast ─────────────────────────────────────────
        await db.commit()

        # Refresh order with items for response
        await db.refresh(order)
        stmt = select(Order).options(selectinload(Order.items)).where(Order.id == order.id)
        order = (await db.execute(stmt)).scalar_one()

        response = OrderCreateResponse(
            order=_build_order_response(order),
            table_session=_build_session_info(table_session, is_first_order=is_first_order),
            is_replay=False,
        )

        # Cache for idempotency replay
        if idempotency_key:
            await cls._store_idempotency(
                db,
                key=idempotency_key,
                actor_scope=str(customer_session.id),
                endpoint_path="/api/v1/customer/orders",
                payload=payload,
                response=response,
                status_code=201,
            )
            await db.commit()

        # WebSocket broadcasts (best-effort; never fail the request)
        await cls._broadcast_order_events(
            order=order,
            table_session=table_session,
            table_id=customer_session.table_id,
            is_first_order=is_first_order,
        )

        return response, 201

    @classmethod
    async def list_customer_orders(
        cls,
        db: AsyncSession,
        *,
        customer_session: CustomerSession,
    ) -> list[Order]:
        """Return all orders placed by this customer session, newest first."""
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_session_id == customer_session.id)
            .order_by(Order.placed_at.desc())  # type: ignore[union-attr]
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ────────────────────────────────────────────────────────────────────

    @classmethod
    async def _resolve_variants(
        cls,
        db: AsyncSession,
        payload: OrderCreate,
    ) -> list[dict[str, Any]]:
        """Fetch variant + item details for each requested variant_id.

        Raises 404 if any variant is inactive or missing.
        Raises 422 if the parent menu item is unavailable.
        """
        variant_ids = [item.variant_id for item in payload.items]
        stmt = (
            select(MenuPriceVariant)
            .options(selectinload(MenuPriceVariant.item))
            .where(MenuPriceVariant.id.in_(variant_ids))
        )
        rows: dict[uuid.UUID, MenuPriceVariant] = {
            v.id: v for v in (await db.execute(stmt)).scalars().all()
        }

        resolved: list[dict[str, Any]] = []
        for item_req in payload.items:
            variant = rows.get(item_req.variant_id)
            if not variant:
                raise ResourceNotFoundError(
                    code="VARIANT_NOT_FOUND",
                    message=f"Menu variant {item_req.variant_id} was not found.",
                )
            if not variant.is_available:
                raise DomainValidationError(
                    code="VARIANT_UNAVAILABLE",
                    message=(f"'{variant.variant_name}' is currently unavailable."),
                )
            menu_item: MenuItem = variant.item
            if not menu_item.is_available:
                raise DomainValidationError(
                    code="ITEM_UNAVAILABLE",
                    message=f"'{menu_item.name}' is currently unavailable.",
                )

            resolved.append(
                {
                    "variant": variant,
                    "menu_item": menu_item,
                    "quantity": item_req.quantity,
                    "item_notes": item_req.item_notes,
                    "unit_price": variant.price,  # authoritative Decimal from DB
                    "line_subtotal": _two_dp(variant.price * Decimal(item_req.quantity)),
                    "item_code": menu_item.item_code,
                    "item_name": menu_item.name,
                    "tax_rate": menu_item.tax_rate_override or Decimal("0.00"),
                }
            )
        return resolved

    @classmethod
    async def _get_or_create_table_session(
        cls,
        db: AsyncSession,
        *,
        table_id: uuid.UUID,
        customer_session: CustomerSession,
    ) -> tuple[TableSession, bool]:
        """Return (table_session, is_first_order).

        If an ACTIVE session exists, lock it with FOR UPDATE.
        If none exists (table is AVAILABLE), atomically create one.

        The FOR UPDATE lock ensures that concurrent first-order races cannot both
        create a TableSession (only one transaction wins; the other retries from
        the top and finds the freshly-created session on the next SELECT).
        """
        # Try to get existing ACTIVE session under a row-level lock
        lock_stmt = (
            select(TableSession)
            .where(
                TableSession.table_id == table_id,
                TableSession.status == TableSessionStatus.ACTIVE.value,
            )
            .with_for_update()
        )
        result = await db.execute(lock_stmt)
        existing = result.scalar_one_or_none()

        if existing:
            return existing, False

        # No active session — lock the table row first to prevent double-create
        table_lock_stmt = (
            select(RestaurantTable).where(RestaurantTable.id == table_id).with_for_update()
        )
        table = (await db.execute(table_lock_stmt)).scalar_one_or_none()
        if not table:
            raise ResourceNotFoundError(
                code="TABLE_NOT_FOUND",
                message="The table associated with your session no longer exists.",
            )
        if not table.is_active:
            raise StateConflictError(
                code="TABLE_INACTIVE",
                message="This table is no longer active and cannot accept orders.",
            )

        # Fetch the session limit from RestaurantSettings
        settings_stmt = select(RestaurantSettings).where(RestaurantSettings.id == 1)
        settings = (await db.execute(settings_stmt)).scalar_one_or_none()
        limit = settings.default_session_outstanding_limit if settings else Decimal("5000.00")

        # Double-check that another concurrent transaction didn't sneak in after our lock
        recheck_stmt = (
            select(TableSession)
            .where(
                TableSession.table_id == table_id,
                TableSession.status == TableSessionStatus.ACTIVE.value,
            )
            .with_for_update()
        )
        recheck = (await db.execute(recheck_stmt)).scalar_one_or_none()
        if recheck:
            return recheck, False

        table_session = TableSession(
            session_code=_generate_session_code(),
            table_id=table_id,
            status=TableSessionStatus.ACTIVE.value,
            opened_by_source=OrderSource.CUSTOMER_QR.value,
            opened_by_customer_session_id=customer_session.id,
            current_outstanding_amount=Decimal("0.00"),
            custom_outstanding_limit=limit,
        )
        db.add(table_session)
        # Flush so the PK is available for the Order FK
        await db.flush()
        return table_session, True

    @classmethod
    async def _persist_order(
        cls,
        db: AsyncSession,
        *,
        table_session: TableSession,
        customer_session: CustomerSession,
        resolved_lines: list[dict[str, Any]],
        order_subtotal: Decimal,
        payload: OrderCreate,
        is_first_order: bool,
    ) -> Order:
        """Create and flush `Order`, `OrderItem[]`, and the initial `OrderStatusHistory`."""
        now = utc_now()

        order = Order(
            order_number=_generate_order_number(),
            table_session_id=table_session.id,
            table_id=table_session.table_id,
            source=OrderSource.CUSTOMER_QR.value,
            customer_session_id=customer_session.id,
            status=OrderStatus.PLACED.value,
            order_subtotal=order_subtotal,
            special_instructions=payload.special_instructions,
            is_first_qr_order_of_session=is_first_order,
            version=1,
            placed_at=now,
        )
        db.add(order)
        await db.flush()  # get order.id

        for line in resolved_lines:
            variant: MenuPriceVariant = line["variant"]
            menu_item: MenuItem = line["menu_item"]
            qty: int = line["quantity"]
            line_subtotal: Decimal = line["line_subtotal"]

            order_item = OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                menu_price_variant_id=variant.id,
                # ── historical snapshots ──────────────────────────────
                item_code_snapshot=line.get("item_code", "") or "",
                item_name_snapshot=line.get("item_name", menu_item.name),
                variant_code_snapshot=variant.variant_code,
                variant_name_snapshot=variant.variant_name,
                quantity_value_snapshot=variant.quantity_value,
                unit_snapshot=variant.unit,
                unit_price_snapshot=variant.price,
                tax_rate_snapshot=line.get("tax_rate", Decimal("0.00")),
                # ── mutable quantities ────────────────────────────────
                original_quantity=qty,
                active_quantity=qty,
                cancelled_quantity=0,
                line_subtotal=line_subtotal,
                item_status=OrderItemStatus.ACTIVE.value,
                item_notes=line.get("item_notes"),
            )
            db.add(order_item)

        # Initial status history entry
        status_entry = OrderStatusHistory(
            order_id=order.id,
            previous_status=None,
            new_status=OrderStatus.PLACED.value,
            changed_by_role=ActorRole.CUSTOMER.value,
            changed_by_customer_session_id=customer_session.id,
            changed_at=now,
        )
        db.add(status_entry)
        await db.flush()

        return order

    # ── Idempotency helpers ───────────────────────────────────────────────────

    @staticmethod
    def _hash_payload(payload: OrderCreate) -> str:
        payload_dict = payload.model_dump(mode="json")
        payload_str = json.dumps(payload_dict, sort_keys=True)
        return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    @classmethod
    async def _check_idempotency(
        cls,
        db: AsyncSession,
        *,
        key: str,
        actor_scope: str,
        endpoint_path: str,
        payload: OrderCreate,
    ) -> OrderCreateResponse | None:
        """Return cached OrderCreateResponse if idempotency key was already processed."""
        stmt = select(IdempotencyKey).where(
            IdempotencyKey.idempotency_key == key,
            IdempotencyKey.actor_scope == actor_scope,
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if not row:
            return None

        # Validate request hash matches (same key, same payload)
        request_hash = cls._hash_payload(payload)
        if row.request_hash != request_hash:
            raise StateConflictError(
                code="IDEMPOTENCY_KEY_CONFLICT",
                message=(
                    "The Idempotency-Key was already used with a different request payload. "
                    "Please use a new key for a different request."
                ),
            )

        if row.response_status_code == 201:
            try:
                return OrderCreateResponse.model_validate(row.response_body_json)
            except Exception:
                logger.warning("Failed to deserialise cached idempotency response for key=%s", key)
                return None
        return None

    @classmethod
    async def _store_idempotency(
        cls,
        db: AsyncSession,
        *,
        key: str,
        actor_scope: str,
        endpoint_path: str,
        payload: OrderCreate,
        response: OrderCreateResponse,
        status_code: int,
    ) -> None:
        """Persist the idempotency cache entry (expires in 24 h)."""
        now = utc_now()
        entry = IdempotencyKey(
            idempotency_key=key[:128],
            actor_scope=actor_scope[:100],
            endpoint_path=endpoint_path[:200],
            request_hash=cls._hash_payload(payload),
            response_status_code=status_code,
            response_body_json=response.model_dump(mode="json"),
            expires_at=now + _IDEMPOTENCY_TTL,
        )
        db.add(entry)

    # ── WebSocket broadcast ───────────────────────────────────────────────────

    @staticmethod
    async def _broadcast_order_events(
        *,
        order: Order,
        table_session: TableSession,
        table_id: uuid.UUID,
        is_first_order: bool,
    ) -> None:
        """Best-effort broadcast of order and table events to all relevant channels."""
        now_iso = utc_now().isoformat()
        table_id_str = str(table_id)
        session_id_str = str(table_session.id)
        order_id_str = str(order.id)

        order_payload: dict[str, Any] = {
            "event": "order.created",
            "order_id": order_id_str,
            "order_number": order.order_number,
            "table_session_id": session_id_str,
            "table_id": table_id_str,
            "status": order.status,
            "source": order.source,
            "order_subtotal": str(order.order_subtotal),
            "timestamp": now_iso,
        }

        try:
            await ws_manager.broadcast_to_room("channel:kitchen", order_payload)
            await ws_manager.broadcast_to_room("channel:waiters", order_payload)
            await ws_manager.broadcast_to_room("channel:admin", order_payload)
            await ws_manager.broadcast_to_room(f"table_session:{session_id_str}", order_payload)

            if is_first_order:
                table_opened: dict[str, Any] = {
                    "event": "table.session_opened",
                    "table_id": table_id_str,
                    "table_session_id": session_id_str,
                    "session_code": table_session.session_code,
                    "timestamp": now_iso,
                }
                await ws_manager.broadcast_to_room("channel:waiters", table_opened)
                await ws_manager.broadcast_to_room("channel:admin", table_opened)
                await ws_manager.broadcast_to_room("channel:tables", table_opened)

                table_status: dict[str, Any] = {
                    "event": "table.status_changed",
                    "table_id": table_id_str,
                    "status": "OCCUPIED",
                    "timestamp": now_iso,
                }
                await ws_manager.broadcast_to_room("channel:waiters", table_status)
                await ws_manager.broadcast_to_room("channel:admin", table_status)
                await ws_manager.broadcast_to_room("channel:tables", table_status)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after order.created: %s", exc)

    # ─────────────────────────────────────────────────────────────────────────
    # Phase 7 — Kitchen KDS Workflow
    # ─────────────────────────────────────────────────────────────────────────

    @classmethod
    def _to_kitchen_ticket(cls, order: Order) -> KitchenOrderTicket:
        """Convert Order model to KitchenOrderTicket, ensuring zero financial fields."""
        items = [
            KitchenItemTicket(
                order_item_id=it.id,
                item_code=it.item_code_snapshot,
                item_name=it.item_name_snapshot,
                variant_name=it.variant_name_snapshot,
                original_quantity=it.original_quantity,
                active_quantity=it.active_quantity,
                item_status=it.item_status,
                item_notes=it.item_notes,
            )
            for it in (order.items or [])
        ]

        unacked_mods: list[KitchenModificationEventResponse] = []
        if order.modification_events:
            for mod in order.modification_events:
                if mod.kitchen_ack_required and mod.acknowledged_at is None:
                    unacked_mods.append(
                        KitchenModificationEventResponse(
                            modification_event_id=mod.id,
                            modification_type=mod.modification_type,
                            item_name="Item",
                            previous_quantity=mod.previous_quantity,
                            new_quantity=mod.new_quantity,
                            reason=mod.reason,
                            modified_by_name=None,
                            created_at=mod.created_at,
                        )
                    )

        now = utc_now()
        elapsed = int((now - order.placed_at).total_seconds()) if order.placed_at else 0

        return KitchenOrderTicket(
            id=order.id,
            order_number=order.order_number,
            table_id=order.table_id,
            table_number=order.table.table_number if order.table else 0,
            table_display_name=order.table.display_name
            if order.table
            else f"Table {order.table_id}",
            source=order.source,
            waiter_name=None,
            status=order.status,
            placed_at=order.placed_at,
            accepted_at=order.accepted_at,
            preparing_at=order.preparing_at,
            ready_at=order.ready_at,
            elapsed_seconds=max(0, elapsed),
            version=order.version,
            special_instructions=order.special_instructions,
            has_unacknowledged_mods=order.has_unacknowledged_mods,
            items=items,
            unacknowledged_modifications=unacked_mods,
        )

    @classmethod
    async def get_kitchen_active_orders(
        cls,
        db: AsyncSession,
        status_filter: list[str] | None = None,
    ) -> KitchenDashboardResponse:
        """Retrieve active KDS queue (PLACED, ACCEPTED, PREPARING, READY) ordered FIFO.
        Strictly zero financial fields are included.
        """
        allowed_statuses = [
            OrderStatus.PLACED.value,
            OrderStatus.ACCEPTED.value,
            OrderStatus.PREPARING.value,
            OrderStatus.READY.value,
        ]
        target_statuses = (
            [s for s in status_filter if s in allowed_statuses]
            if status_filter
            else allowed_statuses
        )

        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.status.in_(target_statuses))
            .order_by(Order.placed_at.asc())
        )
        result = await db.execute(stmt)
        orders = list(result.scalars().all())

        counts = KitchenCounts()
        tickets: list[KitchenOrderTicket] = []

        for o in orders:
            if o.status == OrderStatus.PLACED.value:
                counts.placed += 1
            elif o.status == OrderStatus.ACCEPTED.value:
                counts.accepted += 1
            elif o.status == OrderStatus.PREPARING.value:
                counts.preparing += 1
            elif o.status == OrderStatus.READY.value:
                counts.ready += 1

            if o.has_unacknowledged_mods:
                counts.unacknowledged_modifications += 1

            tickets.append(cls._to_kitchen_ticket(o))

        return KitchenDashboardResponse(counts=counts, orders=tickets)

    @classmethod
    async def get_kitchen_order_by_id(
        cls,
        db: AsyncSession,
        order_id: uuid.UUID,
    ) -> KitchenOrderTicket:
        """Fetch single order ticket on KDS with zero financial fields."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")
        return cls._to_kitchen_ticket(order)

    @classmethod
    async def accept_order(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_version: int,
    ) -> KitchenOrderTicket:
        """Kitchen accepts a PLACED order (PLACED -> ACCEPTED)."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")

        if order.version != expected_version:
            raise StateConflictError(
                "ORDER_VERSION_CONFLICT",
                f"Order version conflict: current {order.version}, expected {expected_version}",
            )

        if order.status != OrderStatus.PLACED.value:
            raise StateConflictError(
                "INVALID_STATE_TRANSITION",
                f"Cannot accept order in status '{order.status}' (must be 'PLACED').",
            )

        now = utc_now()
        order.status = OrderStatus.ACCEPTED.value
        order.accepted_at = now
        order.accepted_by_user_id = user_id
        order.version += 1

        history = OrderStatusHistory(
            order_id=order.id,
            previous_status=OrderStatus.PLACED.value,
            new_status=OrderStatus.ACCEPTED.value,
            changed_by_role=ActorRole.KITCHEN.value,
            changed_by_user_id=user_id,
            changed_at=now,
        )
        db.add(history)
        await db.commit()
        await db.refresh(order)

        # Broadcast order.accepted
        payload = {
            "event": "order.accepted",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "table_code": order.table.display_name if order.table else "",
            "previous_status": "PLACED",
            "current_status": "ACCEPTED",
            "accepted_at": now.isoformat(),
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:kitchen", payload)
            await ws_manager.broadcast_to_room("channel:waiters", payload)
            await ws_manager.broadcast_to_room("channel:admin", payload)
            await ws_manager.broadcast_to_room(f"table_session:{order.table_session_id}", payload)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after order.accepted: %s", exc)

        return cls._to_kitchen_ticket(order)

    @classmethod
    async def reject_order(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_version: int,
        rejection_reason: str,
    ) -> KitchenOrderTicket:
        """Kitchen rejects a PLACED order (PLACED -> REJECTED).
        Deducts amount from table session outstanding amount.
        If sole order in session is rejected, resets table to AVAILABLE.
        """
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")

        if order.version != expected_version:
            raise StateConflictError(
                "ORDER_VERSION_CONFLICT",
                f"Order version conflict: current {order.version}, expected {expected_version}",
            )

        if order.status != OrderStatus.PLACED.value:
            raise StateConflictError(
                "INVALID_STATE_TRANSITION",
                f"Cannot reject order in status '{order.status}' (must be 'PLACED').",
            )

        now = utc_now()

        # Lock table session and deduct exposure
        sess_stmt = (
            select(TableSession).where(TableSession.id == order.table_session_id).with_for_update()
        )
        table_session = await db.scalar(sess_stmt)
        if table_session:
            new_outstanding = table_session.current_outstanding_amount - order.order_subtotal
            table_session.current_outstanding_amount = max(Decimal("0.00"), new_outstanding)

        # Check remaining active orders in this table session
        active_count_stmt = select(func.count(Order.id)).where(
            Order.table_session_id == order.table_session_id,
            Order.id != order.id,
            Order.status.not_in([OrderStatus.REJECTED.value, OrderStatus.CANCELLED.value]),
        )
        active_remaining = (await db.scalar(active_count_stmt)) or 0

        table_reset = False
        if active_remaining == 0 and table_session:
            # Sole order rejected — reset table to AVAILABLE and close session
            table_session.status = TableSessionStatus.CLOSED_CANCELLED.value
            table_session.closed_at = now

            table_stmt = (
                select(RestaurantTable)
                .where(RestaurantTable.id == order.table_id)
                .with_for_update()
            )
            table = await db.scalar(table_stmt)
            if table:  # occupancy derived from table_sessions
                table_reset = True

        order.status = OrderStatus.REJECTED.value
        order.rejected_at = now
        order.rejected_by_user_id = user_id
        order.rejection_reason = rejection_reason
        order.version += 1

        history = OrderStatusHistory(
            order_id=order.id,
            previous_status=OrderStatus.PLACED.value,
            new_status=OrderStatus.REJECTED.value,
            changed_by_role=ActorRole.KITCHEN.value,
            changed_by_user_id=user_id,
            reason=rejection_reason,
            changed_at=now,
        )
        db.add(history)

        await AuditService.record_event(
            db,
            action_type="KITCHEN_ORDER_REJECTED",
            entity_type="order",
            entity_id=str(order.id),
            actor_role=ActorRole.KITCHEN,
            actor_user_id=user_id,
            reason=rejection_reason,
            old_value={"status": "PLACED"},
            new_value={"status": "REJECTED", "rejection_reason": rejection_reason},
        )

        await db.commit()
        await db.refresh(order)

        # Broadcast events
        payload = {
            "event": "order.rejected",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "table_code": order.table.display_name if order.table else "",
            "previous_status": "PLACED",
            "current_status": "REJECTED",
            "rejected_at": now.isoformat(),
            "rejection_reason": rejection_reason,
            "table_outstanding_amount": str(table_session.current_outstanding_amount)
            if table_session
            else "0.00",
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:kitchen", payload)
            await ws_manager.broadcast_to_room("channel:waiters", payload)
            await ws_manager.broadcast_to_room("channel:admin", payload)
            await ws_manager.broadcast_to_room(f"table_session:{order.table_session_id}", payload)

            if table_reset:
                table_status_event = {
                    "event": "table.status_changed",
                    "table_id": str(order.table_id),
                    "status": "AVAILABLE",
                    "timestamp": now.isoformat(),
                }
                await ws_manager.broadcast_to_room("channel:waiters", table_status_event)
                await ws_manager.broadcast_to_room("channel:admin", table_status_event)
                await ws_manager.broadcast_to_room("channel:tables", table_status_event)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after order.rejected: %s", exc)

        return cls._to_kitchen_ticket(order)

    @classmethod
    async def start_preparing_order(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_version: int,
    ) -> KitchenOrderTicket:
        """Kitchen starts preparing an ACCEPTED order (ACCEPTED -> PREPARING)."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")

        if order.version != expected_version:
            raise StateConflictError(
                "ORDER_VERSION_CONFLICT",
                f"Order version conflict: current {order.version}, expected {expected_version}",
            )

        if order.status != OrderStatus.ACCEPTED.value:
            raise StateConflictError(
                "INVALID_STATE_TRANSITION",
                f"Cannot start preparing order in status '{order.status}' (must be 'ACCEPTED').",
            )

        now = utc_now()
        order.status = OrderStatus.PREPARING.value
        order.preparing_at = now
        order.preparing_by_user_id = user_id
        order.version += 1

        history = OrderStatusHistory(
            order_id=order.id,
            previous_status=OrderStatus.ACCEPTED.value,
            new_status=OrderStatus.PREPARING.value,
            changed_by_role=ActorRole.KITCHEN.value,
            changed_by_user_id=user_id,
            changed_at=now,
        )
        db.add(history)
        await db.commit()
        await db.refresh(order)

        payload = {
            "event": "order.preparing",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "table_code": order.table.display_name if order.table else "",
            "previous_status": "ACCEPTED",
            "current_status": "PREPARING",
            "preparing_at": now.isoformat(),
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:kitchen", payload)
            await ws_manager.broadcast_to_room("channel:waiters", payload)
            await ws_manager.broadcast_to_room("channel:admin", payload)
            await ws_manager.broadcast_to_room(f"table_session:{order.table_session_id}", payload)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after order.preparing: %s", exc)

        return cls._to_kitchen_ticket(order)

    @classmethod
    async def mark_order_ready(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_version: int,
    ) -> KitchenOrderTicket:
        """Kitchen marks a PREPARING order ready for pickup (PREPARING -> READY).
        Blocked if has_unacknowledged_mods == true.
        """
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")

        if order.version != expected_version:
            raise StateConflictError(
                "ORDER_VERSION_CONFLICT",
                f"Order version conflict: current {order.version}, expected {expected_version}",
            )

        if order.status != OrderStatus.PREPARING.value:
            raise StateConflictError(
                "INVALID_STATE_TRANSITION",
                f"Cannot mark order ready in status '{order.status}' (must be 'PREPARING').",
            )

        if order.has_unacknowledged_mods:
            raise DomainValidationError(
                "ORDER_MODIFICATIONS_UNACKNOWLEDGED",
                "Cannot mark order ready until kitchen acknowledges unacknowledged modifications.",
            )

        now = utc_now()
        order.status = OrderStatus.READY.value
        order.ready_at = now
        order.ready_by_user_id = user_id
        order.version += 1

        history = OrderStatusHistory(
            order_id=order.id,
            previous_status=OrderStatus.PREPARING.value,
            new_status=OrderStatus.READY.value,
            changed_by_role=ActorRole.KITCHEN.value,
            changed_by_user_id=user_id,
            changed_at=now,
        )
        db.add(history)
        await db.commit()
        await db.refresh(order)

        items_summary = [
            {
                "item_name": it.item_name_snapshot,
                "variant_name": it.variant_name_snapshot,
                "active_quantity": it.active_quantity,
            }
            for it in (order.items or [])
            if it.active_quantity > 0
        ]

        payload = {
            "event": "order.ready",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "table_code": order.table.display_name if order.table else "",
            "previous_status": "PREPARING",
            "current_status": "READY",
            "ready_at": now.isoformat(),
            "items_summary": items_summary,
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:kitchen", payload)
            await ws_manager.broadcast_to_room("channel:waiters", payload)
            await ws_manager.broadcast_to_room("channel:admin", payload)
            await ws_manager.broadcast_to_room(f"table_session:{order.table_session_id}", payload)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after order.ready: %s", exc)

        return cls._to_kitchen_ticket(order)

    @classmethod
    async def acknowledge_order_modifications(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user_id: uuid.UUID,
        modification_event_ids: list[uuid.UUID] | None = None,
    ) -> KitchenOrderTicket:
        """Kitchen acknowledges modification events on an order."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")

        now = utc_now()

        # Update pending modification events
        mods_stmt = select(OrderModificationEvent).where(
            OrderModificationEvent.order_id == order.id,
            OrderModificationEvent.acknowledged_at.is_(None),
        )
        if modification_event_ids:
            mods_stmt = mods_stmt.where(OrderModificationEvent.id.in_(modification_event_ids))

        res = await db.execute(mods_stmt)
        pending_mods = list(res.scalars().all())

        for mod in pending_mods:
            mod.acknowledged_by_kitchen_user_id = user_id
            mod.acknowledged_at = now

        # Check if any other unacknowledged mods remain on this order
        remaining_stmt = select(func.count(OrderModificationEvent.id)).where(
            OrderModificationEvent.order_id == order.id,
            OrderModificationEvent.kitchen_ack_required.is_(True),
            OrderModificationEvent.acknowledged_at.is_(None),
        )
        remaining_count = (await db.scalar(remaining_stmt)) or 0
        if remaining_count == 0:
            order.has_unacknowledged_mods = False

        await db.commit()
        await db.refresh(order)

        payload = {
            "event": "order.modification_acknowledged",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "has_unacknowledged_mods": order.has_unacknowledged_mods,
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:kitchen", payload)
            await ws_manager.broadcast_to_room("channel:waiters", payload)
            await ws_manager.broadcast_to_room("channel:admin", payload)
        except Exception as exc:
            logger.warning(
                "WebSocket broadcast failed after order.modification_acknowledged: %s", exc
            )

        return cls._to_kitchen_ticket(order)

    @classmethod
    async def get_kitchen_order_history(
        cls,
        db: AsyncSession,
        *,
        statuses: list[str] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[KitchenOrderTicket]:
        """Fetch past completed/ready/rejected orders for kitchen history view."""
        history_statuses = statuses or [
            OrderStatus.READY.value,
            OrderStatus.SERVED.value,
            OrderStatus.COMPLETED.value,
            OrderStatus.REJECTED.value,
        ]
        offset = max(0, (page - 1) * page_size)
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.status.in_(history_statuses))
            .order_by(Order.placed_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        orders = list(result.scalars().all())
        return [cls._to_kitchen_ticket(o) for o in orders]

    # ────────────────────────────────────────────────────────────────────
    # Waiter Operations (Phase 8)
    # ────────────────────────────────────────────────────────────────────

    @classmethod
    async def create_waiter_order(
        cls,
        db: AsyncSession,
        *,
        payload: WaiterOrderCreate,
        staff_user: User,
        idempotency_key: str | None = None,
        client_ip: str | None = None,
    ) -> tuple[OrderCreateResponse, int]:
        """Place a waiter manual order for a table session.

        Supports rapid tableside order entry. Enforces the same server-authoritative
        pricing snapshots and ₹5,000 unpaid table exposure limit as customer QR orders.
        """
        # ── 1. Idempotency ────────────────────────────────────────────────
        if idempotency_key:
            cached = await cls._check_idempotency(
                db,
                key=idempotency_key,
                actor_scope=str(staff_user.id),
                endpoint_path="/api/v1/waiter/orders",
                payload=payload,
            )
            if cached is not None:
                return cached, 200

        # ── 2. Validate table exists and is operational ───────────────────
        table_stmt = (
            select(RestaurantTable).where(RestaurantTable.id == payload.table_id).with_for_update()
        )
        table = await db.scalar(table_stmt)
        if not table:
            raise ResourceNotFoundError("TABLE_NOT_FOUND", f"Table {payload.table_id} not found.")

        if table.operational_status != "ENABLED":
            raise DomainValidationError(
                "TABLE_NOT_ENABLED",
                f"Table {table.display_name} is currently {table.operational_status} and "
                "cannot accept orders.",
            )

        # ── 3. Resolve variant prices server-side ─────────────────────────
        resolved_lines = await cls._resolve_variants(
            db, OrderCreate(items=payload.items, special_instructions=payload.special_instructions)
        )

        # ── 4. Compute order subtotal ─────────────────────────────────────
        order_subtotal = _two_dp(
            sum(_two_dp(line["unit_price"] * Decimal(line["quantity"])) for line in resolved_lines)
        )
        if order_subtotal > _MAX_ORDER_SUBTOTAL:
            raise DomainValidationError(
                code="ORDER_SUBTOTAL_LIMIT_EXCEEDED",
                message=f"A single order may not exceed ₹{_MAX_ORDER_SUBTOTAL}.",
            )

        # ── 5. Lock / create TableSession ─────────────────────────────────
        sess_stmt = (
            select(TableSession)
            .where(
                TableSession.table_id == table.id,
                TableSession.status == TableSessionStatus.ACTIVE.value,
            )
            .with_for_update()
        )
        table_session = await db.scalar(sess_stmt)
        is_first_order = False
        now = utc_now()

        if not table_session:
            # First order on an available table activates the session
            table_session = TableSession(
                table_id=table.id,
                session_code=_generate_session_code(),
                status=TableSessionStatus.ACTIVE.value,
                current_outstanding_amount=Decimal("0.00"),
                custom_outstanding_limit=Decimal("5000.00"),
                opened_by_source=OrderSource.WAITER.value,
                opened_by_user_id=staff_user.id,
                started_at=now,
            )
            db.add(table_session)
            await db.flush()

            is_first_order = True

        # ── 6. ₹5,000 cap enforcement ─────────────────────────────────────
        new_outstanding = table_session.current_outstanding_amount + order_subtotal
        _cfg = (
            await db.execute(select(RestaurantSettings).where(RestaurantSettings.id == 1))
        ).scalar_one_or_none()
        _enforce_cap = bool(_cfg and _cfg.apply_outstanding_limit_to_waiter_orders)
        if _enforce_cap and new_outstanding > table_session.custom_outstanding_limit:
            remaining = _two_dp(
                table_session.custom_outstanding_limit - table_session.current_outstanding_amount
            )
            raise DomainValidationError(
                code="LIMIT_EXCEEDED",
                message=(
                    f"This order would exceed the ₹{table_session.custom_outstanding_limit} "
                    f"unpaid table limit. You have ₹{remaining} remaining."
                ),
                details={
                    "outstanding_limit": str(table_session.custom_outstanding_limit),
                    "current_outstanding": str(table_session.current_outstanding_amount),
                    "order_subtotal": str(order_subtotal),
                    "remaining": str(remaining),
                },
            )

        # ── 7. Persist Order ──────────────────────────────────────────────
        order = Order(
            order_number=_generate_order_number(),
            table_session_id=table_session.id,
            table_id=table.id,
            source=OrderSource.WAITER.value,
            customer_session_id=None,
            created_by_user_id=staff_user.id,
            status=OrderStatus.PLACED.value,
            order_subtotal=order_subtotal,
            special_instructions=payload.special_instructions,
            is_first_qr_order_of_session=False,
            has_unacknowledged_mods=False,
            version=1,
            placed_at=now,
        )
        db.add(order)
        await db.flush()

        for line in resolved_lines:
            variant: MenuPriceVariant = line["variant"]
            menu_item: MenuItem = line["menu_item"]
            qty: int = line["quantity"]
            unit_price: Decimal = line["unit_price"]
            line_subtotal = _two_dp(unit_price * Decimal(qty))

            item = OrderItem(
                order_id=order.id,
                menu_item_id=menu_item.id,
                menu_price_variant_id=variant.id,
                item_code_snapshot=menu_item.item_code,
                item_name_snapshot=menu_item.name,
                variant_code_snapshot=variant.variant_code,
                variant_name_snapshot=variant.variant_name,
                quantity_value_snapshot=variant.quantity_value,
                unit_snapshot=variant.unit,
                unit_price_snapshot=unit_price,
                tax_rate_snapshot=menu_item.tax_rate_override or Decimal("0.00"),
                original_quantity=qty,
                active_quantity=qty,
                cancelled_quantity=0,
                line_subtotal=line_subtotal,
                item_status=OrderItemStatus.ACTIVE.value,
                item_notes=line.get("item_notes"),
            )
            db.add(item)

        table_session.current_outstanding_amount = _two_dp(
            table_session.current_outstanding_amount + order_subtotal
        )

        history = OrderStatusHistory(
            order_id=order.id,
            previous_status=None,
            new_status=OrderStatus.PLACED.value,
            changed_by_role=ActorRole.WAITER.value,
            changed_by_user_id=staff_user.id,
            changed_at=now,
        )
        db.add(history)

        await AuditService.record_event(
            db,
            action_type="WAITER_ORDER_CREATED",
            entity_type="order",
            entity_id=str(order.id),
            actor_role=ActorRole.WAITER,
            actor_user_id=staff_user.id,
            new_value={
                "order_number": order.order_number,
                "order_subtotal": str(order_subtotal),
                "table_id": str(table.id),
                "item_count": len(resolved_lines),
            },
        )

        # Flush so items/history are persisted, then eagerly reload the order with its
        # items. Reading `order.items` lazily inside an async session raises
        # MissingGreenlet, so the relationship must be loaded explicitly.
        await db.flush()
        order = (
            await db.execute(
                select(Order)
                .options(selectinload(Order.items))
                .where(Order.id == order.id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()

        response_body = OrderCreateResponse(
            order=_build_order_response(order),
            table_session=_build_session_info(table_session, is_first_order=is_first_order),
            is_replay=False,
        )

        if idempotency_key:
            idem_row = IdempotencyKey(
                idempotency_key=idempotency_key,
                actor_scope=str(staff_user.id),
                endpoint_path="/api/v1/waiter/orders",
                request_hash=hashlib.sha256(
                    json.dumps(payload.model_dump(mode="json"), sort_keys=True).encode()
                ).hexdigest(),
                response_body_json=response_body.model_dump(mode="json"),
                response_status_code=201,
                expires_at=now + _IDEMPOTENCY_TTL,
            )
            db.add(idem_row)

        await db.commit()
        await db.refresh(order)
        await db.refresh(table_session)

        # ── 8. WebSocket broadcasts post-commit ───────────────────────────
        try:
            if is_first_order:
                session_opened_event = {
                    "event": "table.session_opened",
                    "table_id": str(table.id),
                    "table_number": table.table_number,
                    "session_id": str(table_session.id),
                    "opened_by": "WAITER",
                    "timestamp": now.isoformat(),
                }
                table_status_event = {
                    "event": "table.status_changed",
                    "table_id": str(table.id),
                    "previous_status": "AVAILABLE",
                    "current_status": "OCCUPIED",
                    "timestamp": now.isoformat(),
                }
                await ws_manager.broadcast_to_room("channel:waiters", session_opened_event)
                await ws_manager.broadcast_to_room("channel:admin", session_opened_event)
                await ws_manager.broadcast_to_room("channel:waiters", table_status_event)
                await ws_manager.broadcast_to_room("channel:admin", table_status_event)
                await ws_manager.broadcast_to_room("channel:tables", table_status_event)

            order_created_event = {
                "event": "order.created",
                "order_id": str(order.id),
                "order_number": order.order_number,
                "table_id": str(table.id),
                "table_code": table.display_name,
                "source": "WAITER",
                "order_subtotal": str(order_subtotal),
                "item_count": len(resolved_lines),
                "timestamp": now.isoformat(),
            }
            await ws_manager.broadcast_to_room("channel:kitchen", order_created_event)
            await ws_manager.broadcast_to_room("channel:waiters", order_created_event)
            await ws_manager.broadcast_to_room("channel:admin", order_created_event)
            await ws_manager.broadcast_to_room(
                f"table_session:{table_session.id}", order_created_event
            )
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after waiter order creation: %s", exc)

        return response_body, 201

    @classmethod
    async def modify_order(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        payload: OrderModifyRequest,
        staff_user: User,
    ) -> WaiterOrderResponse:
        """Modify an active order (pre- or post-acceptance).

        Pre-acceptance (PLACED):
        Updates lines cleanly, logs OrderModificationEvents (kitchen_ack_required=False).

        Post-acceptance (ACCEPTED / PREPARING):
        Appends immutable OrderModificationEvent with mandatory reason, recalculates
        session exposure (checking ₹5,000 cap on increases), sets
        has_unacknowledged_mods=True, and alerts Kitchen KDS.
        """
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")

        if order.version != payload.expected_version:
            raise StateConflictError(
                "ORDER_VERSION_CONFLICT",
                f"Order version conflict: current {order.version}, expected "
                f"{payload.expected_version}",
            )

        allowed_statuses = [
            OrderStatus.PLACED.value,
            OrderStatus.ACCEPTED.value,
            OrderStatus.PREPARING.value,
        ]
        if order.status not in allowed_statuses:
            raise StateConflictError(
                "INVALID_STATE_TRANSITION",
                f"Cannot modify order in status '{order.status}' "
                "(must be PLACED, ACCEPTED, or PREPARING).",
            )

        if order.status == OrderStatus.PREPARING.value and staff_user.role != UserRole.ADMIN:
            settings = await db.scalar(select(RestaurantSettings))
            if not (settings and settings.allow_waiter_cancel_preparing_item):
                raise DomainValidationError(
                    "PREPARING_MODIFICATION_BLOCKED",
                    "Order is already in PREPARING status; modification requires "
                    "Admin authorization.",
                )

        sess_stmt = (
            select(TableSession).where(TableSession.id == order.table_session_id).with_for_update()
        )
        table_session = await db.scalar(sess_stmt)
        if not table_session:
            raise ResourceNotFoundError(
                "TABLE_SESSION_NOT_FOUND", "Associated table session not found."
            )

        is_post_accept = order.status in [OrderStatus.ACCEPTED.value, OrderStatus.PREPARING.value]
        existing_items = {it.id: it for it in (order.items or [])}
        events_to_add: list[OrderModificationEvent] = []
        net_price_delta = Decimal("0.00")

        for mod in payload.items:
            if mod.order_item_id is not None:
                item = existing_items.get(mod.order_item_id)
                if not item:
                    raise ResourceNotFoundError(
                        "ORDER_ITEM_NOT_FOUND",
                        f"Item {mod.order_item_id} not found in order {order.order_number}.",
                    )
                prev_qty = item.active_quantity
                new_qty = mod.new_quantity
                qty_diff = new_qty - prev_qty

                if qty_diff == 0 and (mod.new_notes is None or mod.new_notes == item.item_notes):
                    continue

                price_delta = _two_dp(Decimal(qty_diff) * item.unit_price_snapshot)
                net_price_delta += price_delta

                if new_qty == 0:
                    mod_type = ModificationType.ITEM_CANCELLED.value
                    item.item_status = OrderItemStatus.CANCELLED.value
                    item.cancelled_quantity += prev_qty
                    item.active_quantity = 0
                    item.line_subtotal = Decimal("0.00")
                    item.cancellation_reason = payload.reason
                elif qty_diff > 0:
                    mod_type = ModificationType.QUANTITY_INCREASED.value
                    item.item_status = OrderItemStatus.MODIFIED.value
                    item.active_quantity = new_qty
                    item.line_subtotal = _two_dp(Decimal(new_qty) * item.unit_price_snapshot)
                elif qty_diff < 0:
                    mod_type = ModificationType.QUANTITY_DECREASED.value
                    item.item_status = OrderItemStatus.MODIFIED.value
                    item.cancelled_quantity += prev_qty - new_qty
                    item.active_quantity = new_qty
                    item.line_subtotal = _two_dp(Decimal(new_qty) * item.unit_price_snapshot)
                    item.cancellation_reason = payload.reason
                else:
                    mod_type = ModificationType.NOTES_UPDATED.value

                prev_notes = item.item_notes
                if mod.new_notes is not None:
                    item.item_notes = mod.new_notes

                ev = OrderModificationEvent(
                    order_id=order.id,
                    order_item_id=item.id,
                    modification_type=mod_type,
                    order_status_at_modification=order.status,
                    previous_quantity=prev_qty,
                    new_quantity=new_qty,
                    previous_notes=prev_notes,
                    new_notes=mod.new_notes,
                    unit_price_snapshot=item.unit_price_snapshot,
                    price_delta=price_delta,
                    reason=payload.reason,
                    modified_by_user_id=staff_user.id,
                    modified_by_role=staff_user.role,
                    kitchen_ack_required=is_post_accept,
                )
                events_to_add.append(ev)

            elif mod.variant_id is not None:
                # Adding a new line to this existing order
                v_stmt = (
                    select(MenuPriceVariant)
                    .options(selectinload(MenuPriceVariant.item))
                    .where(MenuPriceVariant.id == mod.variant_id)
                )
                variant = await db.scalar(v_stmt)
                if not variant or not variant.is_active:
                    raise ResourceNotFoundError(
                        "VARIANT_NOT_FOUND", f"Variant {mod.variant_id} not found or inactive."
                    )
                menu_item = variant.item
                if not menu_item or not menu_item.is_active or not menu_item.is_available:
                    raise DomainValidationError(
                        "ITEM_NOT_AVAILABLE",
                        f"Item '{menu_item.name if menu_item else 'Unknown'}' is not available.",
                    )
                if mod.new_quantity <= 0:
                    raise DomainValidationError(
                        "INVALID_QUANTITY", "Added item quantity must be at least 1."
                    )

                unit_price = _two_dp(variant.price)
                line_subtotal = _two_dp(unit_price * Decimal(mod.new_quantity))
                price_delta = line_subtotal
                net_price_delta += price_delta

                new_item = OrderItem(
                    order_id=order.id,
                    menu_item_id=menu_item.id,
                    menu_price_variant_id=variant.id,
                    item_code_snapshot=menu_item.item_code,
                    item_name_snapshot=menu_item.name,
                    variant_code_snapshot=variant.variant_code,
                    variant_name_snapshot=variant.variant_name,
                    quantity_value_snapshot=variant.quantity_value,
                    unit_snapshot=variant.unit,
                    unit_price_snapshot=unit_price,
                    tax_rate_snapshot=menu_item.tax_rate_override or Decimal("0.00"),
                    original_quantity=mod.new_quantity,
                    active_quantity=mod.new_quantity,
                    cancelled_quantity=0,
                    line_subtotal=line_subtotal,
                    item_status=OrderItemStatus.ACTIVE.value,
                    item_notes=mod.new_notes,
                )
                db.add(new_item)
                await db.flush()
                order.items.append(new_item)

                ev = OrderModificationEvent(
                    order_id=order.id,
                    order_item_id=new_item.id,
                    modification_type=ModificationType.ITEM_ADDED.value,
                    order_status_at_modification=order.status,
                    previous_quantity=0,
                    new_quantity=mod.new_quantity,
                    previous_notes=None,
                    new_notes=mod.new_notes,
                    unit_price_snapshot=unit_price,
                    price_delta=price_delta,
                    reason=payload.reason,
                    modified_by_user_id=staff_user.id,
                    modified_by_role=staff_user.role,
                    kitchen_ack_required=is_post_accept,
                )
                events_to_add.append(ev)

        if not events_to_add:
            return _build_waiter_order_response(order)

        # ── ₹5,000 table cap enforcement on net increase ──────────────────
        new_outstanding = table_session.current_outstanding_amount + net_price_delta
        _cfg = (
            await db.execute(select(RestaurantSettings).where(RestaurantSettings.id == 1))
        ).scalar_one_or_none()
        _enforce_cap = bool(_cfg and _cfg.apply_outstanding_limit_to_waiter_orders)
        if _enforce_cap and net_price_delta > 0 and new_outstanding > table_session.custom_outstanding_limit:
            remaining = _two_dp(
                table_session.custom_outstanding_limit - table_session.current_outstanding_amount
            )
            raise DomainValidationError(
                code="LIMIT_EXCEEDED",
                message=(
                    f"Modification would exceed the ₹{table_session.custom_outstanding_limit} "
                    f"unpaid table limit. You have ₹{remaining} remaining."
                ),
                details={
                    "outstanding_limit": str(table_session.custom_outstanding_limit),
                    "current_outstanding": str(table_session.current_outstanding_amount),
                    "price_delta": str(net_price_delta),
                    "remaining": str(remaining),
                },
            )

        table_session.current_outstanding_amount = max(Decimal("0.00"), _two_dp(new_outstanding))
        order.order_subtotal = _two_dp(sum(i.line_subtotal for i in (order.items or [])))

        # Check if all items in order have been cancelled / reduced to 0
        total_active = sum(i.active_quantity for i in (order.items or []))
        order_cancelled = False
        table_reset = False
        now = utc_now()

        if total_active == 0:
            order.status = OrderStatus.CANCELLED.value
            order.cancelled_at = now
            order.cancelled_by_user_id = staff_user.id
            order.cancelled_by_role = staff_user.role
            order.cancellation_reason = payload.reason
            order_cancelled = True

            active_remaining_stmt = select(func.count(Order.id)).where(
                Order.table_session_id == order.table_session_id,
                Order.id != order.id,
                Order.status.not_in([OrderStatus.REJECTED.value, OrderStatus.CANCELLED.value]),
            )
            active_remaining = (await db.scalar(active_remaining_stmt)) or 0
            if active_remaining == 0:
                table_session.status = TableSessionStatus.CLOSED_CANCELLED.value
                table_session.closed_at = now
                t_stmt = (
                    select(RestaurantTable)
                    .where(RestaurantTable.id == order.table_id)
                    .with_for_update()
                )
                table = await db.scalar(t_stmt)
                if table:  # occupancy derived from table_sessions
                    table_reset = True
        elif is_post_accept:
            order.has_unacknowledged_mods = True

        for ev in events_to_add:
            db.add(ev)
            order.modification_events.append(ev)

        order.version += 1

        await AuditService.record_event(
            db,
            action_type="ORDER_MODIFIED",
            entity_type="order",
            entity_id=str(order.id),
            actor_role=staff_user.role,
            actor_user_id=staff_user.id,
            reason=payload.reason,
            old_value={"version": payload.expected_version},
            new_value={
                "version": order.version,
                "order_subtotal": str(order.order_subtotal),
                "net_price_delta": str(net_price_delta),
                "status": order.status,
            },
        )

        await db.commit()
        await db.refresh(order)

        # ── WebSocket broadcast post-commit ───────────────────────────────
        mod_event_payload = {
            "event": "order.modified",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "table_code": order.table.display_name if order.table else "",
            "has_unacknowledged_mods": order.has_unacknowledged_mods,
            "net_price_delta": str(net_price_delta),
            "reason": payload.reason,
            "version": order.version,
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:kitchen", mod_event_payload)
            await ws_manager.broadcast_to_room("channel:waiters", mod_event_payload)
            await ws_manager.broadcast_to_room("channel:admin", mod_event_payload)
            await ws_manager.broadcast_to_room(
                f"table_session:{order.table_session_id}", mod_event_payload
            )

            if order_cancelled:
                cancel_payload = {
                    "event": "order.cancelled",
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "reason": payload.reason,
                    "timestamp": now.isoformat(),
                }
                await ws_manager.broadcast_to_room("channel:kitchen", cancel_payload)
                await ws_manager.broadcast_to_room("channel:waiters", cancel_payload)
                await ws_manager.broadcast_to_room("channel:admin", cancel_payload)

            if table_reset:
                t_event = {
                    "event": "table.status_changed",
                    "table_id": str(order.table_id),
                    "status": "AVAILABLE",
                    "timestamp": now.isoformat(),
                }
                await ws_manager.broadcast_to_room("channel:waiters", t_event)
                await ws_manager.broadcast_to_room("channel:admin", t_event)
                await ws_manager.broadcast_to_room("channel:tables", t_event)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after order.modified: %s", exc)

        return _build_waiter_order_response(order)

    @classmethod
    async def cancel_order(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        payload: OrderCancelRequest,
        staff_user: User,
    ) -> WaiterOrderResponse:
        """Cancel an entire active order.

        Allowed for PLACED or ACCEPTED orders (and PREPARING with Admin).
        Zeros active quantities, subtracts from session exposure, and reverts
        table to AVAILABLE if 0 active orders remain in the session.
        """
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")

        if order.version != payload.expected_version:
            raise StateConflictError(
                "ORDER_VERSION_CONFLICT",
                f"Order version conflict: current {order.version}, expected "
                f"{payload.expected_version}",
            )

        if order.status not in [OrderStatus.PLACED.value, OrderStatus.ACCEPTED.value]:
            if not (
                order.status == OrderStatus.PREPARING.value and staff_user.role == UserRole.ADMIN
            ):
                raise StateConflictError(
                    "INVALID_STATE_TRANSITION",
                    f"Cannot cancel order in status '{order.status}'.",
                )

        sess_stmt = (
            select(TableSession).where(TableSession.id == order.table_session_id).with_for_update()
        )
        table_session = await db.scalar(sess_stmt)

        now = utc_now()
        is_post_accept = order.status in [OrderStatus.ACCEPTED.value, OrderStatus.PREPARING.value]

        for item in order.items or []:
            if item.active_quantity > 0:
                prev_qty = item.active_quantity
                item.cancelled_quantity += prev_qty
                item.active_quantity = 0
                item.line_subtotal = Decimal("0.00")
                item.item_status = OrderItemStatus.CANCELLED.value
                item.cancellation_reason = payload.cancellation_reason

                ev = OrderModificationEvent(
                    order_id=order.id,
                    order_item_id=item.id,
                    modification_type=ModificationType.ITEM_CANCELLED.value,
                    order_status_at_modification=order.status,
                    previous_quantity=prev_qty,
                    new_quantity=0,
                    previous_notes=item.item_notes,
                    new_notes=None,
                    unit_price_snapshot=item.unit_price_snapshot,
                    price_delta=-_two_dp(Decimal(prev_qty) * item.unit_price_snapshot),
                    reason=payload.cancellation_reason,
                    modified_by_user_id=staff_user.id,
                    modified_by_role=staff_user.role,
                    kitchen_ack_required=is_post_accept,
                )
                db.add(ev)
                order.modification_events.append(ev)

        if table_session:
            new_outstanding = _two_dp(
                table_session.current_outstanding_amount - order.order_subtotal
            )
            table_session.current_outstanding_amount = max(Decimal("0.00"), new_outstanding)

        order.order_subtotal = Decimal("0.00")
        prev_status = order.status
        order.status = OrderStatus.CANCELLED.value
        order.cancelled_at = now
        order.cancelled_by_user_id = staff_user.id
        order.cancelled_by_role = staff_user.role
        order.cancellation_reason = payload.cancellation_reason
        order.version += 1

        history = OrderStatusHistory(
            order_id=order.id,
            previous_status=prev_status,
            new_status=OrderStatus.CANCELLED.value,
            changed_by_role=staff_user.role,
            changed_by_user_id=staff_user.id,
            reason=payload.cancellation_reason,
            changed_at=now,
        )
        db.add(history)

        # Check if 0 active orders remain in session
        active_remaining_stmt = select(func.count(Order.id)).where(
            Order.table_session_id == order.table_session_id,
            Order.id != order.id,
            Order.status.not_in([OrderStatus.REJECTED.value, OrderStatus.CANCELLED.value]),
        )
        active_remaining = (await db.scalar(active_remaining_stmt)) or 0
        table_reset = False

        if active_remaining == 0 and table_session:
            table_session.status = TableSessionStatus.CLOSED_CANCELLED.value
            table_session.closed_at = now
            t_stmt = (
                select(RestaurantTable)
                .where(RestaurantTable.id == order.table_id)
                .with_for_update()
            )
            table = await db.scalar(t_stmt)
            if table:  # occupancy derived from table_sessions
                table_reset = True

        await AuditService.record_event(
            db,
            action_type="ORDER_CANCELLED",
            entity_type="order",
            entity_id=str(order.id),
            actor_role=staff_user.role,
            actor_user_id=staff_user.id,
            reason=payload.cancellation_reason,
            old_value={"status": prev_status},
            new_value={"status": "CANCELLED", "cancellation_reason": payload.cancellation_reason},
        )

        await db.commit()
        await db.refresh(order)

        # Broadcast events
        cancel_payload = {
            "event": "order.cancelled",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "table_code": order.table.display_name if order.table else "",
            "previous_status": prev_status,
            "current_status": "CANCELLED",
            "cancelled_at": now.isoformat(),
            "cancellation_reason": payload.cancellation_reason,
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:kitchen", cancel_payload)
            await ws_manager.broadcast_to_room("channel:waiters", cancel_payload)
            await ws_manager.broadcast_to_room("channel:admin", cancel_payload)
            await ws_manager.broadcast_to_room(
                f"table_session:{order.table_session_id}", cancel_payload
            )

            if table_reset:
                t_event = {
                    "event": "table.status_changed",
                    "table_id": str(order.table_id),
                    "status": "AVAILABLE",
                    "timestamp": now.isoformat(),
                }
                await ws_manager.broadcast_to_room("channel:waiters", t_event)
                await ws_manager.broadcast_to_room("channel:admin", t_event)
                await ws_manager.broadcast_to_room("channel:tables", t_event)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after order.cancelled: %s", exc)

        return _build_waiter_order_response(order)

    @classmethod
    async def cancel_customer_order(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        customer_session: CustomerSession,
        reason: str | None = None,
    ) -> OrderResponse:
        """Cancel an entire active order by customer before cooking starts.

        Allowed ONLY while status is PLACED or ACCEPTED.
        Once cooking starts (PREPARING, READY, SERVED), cancellation is forbidden.
        """
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")

        # Ensure order belongs to customer session or active table session
        if (
            order.customer_session_id != customer_session.id
            and order.table_session_id != customer_session.table_session_id
        ):
            raise StateConflictError("FORBIDDEN", "This order does not belong to your table session.")

        if order.status not in [OrderStatus.PLACED.value, OrderStatus.ACCEPTED.value]:
            raise StateConflictError(
                "CANNOT_CANCEL_AFTER_COOKING",
                f"Cooking has already started (status: {order.status}). Order cannot be cancelled.",
            )

        sess_stmt = (
            select(TableSession).where(TableSession.id == order.table_session_id).with_for_update()
        )
        table_session = await db.scalar(sess_stmt)

        now = utc_now()
        cancel_reason = reason or "Cancelled by customer before cooking started"

        for item in order.items or []:
            if item.active_quantity > 0:
                prev_qty = item.active_quantity
                item.cancelled_quantity += prev_qty
                item.active_quantity = 0
                item.line_subtotal = Decimal("0.00")
                item.item_status = OrderItemStatus.CANCELLED.value
                item.cancellation_reason = cancel_reason

                ev = OrderModificationEvent(
                    order_id=order.id,
                    order_item_id=item.id,
                    modification_type=ModificationType.ITEM_CANCELLED.value,
                    order_status_at_modification=order.status,
                    previous_quantity=prev_qty,
                    new_quantity=0,
                    previous_notes=item.item_notes,
                    new_notes=None,
                    unit_price_snapshot=item.unit_price_snapshot,
                    price_delta=-_two_dp(Decimal(prev_qty) * item.unit_price_snapshot),
                    reason=cancel_reason,
                    modified_by_user_id=None,
                    modified_by_role="CUSTOMER_QR",
                    kitchen_ack_required=False,
                )
                db.add(ev)
                order.modification_events.append(ev)

        if table_session:
            new_outstanding = _two_dp(
                table_session.current_outstanding_amount - order.order_subtotal
            )
            table_session.current_outstanding_amount = max(Decimal("0.00"), new_outstanding)

        order.order_subtotal = Decimal("0.00")
        prev_status = order.status
        order.status = OrderStatus.CANCELLED.value
        order.cancelled_at = now
        order.cancelled_by_user_id = None
        order.cancelled_by_role = "CUSTOMER_QR"
        order.cancellation_reason = cancel_reason
        order.version += 1

        history = OrderStatusHistory(
            order_id=order.id,
            previous_status=prev_status,
            new_status=OrderStatus.CANCELLED.value,
            changed_by_role="CUSTOMER_QR",
            changed_by_user_id=None,
            reason=cancel_reason,
            changed_at=now,
        )
        db.add(history)

        await db.commit()
        await db.refresh(order)

        try:
            await ws_manager.broadcast_to_room(
                "kitchen",
                {
                    "event": "order.cancelled",
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "table_id": str(order.table_id),
                    "reason": cancel_reason,
                },
            )
            await ws_manager.broadcast_to_room(
                "channel:waiters",
                {
                    "event": "order.cancelled",
                    "order_id": str(order.id),
                    "order_number": order.order_number,
                    "table_id": str(order.table_id),
                    "reason": cancel_reason,
                },
            )
            if order.table_session_id:
                await ws_manager.broadcast_to_room(
                    f"table_session:{order.table_session_id}",
                    {
                        "event": "order.cancelled",
                        "order_id": str(order.id),
                        "status": "CANCELLED",
                        "reason": cancel_reason,
                    },
                )
        except Exception as exc:
            logger.warning("WebSocket broadcast failed: %s", exc)

        return _build_order_response(order)

    @classmethod
    async def mark_order_served(
        cls,
        db: AsyncSession,
        *,
        order_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_version: int,
    ) -> WaiterOrderResponse:
        """Waiter marks a READY order as SERVED to the table (READY -> SERVED)."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.id == order_id)
            .with_for_update()
        )
        order = await db.scalar(stmt)
        if not order:
            raise ResourceNotFoundError("ORDER_NOT_FOUND", f"Order {order_id} not found.")

        if order.version != expected_version:
            raise StateConflictError(
                "ORDER_VERSION_CONFLICT",
                f"Order version conflict: current {order.version}, expected {expected_version}",
            )

        if order.status != OrderStatus.READY.value:
            raise StateConflictError(
                "INVALID_STATE_TRANSITION",
                f"Cannot mark order served in status '{order.status}' (must be 'READY').",
            )

        now = utc_now()
        order.status = OrderStatus.SERVED.value
        order.served_at = now
        order.served_by_user_id = user_id
        order.version += 1

        history = OrderStatusHistory(
            order_id=order.id,
            previous_status=OrderStatus.READY.value,
            new_status=OrderStatus.SERVED.value,
            changed_by_role=ActorRole.WAITER.value,
            changed_by_user_id=user_id,
            changed_at=now,
        )
        db.add(history)

        await AuditService.record_event(
            db,
            action_type="ORDER_SERVED",
            entity_type="order",
            entity_id=str(order.id),
            actor_role=ActorRole.WAITER,
            actor_user_id=user_id,
            old_value={"status": "READY"},
            new_value={"status": "SERVED", "served_at": now.isoformat()},
        )

        await db.commit()
        await db.refresh(order)

        payload = {
            "event": "order.served",
            "order_id": str(order.id),
            "order_number": order.order_number,
            "table_code": order.table.display_name if order.table else "",
            "previous_status": "READY",
            "current_status": "SERVED",
            "served_at": now.isoformat(),
            "timestamp": now.isoformat(),
        }
        try:
            await ws_manager.broadcast_to_room("channel:kitchen", payload)
            await ws_manager.broadcast_to_room("channel:waiters", payload)
            await ws_manager.broadcast_to_room("channel:admin", payload)
            await ws_manager.broadcast_to_room(f"table_session:{order.table_session_id}", payload)
        except Exception as exc:
            logger.warning("WebSocket broadcast failed after order.served: %s", exc)

        return _build_waiter_order_response(order)

    @classmethod
    async def get_waiter_active_orders(
        cls,
        db: AsyncSession,
        *,
        table_id: uuid.UUID | None = None,
    ) -> list[WaiterOrderResponse]:
        """Fetch active dining floor orders for Waiter App."""
        active_statuses = [
            OrderStatus.PLACED.value,
            OrderStatus.ACCEPTED.value,
            OrderStatus.PREPARING.value,
            OrderStatus.READY.value,
        ]
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items),
                selectinload(Order.table),
                selectinload(Order.modification_events),
            )
            .where(Order.status.in_(active_statuses))
        )
        if table_id:
            stmt = stmt.where(Order.table_id == table_id)

        stmt = stmt.order_by(Order.placed_at.asc())
        result = await db.execute(stmt)
        orders = list(result.scalars().all())
        return [_build_waiter_order_response(o) for o in orders]

    @classmethod
    async def get_table_session_details(
        cls,
        db: AsyncSession,
        *,
        table_id: uuid.UUID,
    ) -> WaiterTableSessionDetail:
        """Retrieve detailed table session information for the Waiter table detail sheet."""
        table_stmt = select(RestaurantTable).where(RestaurantTable.id == table_id)
        table = await db.scalar(table_stmt)
        if not table:
            raise ResourceNotFoundError("TABLE_NOT_FOUND", f"Table {table_id} not found.")

        # Check for active session
        sess_stmt = (
            select(TableSession)
            .options(
                selectinload(TableSession.orders).selectinload(Order.items),
                selectinload(TableSession.orders).selectinload(Order.table),
                selectinload(TableSession.orders).selectinload(Order.modification_events),
            )
            .where(
                TableSession.table_id == table_id,
                TableSession.status == TableSessionStatus.ACTIVE.value,
            )
        )
        session = await db.scalar(sess_stmt)

        orders_response: list[WaiterOrderResponse] = []
        if session and session.orders:
            # Sort newest first for table sheet
            sorted_orders = sorted(session.orders, key=lambda o: o.placed_at, reverse=True)
            orders_response = [_build_waiter_order_response(o) for o in sorted_orders]

        return WaiterTableSessionDetail(
            table_id=table.id,
            table_number=table.table_number,
            table_display_name=table.display_name,
            table_status="OCCUPIED" if session else "AVAILABLE",
            session_id=session.id if session else None,
            session_code=session.session_code if session else None,
            session_status=session.status if session else None,
            current_outstanding_amount=session.current_outstanding_amount
            if session
            else Decimal("0.00"),
            custom_outstanding_limit=session.custom_outstanding_limit
            if session
            else Decimal("5000.00"),
            orders=orders_response,
        )