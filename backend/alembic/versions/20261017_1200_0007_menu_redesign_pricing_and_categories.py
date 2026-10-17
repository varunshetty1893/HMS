"""Add serving description, pricing type, and seasonal pricing support.

Revision ID: 0007
Revises: 0006
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add serving_description and pricing_type to menu_items
    op.add_column(
        "menu_items",
        sa.Column("serving_description", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "menu_items",
        sa.Column(
            "pricing_type",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'FIXED'"),
        ),
    )
    op.create_check_constraint(
        "pricing_type_valid",
        "menu_items",
        "pricing_type IN ('FIXED', 'SEASONAL')",
    )

    # 2. Allow price to be NULL on menu_price_variants (for seasonal / market pricing)
    op.alter_column(
        "menu_price_variants",
        "price",
        existing_type=sa.Numeric(precision=10, scale=2),
        nullable=True,
    )
    op.drop_constraint("price_non_negative", "menu_price_variants", type_="check")
    op.create_check_constraint(
        "price_non_negative",
        "menu_price_variants",
        "price IS NULL OR price >= 0",
    )

    # 3. Add pricing_status to menu_price_variants
    op.add_column(
        "menu_price_variants",
        sa.Column(
            "pricing_status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'ACTIVE'"),
        ),
    )
    op.create_check_constraint(
        "pricing_status_valid",
        "menu_price_variants",
        "pricing_status IN ('ACTIVE', 'SEASONAL_UNPRICED')",
    )


def downgrade() -> None:
    op.drop_constraint("pricing_status_valid", "menu_price_variants", type_="check")
    op.drop_column("menu_price_variants", "pricing_status")
    op.drop_constraint("price_non_negative", "menu_price_variants", type_="check")
    op.create_check_constraint("price_non_negative", "menu_price_variants", "price >= 0")
    op.alter_column(
        "menu_price_variants",
        "price",
        existing_type=sa.Numeric(precision=10, scale=2),
        nullable=False,
    )

    op.drop_constraint("pricing_type_valid", "menu_items", type_="check")
    op.drop_column("menu_items", "pricing_type")
    op.drop_column("menu_items", "serving_description")
