"""Menu schemas for categories, items, variants, customer catalog, and waiter search.

Follows `docs/05-api-specification.md` (Sections 6, 9.4, 12) and `docs/04-database-design.md`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import DietaryType, PriceUnit, PricingStatus, PricingType, SpiceLevel
from app.schemas.common import StrictRequestModel

# =============================================================================
# Price Variant Schemas
# =============================================================================


class MenuPriceVariantCreate(StrictRequestModel):
    """Schema for adding a price variant to a dish."""

    id: uuid.UUID | None = Field(
        default=None,
        description="Optional ID when updating an existing variant during full dish save",
    )
    variant_code: str | None = Field(
        default=None,
        min_length=1,
        max_length=24,
        description="Globally unique short code (e.g., CB-H, CB-F, CK-2)",
    )
    variant_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
        description="Required only when is_portion is true (e.g., Half, Full, 2 Pcs)",
    )
    is_portion: bool = Field(default=False)
    quantity_value: Decimal = Field(
        default=Decimal("1"),
        gt=0,
        description="Quantity value (e.g., 0.50, 1.00, 6, 12). Defaults to 1.",
    )
    unit: PriceUnit = Field(
        default=PriceUnit.PORTION,
        description="Measurement unit: PORTION, PIECE, ML, L, GRAM, KG, PLATE, BOWL",
    )
    price: Decimal | None = Field(
        default=None,
        ge=0,
        description="Base unit price in currency. Nullable when pricing_status is SEASONAL_UNPRICED.",
    )
    pricing_status: PricingStatus = Field(default=PricingStatus.ACTIVE)
    is_default: bool = Field(default=False)
    is_available: bool = Field(default=True)
    is_active: bool = Field(default=True)
    display_order: int = Field(default=0, ge=0)

    @field_validator("variant_code")
    @classmethod
    def clean_variant_code(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip().upper()
            return cleaned if cleaned else None
        return None

    @field_validator("variant_name")
    @classmethod
    def clean_variant_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned or None

    @model_validator(mode="after")
    def require_name_for_portion(self) -> MenuPriceVariantCreate:
        if self.is_portion and not self.variant_name:
            raise ValueError("variant_name is required when is_portion is true.")
        return self


class MenuPriceVariantUpdate(StrictRequestModel):
    """Schema for updating an existing price variant."""

    variant_code: str | None = Field(default=None, min_length=1, max_length=24)
    variant_name: str | None = Field(default=None, min_length=1, max_length=80)
    is_portion: bool | None = None
    quantity_value: Decimal | None = Field(default=None, gt=0)
    unit: PriceUnit | None = None
    price: Decimal | None = Field(default=None, ge=0)
    pricing_status: PricingStatus | None = None
    is_default: bool | None = None
    is_available: bool | None = None
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0)

    @field_validator("variant_code")
    @classmethod
    def clean_variant_code(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip().upper()
            return cleaned if cleaned else None
        return None


class MenuPriceVariantResponse(BaseModel):
    """Admin/Staff view of a price variant."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    menu_item_id: uuid.UUID
    variant_code: str | None
    variant_name: str
    is_portion: bool
    quantity_value: Decimal
    unit: str
    price: Decimal | None
    pricing_status: str = PricingStatus.ACTIVE.value
    is_default: bool
    is_available: bool
    is_active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime

    @field_validator("pricing_status", mode="before")
    @classmethod
    def coerce_pricing_status(cls, v: Any) -> str:
        if not v:
            return PricingStatus.ACTIVE.value
        return v.value if hasattr(v, "value") else str(v)


# =============================================================================
# Category Schemas
# =============================================================================


class MenuCategoryCreate(StrictRequestModel):
    """Schema for creating a menu category."""

    name: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    display_order: int = Field(default=0, ge=0)
    is_active: bool = Field(default=True)


class MenuCategoryUpdate(StrictRequestModel):
    """Schema for updating a menu category."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    display_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CategoryReorderItem(StrictRequestModel):
    """Item for batch reordering categories."""

    id: uuid.UUID
    display_order: int = Field(ge=0)


class CategoryReorderRequest(StrictRequestModel):
    """Batch reorder request for categories."""

    categories: list[CategoryReorderItem] = Field(min_length=1)


class ItemReorderItem(StrictRequestModel):
    """Item for batch reordering dishes within a category."""

    id: uuid.UUID
    display_order: int = Field(ge=0)


class ItemReorderRequest(StrictRequestModel):
    """Batch reorder request for dishes."""

    items: list[ItemReorderItem] = Field(min_length=1)


class MenuCategoryResponse(BaseModel):
    """Schema for menu category representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    display_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    item_count: int | None = None


# =============================================================================
# Menu Item Schemas
# =============================================================================


class MenuItemCreate(StrictRequestModel):
    """Schema for creating a menu item with initial price variants."""

    category_id: uuid.UUID
    item_code: str = Field(
        min_length=1,
        max_length=16,
        description="Globally unique dish short code (e.g., CB, VB, CK)",
    )
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None
    serving_description: str | None = Field(default=None, max_length=255)
    dietary_type: DietaryType | None = None
    spice_level: SpiceLevel | None = None
    pricing_type: PricingType = Field(default=PricingType.FIXED)
    image_url: str | None = Field(default=None, max_length=500)
    tax_rate_override: Decimal | None = Field(default=None, ge=0)
    is_available: bool = Field(default=True)
    display_order: int = Field(default=0, ge=0)
    variants: list[MenuPriceVariantCreate] = Field(
        min_length=1,
        description="At least one price variant required upon item creation",
    )

    @field_validator("item_code")
    @classmethod
    def clean_item_code(cls, v: str) -> str:
        cleaned = v.strip().upper()
        if not cleaned:
            raise ValueError("item_code cannot be empty or whitespace.")
        return cleaned


