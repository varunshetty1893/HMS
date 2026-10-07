"""SQLAlchemy 2.0 ORM models package.

Exports `Base` so Alembic autogenerate can discover metadata cleanly.
Domain models (`users`, `restaurant_tables`, `menu_items`, `orders`, `bills`, etc.)
will be registered here in Phase 2 (`docs/13-final-implementation-blueprint.md`).
"""

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
]
