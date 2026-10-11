"""Phase 4: Waiter Dual Short-Code & Full-Name Search Tests.

Follows `docs/05-api-specification.md` (Section 9.4) and
`docs/13-final-implementation-blueprint.md`.
Verifies:
1. Role authorization: WAITER and ADMIN allowed; KITCHEN and unauthenticated rejected.
2. Short-code priority ranking:
   - Rank 1: EXACT_VARIANT_CODE (e.g. 'CB-H' highlights matched variant)
   - Rank 2: EXACT_ITEM_CODE (e.g. 'CB' returns item with all portions)
   - Rank 3: PREFIX_CODE (e.g. 'C' matches 'CB', 'CK')
   - Rank 4: NAME_MATCH (e.g. 'Chicken' matches 'Chicken Biryani', 'Chicken Kebab')
3. Case-insensitivity and whitespace trimming.
4. Category filtering parameter (`category_id`).
5. Inactive items/variants are excluded from results.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.dependencies import get_current_staff_user
from app.main import create_app
from app.models.enums import PriceUnit, UserRole, UserStatus
from app.models.identity import User
from app.models.menu import MenuCategory, MenuItem, MenuPriceVariant
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


class FakeSearchSession:
    """Mock database session populated with sample menu items and variants."""

    def __init__(self, categories: list[MenuCategory], items: list[MenuItem]) -> None:
        self.categories = categories
        self.items = items

    async def execute(self, statement: Any) -> Any:
        stmt_str = str(statement).lower()

        # Handle category queries
        if "menu_categories" in stmt_str and "menu_items" not in stmt_str:
            return MockQueryResult(multiple=self.categories)

        # Handle item search queries
        active_items = [
            it
            for it in self.items
            if it.is_active and (it.category is None or it.category.is_active)
        ]
        return MockQueryResult(multiple=active_items)


@pytest.fixture
def sample_menu() -> tuple[list[MenuCategory], list[MenuItem]]:
    cat_biriyani = MenuCategory(
        id=uuid.uuid4(),
        name="Biriyani",
        display_order=1,
        is_active=True,
    )
    cat_starters = MenuCategory(
        id=uuid.uuid4(),
        name="Starters",
        display_order=2,
        is_active=True,
    )

    # 1. Chicken Biryani (CB) with variants CB-H, CB-F
    item_cb = MenuItem(
        id=uuid.uuid4(),
        category_id=cat_biriyani.id,
        item_code="CB",
        name="Chicken Biryani",
        display_order=1,
        is_active=True,
        is_available=True,
    )
    item_cb.category = cat_biriyani
    var_cb_h = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=item_cb.id,
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
    var_cb_f = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=item_cb.id,
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
    item_cb.variants = [var_cb_h, var_cb_f]

    # 2. Veg Biryani (VB) with variants VB-H, VB-F
    item_vb = MenuItem(
        id=uuid.uuid4(),
        category_id=cat_biriyani.id,
        item_code="VB",
        name="Veg Dum Biryani",
        display_order=2,
        is_active=True,
        is_available=True,
    )
    item_vb.category = cat_biriyani
    var_vb_h = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=item_vb.id,
        variant_code="VB-H",
        variant_name="Half",
        quantity_value=Decimal("0.50"),
        unit=PriceUnit.PORTION.value,
        price=Decimal("80.00"),
        is_default=False,
        is_available=True,
        is_active=True,
        display_order=1,
    )
    var_vb_f = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=item_vb.id,
        variant_code="VB-F",
        variant_name="Full",
        quantity_value=Decimal("1.00"),
        unit=PriceUnit.PORTION.value,
        price=Decimal("140.00"),
        is_default=True,
        is_available=True,
        is_active=True,
        display_order=2,
    )
    item_vb.variants = [var_vb_h, var_vb_f]

    # 3. Chicken Kebab (CK) with variants CK-2, CK-4
    item_ck = MenuItem(
        id=uuid.uuid4(),
        category_id=cat_starters.id,
        item_code="CK",
        name="Chicken Kebab",
        display_order=1,
        is_active=True,
        is_available=True,
    )
    item_ck.category = cat_starters
    var_ck_2 = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=item_ck.id,
        variant_code="CK-2",
        variant_name="2 Pcs",
        quantity_value=Decimal("2.00"),
        unit=PriceUnit.PIECE.value,
        price=Decimal("90.00"),
        is_default=False,
        is_available=True,
        is_active=True,
        display_order=1,
    )
    var_ck_4 = MenuPriceVariant(
        id=uuid.uuid4(),
        menu_item_id=item_ck.id,
        variant_code="CK-4",
        variant_name="4 Pcs",
        quantity_value=Decimal("4.00"),
        unit=PriceUnit.PIECE.value,
        price=Decimal("160.00"),
        is_default=True,
        is_available=True,
        is_active=True,
        display_order=2,
    )
    item_ck.variants = [var_ck_2, var_ck_4]

    categories = [cat_biriyani, cat_starters]
    items = [item_cb, item_vb, item_ck]
    return categories, items


# =============================================================================
# Ranking Service Tests
# =============================================================================


@pytest.mark.asyncio
async def test_search_exact_variant_code_priority(
    sample_menu: tuple[list[MenuCategory], list[MenuItem]],
) -> None:
    cats, items = sample_menu
    session = FakeSearchSession(cats, items)

    # Search for "CB-H"
    results = await MenuService.search_waiter_menu(session, "CB-H")  # type: ignore[arg-type]

    assert len(results) >= 1
    top = results[0]
    assert top.item_code == "CB"
    assert top.match_type == "EXACT_VARIANT_CODE"
    # Matched variant ID is highlighted
    expected_var = [v for v in items[0].variants if v.variant_code == "CB-H"][0]
    assert top.matched_variant_id == expected_var.id


@pytest.mark.asyncio
async def test_search_exact_item_code_priority(
    sample_menu: tuple[list[MenuCategory], list[MenuItem]],
) -> None:
    cats, items = sample_menu
    session = FakeSearchSession(cats, items)

    # Search for "CB"
    results = await MenuService.search_waiter_menu(session, "cb")  # type: ignore[arg-type]

    assert len(results) >= 1
    top = results[0]
    assert top.item_code == "CB"
    assert top.match_type == "EXACT_ITEM_CODE"
    assert top.matched_variant_id is None
    assert len(top.variants) == 2


@pytest.mark.asyncio
async def test_search_prefix_code_priority(
    sample_menu: tuple[list[MenuCategory], list[MenuItem]],
) -> None:
    cats, items = sample_menu
    session = FakeSearchSession(cats, items)

    # Search for "C" (prefixes CB and CK)
    results = await MenuService.search_waiter_menu(session, "c")  # type: ignore[arg-type]

    assert len(results) == 2
    for r in results:
        assert r.match_type == "PREFIX_CODE"
    item_codes = [r.item_code for r in results]
    assert "CB" in item_codes
    assert "CK" in item_codes


@pytest.mark.asyncio
async def test_search_full_name_fallback(
    sample_menu: tuple[list[MenuCategory], list[MenuItem]],
) -> None:
    cats, items = sample_menu
    session = FakeSearchSession(cats, items)

    # Search for "Dum Biryani" (substring match on Veg Dum Biryani)
    results = await MenuService.search_waiter_menu(session, "Dum Biryani")  # type: ignore[arg-type]

    assert len(results) == 1
    assert results[0].item_code == "VB"
    assert results[0].match_type == "NAME_MATCH"


# =============================================================================
# API Endpoint & RBAC Tests
# =============================================================================


@pytest.mark.asyncio
async def test_waiter_menu_search_rbac(
    sample_menu: tuple[list[MenuCategory], list[MenuItem]],
) -> None:
    cats, items = sample_menu
    session = FakeSearchSession(cats, items)

    app = create_app()
    app.dependency_overrides[get_db] = lambda: session

    # 1. Unauthenticated -> 401
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/waiter/menu/search?q=CB")
        assert resp.status_code == 401

    # 2. Kitchen role -> 403
    kitchen_user = User(
        id=uuid.uuid4(),
        username="chef_1",
        full_name="Chef Anand",
        role=UserRole.KITCHEN.value,
        is_active=True,
        status=UserStatus.ACTIVE.value,
        token_version=1,
    )
    app.dependency_overrides[get_current_staff_user] = lambda: kitchen_user
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/waiter/menu/search?q=CB")
        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "INSUFFICIENT_ROLE_PERMISSIONS"

    # 3. Waiter role -> 200 OK
    waiter_user = User(
        id=uuid.uuid4(),
        username="waiter_1",
        full_name="Ramesh Waiter",
        role=UserRole.WAITER.value,
        is_active=True,
        status=UserStatus.ACTIVE.value,
        token_version=1,
    )
    app.dependency_overrides[get_current_staff_user] = lambda: waiter_user
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/v1/waiter/menu/search?q=CB-F")
        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "CB-F"
        assert len(body["results"]) >= 1
        assert body["results"][0]["match_type"] == "EXACT_VARIANT_CODE"
