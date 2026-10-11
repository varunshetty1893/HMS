"""Restaurant configuration and policy settings schemas."""

from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import StrictRequestModel


class RestaurantSettingsResponse(BaseModel):
    """Full restaurant settings singleton returned to Admin."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    restaurant_name: str
    address: str | None = None
    phone: str | None = None
    gstin: str | None = None
    logo_url: str | None = None
    currency_code: str
    currency_symbol: str
    prices_include_tax: bool
    cgst_percentage: Decimal
    sgst_percentage: Decimal
    service_charge_percentage: Decimal
    allowed_payment_methods_json: list[Any] | None = None
    default_session_outstanding_limit: Decimal
    is_ordering_enabled: bool
    opening_time: time | None = None
    closing_time: time | None = None

    allow_multi_device_per_table: bool
    allow_customer_cancel_placed: bool
    allow_waiter_cancel_preparing_item: bool
    allow_kitchen_mark_served: bool
    kitchen_can_toggle_availability: bool
    limit_includes_estimated_tax: bool
    apply_outstanding_limit_to_waiter_orders: bool
    allow_waiter_discount: bool
    waiter_max_discount_percentage: Decimal

    created_at: datetime
    updated_at: datetime


class RestaurantSettingsUpdate(StrictRequestModel):
    """Updatable settings fields."""

    restaurant_name: str | None = Field(default=None, min_length=1, max_length=120)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    gstin: str | None = Field(default=None, max_length=15)
    logo_url: str | None = Field(default=None, max_length=500)
    prices_include_tax: bool | None = None
    cgst_percentage: Decimal | None = Field(default=None, ge=Decimal("0.00"), le=Decimal("28.00"))
    sgst_percentage: Decimal | None = Field(default=None, ge=Decimal("0.00"), le=Decimal("28.00"))
    service_charge_percentage: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), le=Decimal("20.00")
    )
    allowed_payment_methods_json: list[str] | None = None
    default_session_outstanding_limit: Decimal | None = Field(
        default=None, ge=Decimal("100.00"), le=Decimal("100000.00")
    )
    is_ordering_enabled: bool | None = None
    opening_time: time | None = None
    closing_time: time | None = None

    allow_multi_device_per_table: bool | None = None
    allow_customer_cancel_placed: bool | None = None
    allow_waiter_cancel_preparing_item: bool | None = None
    allow_kitchen_mark_served: bool | None = None
    kitchen_can_toggle_availability: bool | None = None
    limit_includes_estimated_tax: bool | None = None
    apply_outstanding_limit_to_waiter_orders: bool | None = None
    allow_waiter_discount: bool | None = None
    waiter_max_discount_percentage: Decimal | None = Field(
        default=None, ge=Decimal("0.00"), le=Decimal("100.00")
    )
