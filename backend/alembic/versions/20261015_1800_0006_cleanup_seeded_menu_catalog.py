"""Correct legacy seeded menu labels, categories, and illustration URLs.

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The generated category artwork was never a genuine menu photograph.
    op.execute("UPDATE menu_items SET image_url = NULL WHERE image_url LIKE '/menu/%'")

    # A single price is an internal Standard variant, never a customer-facing
    # Full portion. Order/bill snapshots remain untouched in their own tables.
    op.execute(
        """
        UPDATE menu_price_variants AS variant
        SET is_portion = false
        WHERE variant.menu_item_id IN (
            SELECT menu_item_id
            FROM menu_price_variants
            WHERE is_active = true
            GROUP BY menu_item_id
            HAVING count(*) = 1
        )
        """
    )

    # The source menu explicitly sells Tandoori Chicken as "Half"; it is not a
    # generated Half/Full choice. Retire the synthetic half-price row and keep
    # the listed price as one fixed item.
    op.execute(
        """
        UPDATE menu_price_variants
        SET is_active = false, is_available = false
        WHERE variant_code = 'M035-H'
        """
    )
    op.execute(
        """
        UPDATE menu_price_variants
        SET variant_name = 'Standard', is_portion = false
        WHERE variant_code = 'M035-F'
        """
    )
    op.execute(
        """
        UPDATE menu_price_variants AS variant
        SET variant_name = 'Standard'
        WHERE variant.is_portion = false
          AND variant.variant_name <> 'Standard'
          AND NOT EXISTS (
            SELECT 1 FROM menu_price_variants AS other
            WHERE other.menu_item_id = variant.menu_item_id
              AND other.variant_name = 'Standard'
              AND other.id <> variant.id
          )
        """
    )

    # Pulao is intentionally grouped with breakfast/quick meals for this menu.
    op.execute(
        """
        UPDATE menu_items
        SET category_id = breakfast.id
        FROM menu_categories AS breakfast
        WHERE breakfast.name = 'Breakfast & Quick Meals'
          AND menu_items.item_code IN ('M071', 'M072', 'M073')
        """
    )

    # Keep one Biryani category; an old empty Biriyani tab must not surface.
    op.execute(
        """
        UPDATE menu_categories
        SET name = 'Biryani'
        WHERE name = 'Biryani & Pulao'
          AND NOT EXISTS (SELECT 1 FROM menu_categories WHERE name = 'Biryani')
        """
    )
    op.execute(
        """
        UPDATE menu_items
        SET category_id = biryani.id
        FROM menu_categories AS biryani
        JOIN menu_categories AS legacy ON legacy.name = 'Biryani & Pulao'
        WHERE biryani.name = 'Biryani'
          AND menu_items.category_id = legacy.id
        """
    )
    op.execute(
        """
        UPDATE menu_categories AS category
        SET is_active = false
        WHERE lower(category.name) IN (
            'biriyani', 'biryani & pulao', 'starters & appetizers',
            'breads & accompaniments', 'beverages & desserts'
        )
          AND NOT EXISTS (
            SELECT 1 FROM menu_items AS item
            WHERE item.category_id = category.id AND item.is_active = true
          )
        """
    )


def downgrade() -> None:
    # Deliberately non-destructive: this migration corrects catalog presentation
    # data but never changes historical order or bill snapshots.
    pass
