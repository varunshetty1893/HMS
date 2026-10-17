"""Table configuration and floor layout management service.

Follows `docs/04-database-design.md` (Section 4), `docs/05-api-specification.md` (Sections 12 & 13),
and `docs/13-final-implementation-blueprint.md` (Phase 5).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ResourceNotFoundError,
    StateConflictError,
)
from app.core.time_utils import utc_now
from app.models.billing import Bill
from app.models.enums import TableOperationalStatus
from app.models.operations import Notification
from app.models.orders import Order
from app.models.qr_sessions import CustomerSession, TableQrToken, TableSession
from app.models.restaurant import RestaurantTable
from app.realtime.manager import ws_manager
from app.models.waiter_requests import WaiterRequest
from app.schemas.table import TableCreate, TableResponse, TableUpdate
from app.services.audit_service import AuditService
from app.services.qr_service import QrService


class TableService:
    """Service governing physical dining tables and live occupancy state derivation."""

    @classmethod
    async def list_tables(
        cls,
        db: AsyncSession,
        active_only: bool = False,
        floor_or_zone: str | None = None,
    ) -> list[TableResponse]:
        """List tables with derived live occupancy (AVAILABLE vs OCCUPIED)."""
        stmt = select(RestaurantTable)
        if active_only:
            stmt = stmt.where(RestaurantTable.is_active.is_(True))
        if floor_or_zone:
            stmt = stmt.where(RestaurantTable.floor_or_zone == floor_or_zone)
        stmt = stmt.order_by(RestaurantTable.display_order, RestaurantTable.table_number)

        tables = (await db.execute(stmt)).scalars().all()
        return [await cls._build_table_response(db, t) for t in tables]

    @classmethod
    async def get_table(cls, db: AsyncSession, table_id: uuid.UUID) -> TableResponse:
        """Fetch a single table with its live occupancy state."""
        stmt = select(RestaurantTable).where(RestaurantTable.id == table_id)
        table = (await db.execute(stmt)).scalar_one_or_none()
        if not table:
            raise ResourceNotFoundError(code="TABLE_NOT_FOUND", message="Table not found.")
        return await cls._build_table_response(db, table)

    @classmethod
    async def get_table_by_number(cls, db: AsyncSession, table_number: int) -> TableResponse:
        """Fetch a single table by table number with its live occupancy state."""
        stmt = select(RestaurantTable).where(RestaurantTable.table_number == table_number)
        table = (await db.execute(stmt)).scalar_one_or_none()
        if not table:
            raise ResourceNotFoundError(
                code="TABLE_NOT_FOUND", message=f"Table {table_number} not found."
            )
        return await cls._build_table_response(db, table)

    @classmethod
    async def create_table(
        cls,
        db: AsyncSession,
        payload: TableCreate,
        user_id: uuid.UUID,
    ) -> TableResponse:
        """Create a new physical dining table and automatically issue its initial v1 QR token."""
        # Uniqueness checks
        num_exists = (
            await db.execute(
                select(RestaurantTable.id).where(
                    RestaurantTable.table_number == payload.table_number
                )
            )
        ).scalar_one_or_none()
        if num_exists:
            raise StateConflictError(
                code="TABLE_NUMBER_EXISTS",
                message=f"Table number {payload.table_number} already exists.",
            )

        name_exists = (
            await db.execute(
                select(RestaurantTable.id).where(
                    func.lower(RestaurantTable.display_name) == payload.display_name.lower().strip()
                )
            )
        ).scalar_one_or_none()
        if name_exists:
            raise StateConflictError(
                code="TABLE_NAME_EXISTS",
                message=f"Table display name '{payload.display_name}' already exists.",
            )

        table = RestaurantTable(
            table_number=payload.table_number,
            display_name=payload.display_name.strip(),
            seating_capacity=payload.seating_capacity,
            floor_or_zone=payload.floor_or_zone.strip() if payload.floor_or_zone else None,
            operational_status=payload.operational_status.value,
            is_active=payload.is_active,
            display_order=payload.display_order,
            notes=payload.notes.strip() if payload.notes else None,
        )
        db.add(table)
        await db.flush()

        # Issue initial v1 active QR token
        qr_token, _ = await QrService.create_initial_qr_token(
            db, table=table, created_by_user_id=user_id
        )

        # Audit log creation
        await AuditService.log_action(
            db,
            actor_user_id=user_id,
            action_type="TABLE_CREATED",
            entity_type="restaurant_tables",
            entity_id=table.id,
            description=f"Created table {table.display_name} (#{table.table_number})",
            new_state={
                "table_number": table.table_number,
                "display_name": table.display_name,
                "seating_capacity": table.seating_capacity,
                "operational_status": table.operational_status,
                "initial_qr_version": qr_token.token_version,
            },
        )

        # Broadcast real-time table status update
        await cls._broadcast_table_update(table, "AVAILABLE")

        return await cls._build_table_response(db, table)

    @classmethod
    async def update_table(
        cls,
        db: AsyncSession,
        table_id: uuid.UUID,
        payload: TableUpdate,
        user_id: uuid.UUID,
    ) -> TableResponse:
        """Update table details. Deactivating requires that no active dining session exists."""
        stmt = select(RestaurantTable).where(RestaurantTable.id == table_id)
        table = (await db.execute(stmt)).scalar_one_or_none()
        if not table:
            raise ResourceNotFoundError(code="TABLE_NOT_FOUND", message="Table not found.")

        # Check active session if attempting to disable or set to MAINTENANCE
        target_operational = (
            payload.operational_status.value
            if payload.operational_status is not None
            else table.operational_status
        )
        target_is_active = payload.is_active if payload.is_active is not None else table.is_active

        if (
            target_operational
            in (TableOperationalStatus.MAINTENANCE.value, TableOperationalStatus.DISABLED.value)
            or not target_is_active
        ):
            # Check if active TableSession exists
            active_session = (
                await db.execute(
                    select(TableSession.id).where(
                        TableSession.table_id == table_id,
                        TableSession.status == "ACTIVE",
                    )
                )
            ).scalar_one_or_none()
            if active_session:
                raise StateConflictError(
                    code="TABLE_HAS_ACTIVE_SESSION",
                    message=(
                        "Cannot disable or set table to maintenance while a dining session "
                        "is active."
                    ),
                )

        # Check display name uniqueness if changed
        if (
            payload.display_name
            and payload.display_name.lower().strip() != table.display_name.lower()
        ):
            name_exists = (
                await db.execute(
                    select(RestaurantTable.id).where(
                        func.lower(RestaurantTable.display_name)
                        == payload.display_name.lower().strip(),
                        RestaurantTable.id != table_id,
                    )
                )
            ).scalar_one_or_none()
            if name_exists:
                raise StateConflictError(
                    code="TABLE_NAME_EXISTS",
                    message=f"Table display name '{payload.display_name}' is already taken.",
                )

        prev_state = {
            "display_name": table.display_name,
            "seating_capacity": table.seating_capacity,
            "floor_or_zone": table.floor_or_zone,
            "operational_status": table.operational_status,
            "is_active": table.is_active,
            "display_order": table.display_order,
        }

        if payload.display_name is not None:
            table.display_name = payload.display_name.strip()
        if payload.seating_capacity is not None:
            table.seating_capacity = payload.seating_capacity
        if payload.floor_or_zone is not None:
            table.floor_or_zone = payload.floor_or_zone.strip() if payload.floor_or_zone else None
        if payload.operational_status is not None:
            table.operational_status = payload.operational_status.value
        if payload.is_active is not None:
            table.is_active = payload.is_active
        if payload.display_order is not None:
            table.display_order = payload.display_order
        if payload.notes is not None:
            table.notes = payload.notes.strip() if payload.notes else None

        await db.flush()

        # Audit log update
        await AuditService.log_action(
            db,
            actor_user_id=user_id,
            action_type="TABLE_UPDATED",
            entity_type="restaurant_tables",
            entity_id=table.id,
            description=f"Updated table {table.display_name}",
            previous_state=prev_state,
            new_state={
                "display_name": table.display_name,
                "seating_capacity": table.seating_capacity,
                "floor_or_zone": table.floor_or_zone,
                "operational_status": table.operational_status,
                "is_active": table.is_active,
                "display_order": table.display_order,
            },
        )

        res = await cls._build_table_response(db, table)
        await cls._broadcast_table_update(table, res.current_occupancy)
        return res

    @classmethod
    async def delete_table(
        cls,
        db: AsyncSession,
        table_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Permanently delete a table that has never been used.

        A table with any order / session / bill / waiter-request history cannot be deleted
        (it would break reports and audit trails); it must be deactivated instead.
        """
        table = (
            await db.execute(select(RestaurantTable).where(RestaurantTable.id == table_id))
        ).scalar_one_or_none()
        if not table:
            raise ResourceNotFoundError(code="TABLE_NOT_FOUND", message="Table not found.")

        for model in (Order, TableSession, CustomerSession, Bill, WaiterRequest):
            used = (
                await db.execute(select(model.id).where(model.table_id == table_id).limit(1))
            ).scalar_one_or_none()
            if used:
                raise StateConflictError(
                    code="TABLE_HAS_HISTORY",
                    message=(
                        "This table has order history and cannot be deleted. "
                        "Deactivate it instead."
                    ),
                )

        name = table.display_name
        await db.execute(update(Notification).where(Notification.table_id == table_id).values(table_id=None))
        await db.execute(delete(TableQrToken).where(TableQrToken.table_id == table_id))
        await db.delete(table)
        await db.flush()

        await AuditService.log_action(
            db,
            actor_user_id=user_id,
            action_type="TABLE_DELETED",
            entity_type="restaurant_tables",
            entity_id=table_id,
            description=f"Deleted table {name}",
            previous_state={"display_name": name},
            new_state=None,
        )

    @classmethod
    async def get_floor_grid(cls, db: AsyncSession) -> list[TableResponse]:
        """Fetch active floor tables for Waiter overview."""
        return await cls.list_tables(db, active_only=True)

    @classmethod
    async def _build_table_response(cls, db: AsyncSession, table: RestaurantTable) -> TableResponse:
        """Derive occupancy and latest active QR token version for a table."""
        # Derive occupancy from table_sessions
        session_stmt = select(TableSession.id).where(
            TableSession.table_id == table.id,
            TableSession.status == "ACTIVE",
        )
        active_session_id = (await db.execute(session_stmt)).scalar_one_or_none()

        # Check for any active unserved or in-progress orders on this table
        active_order_stmt = select(Order.id).where(
            Order.table_id == table.id,
            Order.status.in_(["PLACED", "ACCEPTED", "PREPARING", "READY", "SERVED"]),
        ).limit(1)
        has_active_order = (await db.execute(active_order_stmt)).scalar_one_or_none() is not None

        current_occupancy = "OCCUPIED" if (active_session_id or has_active_order) else "AVAILABLE"

        # Latest active QR token info
        qr_stmt = select(TableQrToken).where(
            TableQrToken.table_id == table.id,
            TableQrToken.status == "ACTIVE",
        )
        active_qr = (await db.execute(qr_stmt)).scalar_one_or_none()

        return TableResponse(
            id=table.id,
            table_number=table.table_number,
            display_name=table.display_name,
            seating_capacity=table.seating_capacity,
            floor_or_zone=table.floor_or_zone,
            operational_status=table.operational_status,
            is_active=table.is_active,
            display_order=table.display_order,
            notes=table.notes,
            current_occupancy=current_occupancy,
            occupancy_status=current_occupancy,
            active_session_id=active_session_id,
            active_qr_version=active_qr.token_version if active_qr else None,
            active_qr_prefix=active_qr.token_prefix if active_qr else None,
            created_at=getattr(table, "created_at", None) or utc_now(),
            updated_at=getattr(table, "updated_at", None) or utc_now(),
        )

    @staticmethod
    async def _broadcast_table_update(table: RestaurantTable, occupancy: str) -> None:
        """Push table.status_changed notification across staff WebSocket channels."""
        event: dict[str, Any] = {
            "event": "table.status_changed",
            "data": {
                "table_id": str(table.id),
                "table_number": table.table_number,
                "display_name": table.display_name,
                "operational_status": table.operational_status,
                "is_active": table.is_active,
                "current_occupancy": occupancy,
            },
        }
        await ws_manager.broadcast_to_room("channel:waiters", event)
        await ws_manager.broadcast_to_room("channel:admin", event)
