"""Add the configurable waiter bill-time price override limit.

Revision ID: 0004
Revises: 0003
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "restaurant_settings",
        sa.Column(
            "waiter_max_price_override_percentage",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("0.00"),
        ),
    )
    op.create_check_constraint(
        "waiter_max_price_override_range",
        "restaurant_settings",
        "waiter_max_price_override_percentage >= 0 AND waiter_max_price_override_percentage <= 100",
    )


def downgrade() -> None:
    op.drop_constraint("waiter_max_price_override_range", "restaurant_settings", type_="check")
    op.drop_column("restaurant_settings", "waiter_max_price_override_percentage")
