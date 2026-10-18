"""Add imagekit_file_id to menu_items.

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-18 15:05:00.000000

Adds nullable imagekit_file_id column to menu_items so that the backend can
call the ImageKit Delete File API when an admin replaces or removes a dish photo.
Also migrates existing /static/menu/ URLs to /media/ so they match the Caddy
reverse-proxy route.  Rows without an image_url are unaffected.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add imagekit_file_id column (nullable — existing rows default to NULL)
    op.add_column(
        "menu_items",
        sa.Column("imagekit_file_id", sa.String(255), nullable=True),
    )

    # 2. Rewrite /static/menu/<filename> → /media/<filename> for existing rows.
    #    This makes the stored URLs consistent with the Caddy /media/* route.
    #    Rows already using /media/ or NULL are untouched.
    op.execute(
        sa.text(
            "UPDATE menu_items "
            "SET image_url = '/media/' || substring(image_url FROM 14) "
            "WHERE image_url LIKE '/static/menu/%'"
        )
    )


def downgrade() -> None:
    # Reverse URL rewrite first
    op.execute(
        sa.text(
            "UPDATE menu_items "
            "SET image_url = '/static/menu/' || substring(image_url FROM 8) "
            "WHERE image_url LIKE '/media/%'"
        )
    )

    op.drop_column("menu_items", "imagekit_file_id")
