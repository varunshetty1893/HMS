"""Menu catalog: `menu_categories`, `menu_items`, `menu_price_variants` (`docs/04` Sections 8-10).

`menu_items` has no price column; every dish owns >= 1 `menu_price_variants` row. Variant
prices are mutable and affect future orders only; `order_items` snapshots history.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Index, Integer, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import (
    Base,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    money,
    percentage,
    uuid_fk,
)
from app.models.enums import DietaryType, PriceUnit, SpiceLevel, in_check

if TYPE_CHECKING:
    from app.models.orders import OrderItem


class MenuCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "menu_categories"
    __table_args__ = (
        Index("uq_menu_categories_name_lower", text("lower(name)"), unique=True),
        Index("ix_menu_categories_is_active_display_order", "is_active", "display_order"),
        CheckConstraint("display_order >= 0", name="display_order_non_negative"),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    items: Mapped[list[MenuItem]] = relationship(back_populates="category")


class MenuItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "menu_items"
    __table_args__ = (
        Index("uq_menu_items_item_code_upper", text("upper(item_code)"), unique=True),
        Index(
            "ix_menu_items_name_trgm",
            text("lower(name) gin_trgm_ops"),
            postgresql_using="gin",
        ),
        Index(
            "ix_menu_items_category_active_available_order",
            "category_id",
            "is_active",
            "is_available",
            "display_order",
        ),
        CheckConstraint(
            "dietary_type IS NULL OR " + in_check("dietary_type", DietaryType),
            name="dietary_type_valid",
        ),
        CheckConstraint(
            "spice_level IS NULL OR " + in_check("spice_level", SpiceLevel),
            name="spice_level_valid",
        ),
        CheckConstraint("btrim(item_code) <> ''", name="item_code_not_blank"),
    )

    category_id: Mapped[uuid.UUID] = uuid_fk("menu_categories.id", nullable=False)
    item_code: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dietary_type: Mapped[str | None] = mapped_column(String(15), nullable=True)
    spice_level: Mapped[str | None] = mapped_column(String(15), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tax_rate_override: Mapped[Decimal | None] = mapped_column(percentage(), nullable=True)
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    category: Mapped[MenuCategory] = relationship(back_populates="items")
    variants: Mapped[list[MenuPriceVariant]] = relationship(back_populates="item")
    order_items: Mapped[list[OrderItem]] = relationship(back_populates="menu_item")


class MenuPriceVariant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "menu_price_variants"
    __table_args__ = (
        Index(
            "uq_menu_price_variants_variant_code_upper",
            text("upper(variant_code)"),
            unique=True,
            postgresql_where=text("variant_code IS NOT NULL"),
        ),
        Index(
            "uq_menu_price_variants_item_variant_name_lower",
            "menu_item_id",
            text("lower(variant_name)"),
            unique=True,
        ),
        Index(
            "ix_menu_price_variants_item_active_available_order",
            "menu_item_id",
            "is_active",
            "is_available",
            "display_order",
        ),
        CheckConstraint("price >= 0", name="price_non_negative"),
        CheckConstraint("quantity_value > 0", name="quantity_value_positive"),
        CheckConstraint(in_check("unit", PriceUnit), name="unit_valid"),
    )

    menu_item_id: Mapped[uuid.UUID] = uuid_fk("menu_items.id", nullable=False)
    variant_code: Mapped[str | None] = mapped_column(String(24), nullable=True)
    variant_name: Mapped[str] = mapped_column(String(80), nullable=False)
    quantity_value: Mapped[Decimal] = mapped_column(Numeric(8, 2, asdecimal=True), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    price: Mapped[Decimal] = mapped_column(money(), nullable=False)
    is_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_available: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    display_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    item: Mapped[MenuItem] = relationship(back_populates="variants")
    order_items: Mapped[list[OrderItem]] = relationship(back_populates="variant")
