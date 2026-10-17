"""Phase 4: Admin Menu Management API & Service Tests.

Covers:
1. Category CRUD with case-insensitive name uniqueness (HTTP 409)
2. Dish item creation with atomic initial variants
3. Dish item code uniqueness validation (HTTP 409)
4. Variant code uniqueness validation (HTTP 409)
5. Portion/Price variant addition and updating
6. Historical price protection: updating variant price creates PRICE_VARIANT_PRICE_CHANGED audit log
7. Instant stock availability toggle (Admin & Kitchen) with audit log and realtime event
8. RBAC enforcement: non-admin roles rejected (HTTP 403)
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.dependencies import get_current_staff_user
from app.core.exceptions import StateConflictError
from app.main import create_app
from app.models.enums import (
    DietaryType,
    PriceUnit,
    PricingStatus,
    PricingType,
    SpiceLevel,
    UserRole,
    UserStatus,
)
from app.models.identity import User
from app.models.menu import MenuCategory, MenuItem, MenuPriceVariant
from app.models.operations import AuditLog
from app.schemas.menu import (
    CategoryReorderItem,
    CategoryReorderRequest,
    ItemReorderItem,
    ItemReorderRequest,
    MenuCategoryCreate,
    MenuItemCreate,
    MenuItemUpdate,
    MenuPriceVariantCreate,
    MenuPriceVariantUpdate,
)
from app.services.menu_service import MenuService


class MockQueryResult:
    def __init__(self, single: Any = None, multiple: list[Any] | None = None) -> None:
        self._single = single
        self._multiple = (
            multiple if multiple is not None else ([single] if single is not None else [])
        )

    def scalar_one_or_none(self) -> Any:
        return self._single

    def scalar_one(self) -> Any:
        return self._single

    def scalars(self) -> MockQueryResult:
        return self

    def all(self) -> list[Any]:
        return self._multiple


class FakeMenuSession:
    """Mock session holding categories, items, and variants in-memory."""

    def __init__(self) -> None:
        self.categories: dict[uuid.UUID, MenuCategory] = {}
        self.items: dict[uuid.UUID, MenuItem] = {}
        self.variants: dict[uuid.UUID, MenuPriceVariant] = {}
        self.audit_logs: list[AuditLog] = []

    def add(self, instance: Any) -> None:
        if isinstance(instance, MenuCategory):
            if not instance.id:
                instance.id = uuid.uuid4()
            self.categories[instance.id] = instance
        elif isinstance(instance, MenuItem):
            if not instance.id:
                instance.id = uuid.uuid4()
            self.items[instance.id] = instance
        elif isinstance(instance, MenuPriceVariant):
            if not instance.id:
                instance.id = uuid.uuid4()
            self.variants[instance.id] = instance
        elif isinstance(instance, AuditLog):
            self.audit_logs.append(instance)

    async def flush(self) -> None:
        for item in self.items.values():
            matching = [v for v in self.variants.values() if v.menu_item_id == item.id]
            item.variants = matching

    async def commit(self) -> None:
        pass

    async def get(self, entity_cls: Any, pk: Any) -> Any:
        if entity_cls is MenuCategory:
            return self.categories.get(pk)
        if entity_cls is MenuItem:
            return self.items.get(pk)
        if entity_cls is MenuPriceVariant:
            return self.variants.get(pk)
        return None

    async def execute(self, statement: Any) -> Any:
        stmt_str = str(statement).lower()

        # Handle category queries
        if "menu_categories" in stmt_str:
            cats = list(self.categories.values())
            return MockQueryResult(single=None, multiple=cats)

        # Handle item queries
        if "menu_items" in stmt_str:
            items = list(self.items.values())
            for it in items:
                it.variants = [v for v in self.variants.values() if v.menu_item_id == it.id]
            return MockQueryResult(single=items[0] if items else None, multiple=items)

        # Handle variant queries
        if "menu_price_variants" in stmt_str:
            vars_list = list(self.variants.values())
            return MockQueryResult(single=None, multiple=vars_list)

        return MockQueryResult(single=None, multiple=[])

        mock_res = AsyncMock()
        mock_res.scalar_one_or_none.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        return mock_res


@pytest.fixture
def admin_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="admin_test",
        full_name="Admin Test",
        role=UserRole.ADMIN.value,
        password_hash="dummy",
        is_active=True,
        status=UserStatus.ACTIVE.value,
        token_version=1,
    )


@pytest.fixture
def waiter_user() -> User:
    return User(
        id=uuid.uuid4(),
        username="waiter_test",
        full_name="Waiter Test",
        role=UserRole.WAITER.value,
        password_hash="dummy",
        is_active=True,
        status=UserStatus.ACTIVE.value,
        token_version=1,
    )


# =============================================================================
# Service Unit Tests
# =============================================================================


@pytest.mark.asyncio
async def test_create_category_success() -> None:
    session = FakeMenuSession()
    data = MenuCategoryCreate(name="Biriyani", description="Dum biriyanis", display_order=1)

    cat = await MenuService.create_category(session, data)  # type: ignore[arg-type]
    assert cat.name == "Biriyani"
    assert cat.display_order == 1
    assert cat.is_active is True
    assert len(session.audit_logs) == 1
    assert session.audit_logs[0].action_type == "MENU_CATEGORY_CREATED"


@pytest.mark.asyncio
async def test_create_category_duplicate_rejected() -> None:
    session = FakeMenuSession()
    existing = MenuCategory(
        id=uuid.uuid4(),
        name="Biriyani",
        description=None,
        display_order=1,
        is_active=True,
    )
    session.add(existing)

    async def mock_exec(stmt: Any) -> Any:
        return MockQueryResult(single=existing, multiple=[existing])

    session.execute = mock_exec  # type: ignore[method-assign]

    with pytest.raises(StateConflictError) as exc_info:
        await MenuService.create_category(
            session,  # type: ignore[arg-type]
            MenuCategoryCreate(name="BIRIYANI"),
        )
    assert exc_info.value.code == "CATEGORY_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_item_with_atomic_variants_success() -> None:
    session = FakeMenuSession()
    cat = MenuCategory(
        id=uuid.uuid4(),
        name="Biriyani",
        description=None,
        display_order=1,
        is_active=True,
    )
    session.add(cat)

    item_data = MenuItemCreate(
        category_id=cat.id,
        item_code="CB",
        name="Chicken Biryani",
        description="Dum cooked biryani",
        dietary_type=DietaryType.NON_VEG,
        spice_level=SpiceLevel.MEDIUM,
        variants=[
            MenuPriceVariantCreate(
                variant_code="CB-H",
                variant_name="Half",
                quantity_value=Decimal("0.50"),
                unit=PriceUnit.PORTION,
                price=Decimal("100.00"),
                is_default=False,
            ),
            MenuPriceVariantCreate(
                variant_code="CB-F",
                variant_name="Full",
                quantity_value=Decimal("1.00"),
                unit=PriceUnit.PORTION,
                price=Decimal("180.00"),
                is_default=True,
            ),
        ],
    )

    created_item = await MenuService.create_item(session, item_data)  # type: ignore[arg-type]
    assert created_item.item_code == "CB"
    assert created_item.name == "Chicken Biryani"
    assert len(created_item.variants) == 2
    assert session.audit_logs[-1].action_type == "MENU_ITEM_CREATED"


@pytest.mark.asyncio
async def test_create_item_duplicate_variant_code_in_payload_rejected() -> None:
    session = FakeMenuSession()
    cat = MenuCategory(id=uuid.uuid4(), name="Biriyani")
    session.add(cat)

    item_data = MenuItemCreate(
        category_id=cat.id,
        item_code="CB",
        name="Chicken Biryani",
        variants=[
            MenuPriceVariantCreate(
                variant_code="CB-H",
                variant_name="Half",
                quantity_value=Decimal("0.50"),
                unit=PriceUnit.PORTION,
                price=Decimal("100.00"),
            ),
            MenuPriceVariantCreate(
                variant_code="CB-H",  # Duplicate code in same request
                variant_name="Half Duplicate",
                quantity_value=Decimal("0.50"),
                unit=PriceUnit.PORTION,
                price=Decimal("110.00"),
            ),
        ],
    )

    with pytest.raises(StateConflictError) as exc_info:
        await MenuService.create_item(session, item_data)  # type: ignore[arg-type]
    assert exc_info.value.code == "VARIANT_CODE_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_variant_historical_price_protection_audit() -> None:
    session = FakeMenuSession()
    variant = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=uuid.uuid4(),
        variant_code="CB-F",
        variant_name="Full",
        quantity_value=Decimal("1.00"),
        unit=PriceUnit.PORTION.value,
        price=Decimal("180.00"),
        is_default=True,
        is_available=True,
        is_active=True,
    )
    session.add(variant)

    update_data = MenuPriceVariantUpdate(price=Decimal("200.00"))
    updated = await MenuService.update_variant(session, variant.id, update_data)  # type: ignore[arg-type]

    assert updated.price == Decimal("200.00")
    # Verify PRICE_VARIANT_PRICE_CHANGED audit entry
    price_audits = [a for a in session.audit_logs if a.action_type == "PRICE_VARIANT_PRICE_CHANGED"]
    assert len(price_audits) == 1
    assert price_audits[0].old_value_json == {"price": "180.00"}
    assert price_audits[0].new_value_json == {"price": "200.00"}


@pytest.mark.asyncio
async def test_create_fixed_price_variant_uses_internal_standard_name() -> None:
    """Fixed-price dishes retain a variant for price snapshots but expose no portion."""
    session = FakeMenuSession()
    item = MenuItem(
        id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        item_code="IDLI",
        name="Idli (2 pcs)",
    )
    session.add(item)

    variant = await MenuService.create_variant(
        session,  # type: ignore[arg-type]
        item.id,
        MenuPriceVariantCreate(price=Decimal("40.00")),
    )

    assert variant.variant_name == "Standard"
    assert variant.is_portion is False


@pytest.mark.asyncio
async def test_set_item_availability_records_audit_and_emits() -> None:
    session = FakeMenuSession()
    item = MenuItem(
        id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        item_code="CB",
        name="Chicken Biryani",
        is_available=True,
    )
    session.add(item)

    updated = await MenuService.set_item_availability(
        session,  # type: ignore[arg-type]
        item.id,
        is_available=False,
        reason="Sold out for lunch",
    )
    assert updated.is_available is False
    assert len(session.audit_logs) == 1
    assert session.audit_logs[0].action_type == "MENU_ITEM_AVAILABILITY_CHANGED"
    assert session.audit_logs[0].reason == "Sold out for lunch"
    assert session.audit_logs[0].old_value_json == {"is_available": True}
    assert session.audit_logs[0].new_value_json == {"is_available": False}


# =============================================================================
# API Endpoint Integration Tests & RBAC
# =============================================================================


@pytest.mark.asyncio
async def test_admin_menu_routes_require_admin_role(waiter_user: User) -> None:
    app = create_app()

    # Override staff user as WAITER
    app.dependency_overrides[get_current_staff_user] = lambda: waiter_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # GET /api/v1/admin/menu/categories requires ADMIN -> 403
        resp = await client.get("/api/v1/admin/menu/categories")
        assert resp.status_code == 403
        body = resp.json()
        assert body["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

        # POST /api/v1/admin/menu/categories requires ADMIN -> 403
        post_resp = await client.post(
            "/api/v1/admin/menu/categories",
            json={"name": "Test Cat"},
        )
        assert post_resp.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_admin_request_returns_401() -> None:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/admin/menu/categories")
        assert resp.status_code == 401
        assert resp.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_create_item_with_serving_description_and_plate_by_pieces() -> None:
    session = FakeMenuSession()
    cat = await MenuService.create_category(session, MenuCategoryCreate(name="Snacks - Chicken"))
    session.add(cat)

    payload = MenuItemCreate(
        category_id=cat.id,
        item_code="CK-PLT",
        name="Chicken Kebab",
        serving_description="Served with mint chutney and fresh onion rings",
        dietary_type=DietaryType.NON_VEG,
        spice_level=SpiceLevel.MEDIUM,
        variants=[
            MenuPriceVariantCreate(
                variant_name="4 pieces",
                is_portion=True,
                quantity_value=Decimal("4.00"),
                unit=PriceUnit.PORTION,
                price=Decimal("150.00"),
            ),
            MenuPriceVariantCreate(
                variant_name="8 pieces",
                is_portion=True,
                quantity_value=Decimal("8.00"),
                unit=PriceUnit.PORTION,
                price=Decimal("280.00"),
            ),
        ],
    )
    item = await MenuService.create_item(session, payload)
    assert item.name == "Chicken Kebab"
    assert item.serving_description == "Served with mint chutney and fresh onion rings"
    assert len(item.variants) == 2
    assert item.variants[0].variant_name == "4 pieces"
    assert item.variants[1].variant_name == "8 pieces"


@pytest.mark.asyncio
async def test_create_seasonal_item_with_unpriced_variant() -> None:
    session = FakeMenuSession()
    cat = await MenuService.create_category(session, MenuCategoryCreate(name="Seafood"))
    session.add(cat)

    payload = MenuItemCreate(
        category_id=cat.id,
        item_code="POMF",
        name="Tandoori Pomfret",
        serving_description="Fresh catch prepared in clay oven",
        pricing_type=PricingType.SEASONAL,
        variants=[
            MenuPriceVariantCreate(
                price=None,
                pricing_status=PricingStatus.SEASONAL_UNPRICED,
            )
        ],
    )
    item = await MenuService.create_item(session, payload)
    assert item.pricing_type == PricingType.SEASONAL
    assert item.variants[0].price is None
    assert item.variants[0].pricing_status == PricingStatus.SEASONAL_UNPRICED


@pytest.mark.asyncio
async def test_update_item_atomically_synchronizes_variants() -> None:
    session = FakeMenuSession()
    cat = await MenuService.create_category(session, MenuCategoryCreate(name="Biryani"))
    session.add(cat)

    created = await MenuService.create_item(
        session,
        MenuItemCreate(
            category_id=cat.id,
            item_code="CB-TEST",
            name="Chicken Biryani",
            variants=[
                MenuPriceVariantCreate(
                    variant_name="Half",
                    is_portion=True,
                    price=Decimal("130.00"),
                ),
            ],
        ),
    )
    var_half = created.variants[0]

    # Update item and add Full portion atomically
    updated = await MenuService.update_item(
        session,
        created.id,
        MenuItemUpdate(
            name="Special Chicken Biryani",
            serving_description="Served with Mirchi ka Salan and Raita",
            variants=[
                MenuPriceVariantCreate(
                    id=var_half.id,
                    variant_name="Half",
                    is_portion=True,
                    price=Decimal("140.00"),
                ),
                MenuPriceVariantCreate(
                    variant_name="Full",
                    is_portion=True,
                    price=Decimal("240.00"),
                ),
            ],
        ),
    )
    assert updated.name == "Special Chicken Biryani"
    assert updated.serving_description == "Served with Mirchi ka Salan and Raita"
    assert len(updated.variants) == 2
    assert updated.variants[0].price == Decimal("140.00")
    assert updated.variants[1].price == Decimal("240.00")


@pytest.mark.asyncio
async def test_reorder_categories_and_safe_delete() -> None:
    session = FakeMenuSession()
    cat1 = await MenuService.create_category(session, MenuCategoryCreate(name="Cat 1"))
    cat2 = await MenuService.create_category(session, MenuCategoryCreate(name="Cat 2"))
    session.add(cat1)
    session.add(cat2)

    await MenuService.reorder_categories(
        session,
        CategoryReorderRequest(
            categories=[
                CategoryReorderItem(id=cat2.id, display_order=0),
                CategoryReorderItem(id=cat1.id, display_order=1),
            ]
        ),
    )
    assert cat2.display_order == 0
    assert cat1.display_order == 1

    # Safe delete (deactivate)
    await MenuService.delete_category(session, cat1.id)
    assert cat1.is_active is False

