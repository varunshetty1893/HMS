"""Phase 10: Admin Reports & Business Intelligence Tests.

Covers:
1. GET /api/v1/admin/dashboard KPIs
2. GET /api/v1/admin/reports/daily-sales aggregation
3. GET /api/v1/admin/reports/popular-dishes ranking
4. GET /api/v1/admin/reports/revenue time-series
5. GET /api/v1/admin/reports/payment-methods breakdown
6. GET /api/v1/admin/reports/export.csv RFC-4180 export
7. RBAC security enforcement (non-admin receives 403 Forbidden)
"""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_staff_user
from app.main import create_app
from app.models.enums import UserRole, UserStatus
from app.models.identity import User
from app.schemas.reports import (
    AdminDashboardKPIs,
    DailySalesSummary,
    PaymentMethodReportItem,
    PaymentTransactionReportItem,
    PopularDishReportItem,
)
from app.services.report_service import ReportService


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="admin_boss",
        full_name="Admin Boss",
        password_hash="argon2id$hashed",
        role=UserRole.ADMIN.value,
        status=UserStatus.ACTIVE.value,
        is_active=True,
    )


@pytest.fixture
def waiter_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="waiter_sam",
        full_name="Waiter Sam",
        password_hash="argon2id$hashed",
        role=UserRole.WAITER.value,
        status=UserStatus.ACTIVE.value,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_admin_dashboard_kpis_success(admin_user: User) -> None:
    """Admin receives real-time overview KPIs."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    mock_kpis = AdminDashboardKPIs(
        today_revenue=Decimal("12500.00"),
        active_occupied_tables=4,
        total_tables=10,
        active_orders_count=6,
        orders_by_status={"PLACED": 2, "PREPARING": 3, "READY": 1},
        unpaid_bills_count=2,
        unpaid_exposure_amount=Decimal("1850.00"),
        recent_rejections_cancellations=1,
    )

    with patch.object(ReportService, "get_dashboard_kpis", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_kpis
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/dashboard")
            assert resp.status_code == 200
            data = resp.json()
            assert data["today_revenue"] == "12500.00"
            assert data["active_occupied_tables"] == 4
            assert data["total_tables"] == 10
            assert data["unpaid_bills_count"] == 2


@pytest.mark.asyncio
async def test_admin_reports_daily_sales_success(admin_user: User) -> None:
    """Daily sales aggregation returns formatted summaries."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    mock_daily = [
        DailySalesSummary(
            date=date(2026, 10, 10),
            gross_subtotal=Decimal("10000.00"),
            total_discounts=Decimal("500.00"),
            cgst_amount=Decimal("237.50"),
            sgst_amount=Decimal("237.50"),
            net_collected_revenue=Decimal("9975.00"),
            cash_tendered=Decimal("6000.00"),
            cash_change_returned=Decimal("125.00"),
            total_bills=15,
            total_orders=22,
            completed_sessions=14,
            average_bill_value=Decimal("665.00"),
        )
    ]

    with patch.object(ReportService, "get_daily_sales", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_daily
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(
                "/api/v1/admin/reports/daily-sales?from=2026-10-10&to=2026-10-10"
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["gross_subtotal"] == "10000.00"
            assert data[0]["net_collected_revenue"] == "9975.00"
            assert data[0]["cash_tendered"] == "6000.00"
            assert data[0]["cash_change_returned"] == "125.00"
            assert data[0]["total_bills"] == 15


@pytest.mark.asyncio
async def test_admin_reports_payment_transaction_drilldown(admin_user: User) -> None:
    """A daily report row can retrieve applied, tendered, and returned cash separately."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user
    transaction = PaymentTransactionReportItem(
        payment_id=uuid.uuid4(),
        bill_id=uuid.uuid4(),
        bill_number="INV-20261021-0002",
        table_number=1,
        table_display_name="Table 1",
        payment_method="CASH",
        amount_applied=Decimal("357.00"),
        amount_tendered=Decimal("400.00"),
        change_returned=Decimal("43.00"),
        completed_at=None,
    )
    with patch.object(
        ReportService, "get_payment_transactions", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = [transaction]
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/v1/admin/reports/payment-transactions?from=2026-10-21&to=2026-10-21"
            )
    assert response.status_code == 200
    data = response.json()
    assert data[0]["amount_applied"] == "357.00"
    assert data[0]["amount_tendered"] == "400.00"
    assert data[0]["change_returned"] == "43.00"


@pytest.mark.asyncio
async def test_admin_open_table_checks_list_unbilled_tables(admin_user: User) -> None:
    """Tables with orders but no bill appear as live checks with current prices."""
    from app.schemas.billing import TableBillResponse
    from app.services.billing_service import BillingService

    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user
    check = TableBillResponse(
        table_number=6,
        table_id=uuid.uuid4(),
        table_session_id=uuid.uuid4(),
        session_code="S-6",
        bill_status="NOT_GENERATED",
        preview_subtotal=Decimal("200.00"),
        preview_grand_total=Decimal("210.00"),
    )
    with patch.object(
        BillingService, "list_open_table_checks", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = [check]
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/admin/bills/open-tables")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["table_number"] == 6
    assert data[0]["bill_status"] == "NOT_GENERATED"
    assert data[0]["preview_grand_total"] == "210.00"


@pytest.mark.asyncio
async def test_admin_reports_popular_dishes_success(admin_user: User) -> None:
    """Popular dishes endpoint returns velocity metrics."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    mock_dishes = [
        PopularDishReportItem(
            menu_item_id=uuid.uuid4(),
            item_code="CB",
            item_name="Chicken Biryani",
            variant_name="Full",
            quantity_billed=42,
            gross_revenue=Decimal("7560.00"),
        )
    ]

    with patch.object(ReportService, "get_popular_dishes", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_dishes
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/reports/popular-dishes?limit=10")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 1
            assert data[0]["item_code"] == "CB"
            assert data[0]["quantity_billed"] == 42


@pytest.mark.asyncio
async def test_admin_reports_payment_methods_success(admin_user: User) -> None:
    """Payment methods breakdown endpoint returns counts and totals."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    mock_payments = [
        PaymentMethodReportItem(
            payment_method="UPI",
            transaction_count=25,
            total_amount=Decimal("15200.00"),
        ),
        PaymentMethodReportItem(
            payment_method="CASH",
            transaction_count=10,
            total_amount=Decimal("4800.00"),
        ),
    ]

    with patch.object(ReportService, "get_payment_methods", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_payments
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/reports/payment-methods")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2
            assert data[0]["payment_method"] == "UPI"
            assert data[0]["total_amount"] == "15200.00"


@pytest.mark.asyncio
async def test_admin_reports_csv_export_success(admin_user: User) -> None:
    """CSV export returns proper Content-Type and headers."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    sample_csv = "Bill Number,Status,Grand Total\nINV-001,PAID,500.00\n"

    with patch.object(ReportService, "generate_sales_csv", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = sample_csv
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/admin/reports/export.csv")
            assert resp.status_code == 200
            assert "text/csv" in resp.headers["content-type"]
            assert "attachment; filename=" in resp.headers["content-disposition"]
            assert "INV-001" in resp.text


@pytest.mark.asyncio
async def test_admin_reports_forbidden_for_waiter(waiter_user: User) -> None:
    """Waiter role receives 403 Forbidden when calling Admin report endpoints."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: waiter_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/admin/dashboard")
        assert resp.status_code == 403
        data = resp.json()
        assert data["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

        resp2 = await client.get("/api/v1/admin/reports/daily-sales")
        assert resp2.status_code == 403
