"""SQLAlchemy 2.0 ORM models package (Phase 2 — 20 canonical tables, `docs/04`).

Importing this package registers every model on `Base.metadata`, which is what Alembic
autogenerate and the metadata tests rely on. Do not import models lazily elsewhere.
"""

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.billing import Bill, BillItem, Payment
from app.models.identity import StaffRefreshToken, User
from app.models.menu import MenuCategory, MenuItem, MenuPriceVariant
from app.models.operations import AuditLog, IdempotencyKey, Notification
from app.models.orders import Order, OrderItem, OrderModificationEvent, OrderStatusHistory
from app.models.qr_sessions import CustomerSession, TableQrToken, TableSession
from app.models.restaurant import RestaurantSettings, RestaurantTable
from app.models.waiter_requests import WaiterRequest

__all__ = [
    "AuditLog",
    "Base",
    "Bill",
    "BillItem",
    "CustomerSession",
    "IdempotencyKey",
    "MenuCategory",
    "MenuItem",
    "MenuPriceVariant",
    "Notification",
    "Order",
    "OrderItem",
    "OrderModificationEvent",
    "OrderStatusHistory",
    "Payment",
    "RestaurantSettings",
    "RestaurantTable",
    "StaffRefreshToken",
    "TableQrToken",
    "TableSession",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "User",
    "WaiterRequest",
]
