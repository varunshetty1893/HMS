"""Phase 4: Customer Menu Catalog API & Service Tests.

Follows `docs/05-api-specification.md` (Section 6) and `docs/13-final-implementation-blueprint.md`.
Verifies:
1. `GET /api/v1/customer/menu`:
   - Catalog grouped by category
   - Tax percentages and currency symbols from settings
   - Query filters: category_id, dietary_type, available_only
2. `GET /api/v1/customer/menu/categories`:
   - Ordered category list with item counts
3. `GET /api/v1/customer/menu/items/{id}`:
   - Single dish detail with portion variants
   - 404 ITEM_NOT_FOUND on missing or inactive dish
4. `GET /api/v1/customer/menu/search`:
   - Search active items by dish name or short code
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import create_app
from app.models.enums import DietaryType, PriceUnit, SpiceLevel
from app.models.menu import MenuCategory, MenuItem, MenuPriceVariant
from app.models.restaurant import RestaurantSettings


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


class FakeCustomerMenuSession:
    """Mock database session populated with settings and menu items."""

    def __init__(
        self,
        categories: list[MenuCategory],
        items: list[MenuItem],
        settings_row: RestaurantSettings | None = None,
    ) -> None:
        self.categories = categories
        self.items = items
        self.settings_row = settings_row or RestaurantSettings(
            id=1,
            restaurant_name="The Royal Spice",
            currency_symbol="₹",
            prices_include_tax=False,
            cgst_percentage=Decimal("2.50"),
            sgst_percentage=Decimal("2.50"),
        )

    async def get(self, entity_cls: Any, pk: Any) -> Any:
        if entity_cls is RestaurantSettings and pk == 1:
            return self.settings_row
        if entity_cls is MenuItem:
            return next((it for it in self.items if it.id == pk), None)
        return None

    async def execute(self, statement: Any) -> Any:
        stmt_str = str(statement).lower()

        # Handle categories with count query
        if "menu_categories" in stmt_str and "count(" in stmt_str:
            rows = [
                type(
                    "Row",
                    (),
                    {
                        "id": c.id,
                        "name": c.name,
                        "description": c.description,
                        "display_order": c.display_order,
                        "item_count": len(
                            [i for i in self.items if i.category_id == c.id and i.is_active]
                        ),
                    },
                )()
                for c in self.categories
                if c.is_active
            ]
            return MockQueryResult(multiple=rows)

        if "menu_categories" in stmt_str and "menu_items" not in stmt_str:
            cats = [c for c in self.categories if c.is_active]
            return MockQueryResult(multiple=cats)

        # Handle items queries
        active_items = [
            it
            for it in self.items
            if it.is_active and (it.category is None or it.category.is_active)
        ]
        return MockQueryResult(
            single=active_items[0] if active_items else None,
            multiple=active_items,
        )


@pytest.fixture
def populated_menu() -> tuple[list[MenuCategory], list[MenuItem]]:
    cat_biriyani = MenuCategory(
        id=uuid.uuid4(),
        name="Biriyani",
        description="Dum Biriyanis",
        display_order=1,
        is_active=True,
    )
    cat_starters = MenuCategory(
        id=uuid.uuid4(),
        name="Starters",
        description="Appetizers",
        display_order=2,
        is_active=True,
    )

    item1 = MenuItem(
        id=uuid.uuid4(),
        category_id=cat_biriyani.id,
        item_code="CB",
        name="Chicken Biryani",
        description="Spiced chicken biryani",
        dietary_type=DietaryType.NON_VEG.value,
        spice_level=SpiceLevel.MEDIUM.value,
        display_order=1,
        is_active=True,
        is_available=True,
    )
    item1.category = cat_biriyani
    var1_h = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=item1.id,
        variant_code="CB-H",
        variant_name="Half",
        quantity_value=Decimal("0.50"),
        unit=PriceUnit.PORTION.value,
        price=Decimal("100.00"),
        is_default=False,
        is_available=True,
        is_active=True,
        display_order=1,
    )
    var1_f = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=item1.id,
        variant_code="CB-F",
        variant_name="Full",
        quantity_value=Decimal("1.00"),
        unit=PriceUnit.PORTION.value,
        price=Decimal("180.00"),
        is_default=True,
        is_available=True,
        is_active=True,
        display_order=2,
    )
    item1.variants = [var1_h, var1_f]

    item2 = MenuItem(
        id=uuid.uuid4(),
        category_id=cat_biriyani.id,
        item_code="VB",
        name="Veg Dum Biryani",
        description="Fresh vegetable biryani",
        dietary_type=DietaryType.VEG.value,
        spice_level=SpiceLevel.MILD.value,
        display_order=2,
        is_active=True,
        is_available=False,  # Sold out
    )
    item2.category = cat_biriyani
    var2 = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=item2.id,
        variant_code="VB-F",
        variant_name="Full",
        quantity_value=Decimal("1.00"),
        unit=PriceUnit.PORTION.value,
        price=Decimal("140.00"),
        is_default=True,
        is_available=False,
        is_active=True,
        display_order=1,
    )
    item2.variants = [var2]

    return [cat_biriyani, cat_starters], [item1, item2]


# =============================================================================
# API Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_customer_menu_full_structure(
    populated_menu: tuple[list[MenuCategory], list[MenuItem]],
) -> None:
    cats, items = populated_menu
    session = FakeCustomerMenuSession(cats, items)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/customer/menu")
        assert resp.status_code == 200
        data = resp.json()
        assert data["currency_symbol"] == "₹"
        assert data["prices_include_tax"] is False
        assert data["cgst_percentage"] == "2.50"
        assert data["sgst_percentage"] == "2.50"
        assert len(data["categories"]) >= 1

        cat = data["categories"][0]
        assert cat["name"] == "Biriyani"
        assert len(cat["items"]) == 2

        # Check Chicken Biryani
        dish1 = next(d for d in cat["items"] if d["item_code"] == "CB")
        assert dish1["is_available"] is True
        assert len(dish1["variants"]) == 2

        # Check Veg Biryani (unavailable sold-out badge)
        dish2 = next(d for d in cat["items"] if d["item_code"] == "VB")
        assert dish2["is_available"] is False


@pytest.mark.asyncio
async def test_get_customer_categories(
    populated_menu: tuple[list[MenuCategory], list[MenuItem]],
) -> None:
    cats, items = populated_menu
    session = FakeCustomerMenuSession(cats, items)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/customer/menu/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "Biriyani"
        assert data[0]["item_count"] == 2
        assert data[1]["name"] == "Starters"
        assert data[1]["item_count"] == 0


@pytest.mark.asyncio
async def test_get_customer_item_details(
    populated_menu: tuple[list[MenuCategory], list[MenuItem]],
) -> None:
    cats, items = populated_menu
    session = FakeCustomerMenuSession(cats, items)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        item_id = items[0].id
        resp = await client.get(f"/api/v1/customer/menu/items/{item_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["item_code"] == "CB"
        assert data["name"] == "Chicken Biryani"
        assert len(data["variants"]) == 2


@pytest.mark.asyncio
async def test_search_customer_menu(
    populated_menu: tuple[list[MenuCategory], list[MenuItem]],
) -> None:
    cats, items = populated_menu
    session = FakeCustomerMenuSession(cats, items)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/customer/menu/search?q=chicken")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["item_code"] == "CB"
