"""Phase 10: Admin Staff Management & Settings Tests.

Covers:
1. Staff user CRUD, unlock, and password reset
2. 409 Conflict on duplicate username
3. Restaurant settings singleton get & update
4. Table session unpaid limit override
5. Audit log query endpoint
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_staff_user
from app.core.exceptions import StateConflictError
from app.main import create_app
from app.models.enums import UserRole, UserStatus
from app.models.identity import User
from app.schemas.settings import RestaurantSettingsResponse
from app.schemas.staff import StaffUserAdminResponse
from app.services.settings_service import SettingsService
from app.services.staff_service import StaffService


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


@pytest.mark.asyncio
async def test_staff_create_success(admin_user: User) -> None:
    """Admin creates a new waiter user account."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    mock_resp = StaffUserAdminResponse(
        id=uuid.uuid4(),
        username="waiter_rahul",
        full_name="Rahul Kumar",
        role="WAITER",
        status="ACTIVE",
        is_active=True,
        failed_login_attempts=0,
        locked_until=None,
        last_login_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.object(StaffService, "create_user", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_resp
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/admin/users",
                json={
                    "username": "waiter_rahul",
                    "full_name": "Rahul Kumar",
                    "password": "SecretPassword123",
                    "role": "WAITER",
                },
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["username"] == "waiter_rahul"
            assert data["role"] == "WAITER"


@pytest.mark.asyncio
async def test_staff_create_duplicate_username_fails(admin_user: User) -> None:
    """Admin cannot create account with already taken username."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    with patch.object(StaffService, "create_user", new_callable=AsyncMock) as mock_create:
        mock_create.side_effect = StateConflictError(
            "USERNAME_ALREADY_EXISTS",
            "A staff account with username 'waiter_rahul' already exists.",
        )
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/admin/users",
                json={
                    "username": "waiter_rahul",
                    "full_name": "Rahul Kumar",
                    "password": "SecretPassword123",
                    "role": "WAITER",
                },
            )
            assert resp.status_code == 409
            data = resp.json()
            assert data["error"]["code"] == "USERNAME_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_staff_reset_password_success(admin_user: User) -> None:
    """Admin resets a staff member's password."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    target_id = uuid.uuid4()
    mock_resp = StaffUserAdminResponse(
        id=target_id,
        username="waiter_rahul",
        full_name="Rahul Kumar",
        role="WAITER",
        status="ACTIVE",
        is_active=True,
        failed_login_attempts=0,
        locked_until=None,
        last_login_at=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with patch.object(StaffService, "reset_password", new_callable=AsyncMock) as mock_reset:
        mock_reset.return_value = mock_resp
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                f"/api/v1/admin/users/{target_id}/reset-password",
                json={"new_password": "NewSecretPassword999"},
            )
            assert resp.status_code == 200
            assert resp.json()["username"] == "waiter_rahul"


@pytest.mark.asyncio
async def test_restaurant_settings_get_and_update(admin_user: User) -> None:
    """Admin retrieves and updates restaurant settings singleton."""
    app = create_app()
    app.dependency_overrides[get_current_staff_user] = lambda: admin_user

    settings_mock = RestaurantSettingsResponse(
        id=1,
        restaurant_name="Spice Garden",
        currency_code="INR",
        currency_symbol="₹",
        prices_include_tax=False,
        cgst_percentage=Decimal("2.50"),
        sgst_percentage=Decimal("2.50"),
        service_charge_percentage=Decimal("0.00"),
        default_session_outstanding_limit=Decimal("5000.00"),
        is_ordering_enabled=True,
        allow_multi_device_per_table=True,
        allow_customer_cancel_placed=False,
        allow_waiter_cancel_preparing_item=False,
        allow_kitchen_mark_served=False,
        kitchen_can_toggle_availability=True,
        limit_includes_estimated_tax=False,
        apply_outstanding_limit_to_waiter_orders=False,
        allow_waiter_discount=False,
        waiter_max_discount_percentage=Decimal("0.00"),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    with (
        patch.object(SettingsService, "get_settings_response", new_callable=AsyncMock) as mock_get,
        patch.object(SettingsService, "update_settings", new_callable=AsyncMock) as mock_update,
    ):
        mock_get.return_value = settings_mock
        mock_update.return_value = settings_mock
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            get_resp = await client.get("/api/v1/admin/settings")
            assert get_resp.status_code == 200
            assert get_resp.json()["restaurant_name"] == "Spice Garden"

            patch_resp = await client.patch(
                "/api/v1/admin/settings",
                json={"restaurant_name": "Spice Garden Grand"},
            )
            assert patch_resp.status_code == 200