class MenuItemUpdate(StrictRequestModel):
    """Schema for updating a menu item."""

    category_id: uuid.UUID | None = None
    item_code: str | None = Field(default=None, min_length=1, max_length=16)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    serving_description: str | None = Field(default=None, max_length=255)
    dietary_type: DietaryType | None = None
    spice_level: SpiceLevel | None = None
    pricing_type: PricingType | None = None
    tax_rate_override: Decimal | None = Field(default=None, ge=0)
    is_available: bool | None = None
    is_active: bool | None = None
    display_order: int | None = Field(default=None, ge=0)
    variants: list[MenuPriceVariantCreate] | None = Field(
        default=None,
        description="When provided, replaces or synchronizes all dish variants atomically",
    )

    @field_validator("item_code")
    @classmethod
    def clean_item_code(cls, v: str | None) -> str | None:
        if v is not None:
            cleaned = v.strip().upper()
            return cleaned if cleaned else None
        return None


class MenuItemAvailabilityUpdate(StrictRequestModel):
    """Instant stock availability toggle schema (Admin / Kitchen)."""

    is_available: bool
    reason: str | None = Field(default=None, max_length=255)


class MenuItemResponse(BaseModel):
    """Admin / Staff view of a menu item."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    item_code: str
    name: str
    description: str | None
    serving_description: str | None = None
    dietary_type: str | None
    spice_level: str | None
    pricing_type: str = PricingType.FIXED.value
    image_url: str | None
    tax_rate_override: Decimal | None
    is_available: bool
    is_active: bool
    display_order: int
    created_at: datetime
    updated_at: datetime
    variants: list[MenuPriceVariantResponse] = Field(default_factory=list)

    @field_validator("pricing_type", mode="before")
    @classmethod
    def coerce_pricing_type(cls, v: Any) -> str:
        if not v:
            return PricingType.FIXED.value
        return v.value if hasattr(v, "value") else str(v)


# =============================================================================
# Customer Menu Schemas
# =============================================================================


class CustomerMenuVariant(BaseModel):
    """Portion variant representation for Customer Web."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    variant_code: str | None
    variant_name: str
    is_portion: bool
    quantity_value: Decimal
    unit: str
    price: Decimal | None
    pricing_status: str = PricingStatus.ACTIVE.value
    is_default: bool
    is_available: bool

    @field_validator("pricing_status", mode="before")
    @classmethod
    def coerce_pricing_status(cls, v: Any) -> str:
        if not v:
            return PricingStatus.ACTIVE.value
        return v.value if hasattr(v, "value") else str(v)


class CustomerMenuItem(BaseModel):
    """Dish representation for Customer Web."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_code: str
    name: str
    description: str | None
    serving_description: str | None = None
    dietary_type: str | None
    spice_level: str | None
    pricing_type: str = PricingType.FIXED.value
    image_url: str | None
    is_available: bool
    variants: list[CustomerMenuVariant]

    @field_validator("pricing_type", mode="before")
    @classmethod
    def coerce_pricing_type(cls, v: Any) -> str:
        if not v:
            return PricingType.FIXED.value
        return v.value if hasattr(v, "value") else str(v)


class CustomerMenuCategory(BaseModel):
    """Category group representation for Customer Web."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    display_order: int
    items: list[CustomerMenuItem]


class CustomerMenuResponse(BaseModel):
    """Full customer-facing menu catalog response (`GET /api/v1/customer/menu`)."""

    currency_symbol: str = "₹"
    prices_include_tax: bool = False
    cgst_percentage: Decimal = Decimal("2.50")
    sgst_percentage: Decimal = Decimal("2.50")
    categories: list[CustomerMenuCategory]
    popular_item_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="Most-ordered available dishes (last 30 days), best first, max 6.",
    )


class CustomerCategorySummary(BaseModel):
    """Category tab navigation item (`GET /api/v1/customer/menu/categories`)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    display_order: int
    item_count: int = 0


# =============================================================================
# Waiter Search Schemas
# =============================================================================


class WaiterSearchVariant(BaseModel):
    """Variant detail in waiter search results."""

    model_config = ConfigDict(from_attributes=True)

    variant_id: uuid.UUID
    variant_code: str | None
    variant_name: str
    is_portion: bool
    quantity_value: Decimal
    unit: str
    price: Decimal | None
    pricing_status: str = PricingStatus.ACTIVE.value
    is_available: bool

    @field_validator("pricing_status", mode="before")
    @classmethod
    def coerce_pricing_status(cls, v: Any) -> str:
        if not v:
            return PricingStatus.ACTIVE.value
        return v.value if hasattr(v, "value") else str(v)


class WaiterSearchResultItem(BaseModel):
    """Ranked item in waiter dual short-code / full-name search."""

    item_id: uuid.UUID
    item_code: str
    name: str
    category_name: str
    is_available: bool
    match_type: Literal["EXACT_VARIANT_CODE", "EXACT_ITEM_CODE", "PREFIX_CODE", "NAME_MATCH"]
    matched_variant_id: uuid.UUID | None = None
    variants: list[WaiterSearchVariant]


class WaiterSearchResponse(BaseModel):
    """Response for `GET /api/v1/waiter/menu/search`."""

    query: str
    results: list[WaiterSearchResultItem]
