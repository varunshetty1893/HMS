"""Waiter confirmation for the first QR order on an empty table (threat T-01).

Revision ID: 0012
Revises: 0011
Create Date: 2026-10-19 09:00:00.000000

A customer QR order placed on an AVAILABLE table is parked as `PENDING_CONFIRMATION` (on a
table session that is also `PENDING_CONFIRMATION`, so the table is NOT occupied and the
kitchen never sees it) until a waiter confirms guests are really seated.

Changes
- `orders.status`, `order_status_history.new_status/previous_status` accept `PENDING_CONFIRMATION`.
- `table_sessions.status` accepts `PENDING_CONFIRMATION`; at most one pending session per table.
- `restaurant_settings`: `require_waiter_confirmation_for_first_qr_order` (default ON),
  `qr_confirmation_timeout_seconds` (default 180), `max_pending_qr_confirmations` (default 15).
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

_ORDER_STATUSES_OLD = (
    "'PLACED','ACCEPTED','PREPARING','READY','SERVED','COMPLETED','REJECTED','CANCELLED'"
)
_ORDER_STATUSES_NEW = "'PENDING_CONFIRMATION'," + _ORDER_STATUSES_OLD
_SESSION_STATUSES_OLD = "'ACTIVE','CLOSED_PAID','CLOSED_CANCELLED','CLOSED_ADMIN_OVERRIDE'"
_SESSION_STATUSES_NEW = "'PENDING_CONFIRMATION'," + _SESSION_STATUSES_OLD


def _swap_checks(order_list: str, session_list: str) -> None:
    for table, name, sql in (
        ("orders", "ck_orders_status_valid", f"status IN ({order_list})"),
        (
            "order_status_history",
            "ck_order_status_history_new_status_valid",
            f"new_status IN ({order_list})",
        ),
        (
            "order_status_history",
            "ck_order_status_history_previous_status_valid",
            f"previous_status IS NULL OR previous_status IN ({order_list})",
        ),
        ("table_sessions", "ck_table_sessions_status_valid", f"status IN ({session_list})"),
    ):
        op.drop_constraint(op.f(name), table, type_="check")
        op.create_check_constraint(op.f(name), table, sql)


def upgrade() -> None:
    _swap_checks(_ORDER_STATUSES_NEW, _SESSION_STATUSES_NEW)

    op.create_index(
        "uq_table_sessions_one_pending_per_table",
        "table_sessions",
        ["table_id"],
        unique=True,
        postgresql_where=sa.text("status = 'PENDING_CONFIRMATION'"),
    )
    op.create_index(
        "ix_orders_pending_confirmation",
        "orders",
        ["placed_at"],
        postgresql_where=sa.text("status = 'PENDING_CONFIRMATION'"),
    )

    op.add_column(
        "restaurant_settings",
        sa.Column(
            "require_waiter_confirmation_for_first_qr_order",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )
    op.add_column(
        "restaurant_settings",
        sa.Column(
            "qr_confirmation_timeout_seconds",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("180"),
        ),
    )
    op.add_column(
        "restaurant_settings",
        sa.Column(
            "max_pending_qr_confirmations",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("15"),
        ),
    )
    op.create_check_constraint(
        op.f("ck_restaurant_settings_qr_confirmation_timeout_range"),
        "restaurant_settings",
        "qr_confirmation_timeout_seconds BETWEEN 30 AND 1800",
    )
    op.create_check_constraint(
        op.f("ck_restaurant_settings_max_pending_qr_confirmations_range"),
        "restaurant_settings",
        "max_pending_qr_confirmations BETWEEN 1 AND 100",
    )


def downgrade() -> None:
    # Rows in the new states cannot satisfy the old CHECKs: resolve them first.
    op.execute(
        """
        UPDATE orders
           SET status = 'CANCELLED',
               cancelled_at = COALESCE(cancelled_at, now()),
               cancelled_by_role = COALESCE(cancelled_by_role, 'SYSTEM'),
               cancellation_reason = COALESCE(
                   cancellation_reason, 'Waiter confirmation feature rolled back')
         WHERE status = 'PENDING_CONFIRMATION'
        """
    )
    op.execute(
        """
        UPDATE order_status_history
           SET new_status = 'CANCELLED'
         WHERE new_status = 'PENDING_CONFIRMATION'
        """
    )
    op.execute(
        """
        UPDATE order_status_history
           SET previous_status = 'PLACED'
         WHERE previous_status = 'PENDING_CONFIRMATION'
        """
    )
    op.execute(
        """
        UPDATE table_sessions
           SET status = 'CLOSED_CANCELLED',
               closed_at = COALESCE(closed_at, now()),
               closed_reason = COALESCE(closed_reason, 'Waiter confirmation feature rolled back')
         WHERE status = 'PENDING_CONFIRMATION'
        """
    )

    op.drop_constraint(
        op.f("ck_restaurant_settings_max_pending_qr_confirmations_range"),
        "restaurant_settings",
        type_="check",
    )
    op.drop_constraint(
        op.f("ck_restaurant_settings_qr_confirmation_timeout_range"),
        "restaurant_settings",
        type_="check",
    )
    op.drop_column("restaurant_settings", "max_pending_qr_confirmations")
    op.drop_column("restaurant_settings", "qr_confirmation_timeout_seconds")
    op.drop_column("restaurant_settings", "require_waiter_confirmation_for_first_qr_order")

    op.drop_index("ix_orders_pending_confirmation", table_name="orders")
    op.drop_index("uq_table_sessions_one_pending_per_table", table_name="table_sessions")

    _swap_checks(_ORDER_STATUSES_OLD, _SESSION_STATUSES_OLD)
