"""Reporting and analytics schemas for Admin Web."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class DailySalesSummary(BaseModel):
    """Aggregate metrics for daily sales."""

    date: date
    gross_subtotal: Decimal
    total_discounts: Decimal
    cgst_amount: Decimal
    sgst_amount: Decimal
    net_collected_revenue: Decimal
    total_bills: int
    total_orders: int
    completed_sessions: int
    average_bill_value: Decimal


class OrderReportItem(BaseModel):
    """Order detail entry in order logs report."""

    order_id: uuid.UUID
    order_number: str
    table_number: int
    source: str
    status: str
    placed_at: datetime
    completed_at: datetime | None = None
    order_subtotal: Decimal
    item_count: int


class PopularDishReportItem(BaseModel):
    """Item-level sales velocity and revenue."""

    menu_item_id: uuid.UUID
    item_code: str
    item_name: str
    variant_id: uuid.UUID | None = None
    variant_name: str
    quantity_billed: int
    gross_revenue: Decimal


class RevenueTimeSeriesItem(BaseModel):
    """Time-series point for sales graphs."""

    bucket_label: str
    revenue: Decimal
    order_count: int
    bill_count: int


class PaymentMethodReportItem(BaseModel):
    """Breakdown of collections by payment method."""

    payment_method: str
    transaction_count: int
    total_amount: Decimal


class TableUsageReportItem(BaseModel):
    """Table turnover, average session duration, and revenue."""

    table_id: uuid.UUID
    table_number: int
    display_name: str
    session_count: int
    total_revenue: Decimal
    average_session_minutes: Decimal


class OrderStatusReportItem(BaseModel):
    """Live and historical counts of orders by status with kitchen turnaround SLA."""

    status: str
    count: int
    avg_duration_minutes: Decimal | None = None


class UnavailableDishReportItem(BaseModel):
    """List of currently 86'd / unavailable dishes."""

    item_id: uuid.UUID
    item_code: str
    name: str
    category_name: str
    is_available: bool
    updated_at: datetime


class CancelledRejectedReportItem(BaseModel):
    """Accountability log for rejected or cancelled orders."""

    order_id: uuid.UUID
    order_number: str
    table_number: int
    status: str
    reason: str | None = None
    actor_role: str | None = None
    occurred_at: datetime
    order_subtotal: Decimal


class WaiterActivityReportItem(BaseModel):
    """Staff performance metrics for waiters."""

    user_id: uuid.UUID
    username: str
    full_name: str
    orders_placed: int
    items_served: int
    bills_generated: int
    payments_recorded: int


class KitchenActivityReportItem(BaseModel):
    """Staff performance metrics for kitchen."""

    user_id: uuid.UUID
    username: str
    full_name: str
    orders_accepted: int
    orders_rejected: int
    orders_ready: int
    avg_prep_minutes: Decimal | None = None


class AdminDashboardKPIs(BaseModel):
    """Overview screen real-time KPIs."""

    today_revenue: Decimal
    active_occupied_tables: int
    total_tables: int
    active_orders_count: int
    orders_by_status: dict[str, int]
    unpaid_bills_count: int
    unpaid_exposure_amount: Decimal
    recent_rejections_cancellations: int
