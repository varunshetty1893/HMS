"""Canonical status/enum vocabularies (`docs/04-database-design.md`, `docs/13` Section 1.1).

Each class is the single source of truth for both the database `CHECK` constraints and
application code. Values are stored as plain `VARCHAR` + `CHECK ... IN (...)` (no native
PostgreSQL ENUM types) so adding a value never needs `ALTER TYPE`.
"""

from __future__ import annotations

from enum import Enum


class _StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


def enum_values(enum_cls: type[Enum]) -> tuple[str, ...]:
    """Return the string values of an enum in declaration order."""
    return tuple(str(member.value) for member in enum_cls)


def in_check(column: str, enum_cls: type[Enum]) -> str:
    """Render `column IN ('A','B',...)` for a `CHECK` constraint."""
    quoted = ",".join(f"'{value}'" for value in enum_values(enum_cls))
    return f"{column} IN ({quoted})"


class UserRole(_StrEnum):
    ADMIN = "ADMIN"
    WAITER = "WAITER"
    KITCHEN = "KITCHEN"


class UserStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    LOCKED = "LOCKED"


class TableOperationalStatus(_StrEnum):
    ENABLED = "ENABLED"
    MAINTENANCE = "MAINTENANCE"
    DISABLED = "DISABLED"


class QrTokenStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    DISABLED = "DISABLED"


class CustomerSessionStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    LOCKED_SUSPICIOUS = "LOCKED_SUSPICIOUS"
    EXPIRED = "EXPIRED"
    CLOSED_BY_PAYMENT = "CLOSED_BY_PAYMENT"
    REVOKED = "REVOKED"


class TableSessionStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    CLOSED_PAID = "CLOSED_PAID"
    CLOSED_CANCELLED = "CLOSED_CANCELLED"
    CLOSED_ADMIN_OVERRIDE = "CLOSED_ADMIN_OVERRIDE"


class OrderSource(_StrEnum):
    """Used by `orders.source` and `table_sessions.opened_by_source`."""

    CUSTOMER_QR = "CUSTOMER_QR"
    WAITER = "WAITER"


class DietaryType(_StrEnum):
    VEG = "VEG"
    NON_VEG = "NON_VEG"
    EGG = "EGG"


class SpiceLevel(_StrEnum):
    MILD = "MILD"
    MEDIUM = "MEDIUM"
    HOT = "HOT"


class PriceUnit(_StrEnum):
    PORTION = "PORTION"
    PIECE = "PIECE"
    ML = "ML"
    L = "L"
    GRAM = "GRAM"
    KG = "KG"
    PLATE = "PLATE"
    BOWL = "BOWL"
    GLASS = "GLASS"
    BOTTLE = "BOTTLE"


class PricingType(_StrEnum):
    FIXED = "FIXED"
    SEASONAL = "SEASONAL"


class PricingStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    SEASONAL_UNPRICED = "SEASONAL_UNPRICED"


class OrderStatus(_StrEnum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    SERVED = "SERVED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OrderItemStatus(_StrEnum):
    ACTIVE = "ACTIVE"
    MODIFIED = "MODIFIED"
    CANCELLED = "CANCELLED"


class ModificationType(_StrEnum):
    ITEM_ADDED = "ITEM_ADDED"
    QUANTITY_INCREASED = "QUANTITY_INCREASED"
    QUANTITY_DECREASED = "QUANTITY_DECREASED"
    ITEM_CANCELLED = "ITEM_CANCELLED"
    NOTES_UPDATED = "NOTES_UPDATED"


class ActorRole(_StrEnum):
    """Used by `order_status_history.changed_by_role`, `audit_logs.actor_role`, etc."""

    CUSTOMER = "CUSTOMER"
    WAITER = "WAITER"
    KITCHEN = "KITCHEN"
    ADMIN = "ADMIN"
    SYSTEM = "SYSTEM"


class BillStatus(_StrEnum):
    ISSUED = "ISSUED"
    PAID = "PAID"
    VOIDED_FOR_REVISION = "VOIDED_FOR_REVISION"


class PaymentMethod(_StrEnum):
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"
    OTHER = "OTHER"


class PaymentStatus(_StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    VOIDED = "VOIDED"


class NotificationChannel(_StrEnum):
    KITCHEN_ALL = "KITCHEN_ALL"
    WAITERS_ALL = "WAITERS_ALL"
    ADMIN_ALL = "ADMIN_ALL"
    USER_SPECIFIC = "USER_SPECIFIC"
    TABLE_SESSION = "TABLE_SESSION"


class NotificationSeverity(_StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class WaiterRequestStatus(_StrEnum):
    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class WaiterRequestReason(_StrEnum):
    ASSISTANCE = "ASSISTANCE"
    CUTLERY = "CUTLERY"
    WATER = "WATER"
    OTHER = "OTHER"
