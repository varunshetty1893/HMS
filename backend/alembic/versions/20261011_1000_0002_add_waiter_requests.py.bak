"""Add waiter_requests table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "waiter_requests",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_session_id", sa.UUID(), nullable=False),
        sa.Column("table_session_id", sa.UUID(), nullable=False),
        sa.Column("table_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("claimed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now() + INTERVAL '15 minutes'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # PK
        sa.PrimaryKeyConstraint("id"),
        # Check constraints
        sa.CheckConstraint(
            "status IN ('PENDING','CLAIMED','COMPLETED','CANCELLED','EXPIRED')",
            name="status_valid",
        ),
        sa.CheckConstraint(
            "reason IN ('ASSISTANCE','CUTLERY','WATER','OTHER')",
            name="reason_valid",
        ),
        # FK
        sa.ForeignKeyConstraint(["customer_session_id"], ["customer_sessions.id"]),
        sa.ForeignKeyConstraint(["table_session_id"], ["table_sessions.id"]),
        sa.ForeignKeyConstraint(["table_id"], ["restaurant_tables.id"]),
        sa.ForeignKeyConstraint(["claimed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["completed_by_user_id"], ["users.id"]),
    )

    # Partial unique index — only one PENDING/CLAIMED request per table session
    op.create_index(
        "uq_waiter_requests_one_open_per_table_session",
        "waiter_requests",
        ["table_session_id"],
        unique=True,
        postgresql_where=sa.text("status IN ('PENDING', 'CLAIMED')"),
    )
    # Supporting indexes
    op.create_index(
        "ix_waiter_requests_table_session_status",
        "waiter_requests",
        ["table_session_id", "status"],
    )
    op.create_index(
        "ix_waiter_requests_status_created_at",
        "waiter_requests",
        ["status", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_waiter_requests_status_created_at", table_name="waiter_requests")
    op.drop_index("ix_waiter_requests_table_session_status", table_name="waiter_requests")
    op.drop_index(
        "uq_waiter_requests_one_open_per_table_session", table_name="waiter_requests"
    )
    op.drop_table("waiter_requests")
