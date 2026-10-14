"""Customer order edits: allow non-staff actors on order_modification_events.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-13

Why: customers (QR sessions) can now cancel / edit their own orders. Those events have
no `users` row, so `modified_by_user_id` must be nullable and the customer session is
recorded instead. A CHECK guarantees every event still has *some* actor.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "order_modification_events",
        "modified_by_user_id",
        existing_type=sa.UUID(),
        nullable=True,
    )
    op.add_column(
        "order_modification_events",
        sa.Column("modified_by_customer_session_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_order_modification_events_modified_by_customer_session_id",
        "order_modification_events",
        "customer_sessions",
        ["modified_by_customer_session_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        op.f("ck_order_modification_events_actor_present"),
        "order_modification_events",
        "modified_by_user_id IS NOT NULL OR modified_by_customer_session_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("ck_order_modification_events_actor_present"),
        "order_modification_events",
        type_="check",
    )
    op.drop_constraint(
        "fk_order_modification_events_modified_by_customer_session_id",
        "order_modification_events",
        type_="foreignkey",
    )
    op.drop_column("order_modification_events", "modified_by_customer_session_id")
    # Customer-originated rows have no user; remove them before restoring NOT NULL.
    op.execute("DELETE FROM order_modification_events WHERE modified_by_user_id IS NULL")
    op.alter_column(
        "order_modification_events",
        "modified_by_user_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
