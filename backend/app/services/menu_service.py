"""Menu catalog domain service: categories, dishes, price variants, and search.

Follows `docs/04-database-design.md` (Sections 8-10), `docs/05-api-specification.md`
(Sections 6, 9.4, 12), and `docs/06-security-specification.md` (Sections 21, 26).
Enforces:
1. Unique item short codes (e.g. CB) and variant short codes (e.g. CB-H, CB-F, CK-2).
2. Atomic item + initial variants creation.
3. Historical price protection (variant price update does not affect historical orders;
   audit logged).
4. Dual short-code and full-name waiter search with deterministic priority ranking.
5. In-process WebSocket emission of `menu.availability_changed`.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ResourceNotFoundError, StateConflictError
from app.core.logging import get_logger
from app.core.time_utils import utc_now
from app.models.menu import MenuCategory, MenuItem, MenuPriceVariant
from app.models.orders import Order, OrderItem
from app.models.restaurant import RestaurantSettings
from app.realtime.manager import ws_manager
from app.schemas.menu import (
    CustomerCategorySummary,
    CustomerMenuCategory,
    CustomerMenuItem,
    CustomerMenuResponse,
    CustomerMenuVariant,
    MenuCategoryCreate,
    MenuCategoryUpdate,
    MenuItemCreate,
    MenuItemUpdate,
    MenuPriceVariantCreate,
    MenuPriceVariantUpdate,
    WaiterSearchResultItem,
    WaiterSearchVariant,
)
from app.services.audit_service import AuditService

logger = get_logger(__name__)


class MenuService:
    """Service handling categories, menu items, price variants, and catalog searches."""

    # =========================================================================
    # Category Management
    # =========================================================================

    @classmethod
    async def list_categories(
        cls,
        session: AsyncSession,
        *,
        active_only: bool = False,
    ) -> list[MenuCategory]:
        """List menu categories ordered by display_order then name."""
        stmt = select(MenuCategory).order_by(MenuCategory.display_order, MenuCategory.name)
        if active_only:
            stmt = stmt.where(MenuCategory.is_active.is_(True))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_category(
        cls,
        session: AsyncSession,
        category_id: uuid.UUID,
    ) -> MenuCategory:
        """Get a single category or raise ResourceNotFoundError."""
        category = await session.get(MenuCategory, category_id)
        if not category:
            raise ResourceNotFoundError(
                code="CATEGORY_NOT_FOUND",
                message=f"Menu category with ID '{category_id}' was not found.",
            )
        return category

    @classmethod
    async def create_category(
        cls,
        session: AsyncSession,
        data: MenuCategoryCreate,
        *,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str = "ADMIN",
    ) -> MenuCategory:
        """Create a new menu category with case-insensitive name uniqueness check."""
        clean_name = data.name.strip()
        existing = await session.execute(
            select(MenuCategory).where(func.lower(MenuCategory.name) == func.lower(clean_name))
        )
        if existing.scalar_one_or_none():
            raise StateConflictError(
                code="CATEGORY_ALREADY_EXISTS",
                message=f"Category with name '{clean_name}' already exists.",
                details={"name": clean_name},
            )

        category = MenuCategory(
            name=clean_name,
            description=data.description.strip() if data.description else None,
            display_order=data.display_order,
            is_active=data.is_active,
        )
        session.add(category)
        await session.flush()

        await AuditService.record_event(
            session,
            action_type="MENU_CATEGORY_CREATED",
            entity_type="menu_category",
            entity_id=str(category.id),
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            new_value={"name": category.name, "display_order": category.display_order},
        )
        return category

    @classmethod
    async def update_category(
        cls,
        session: AsyncSession,
        category_id: uuid.UUID,
        data: MenuCategoryUpdate,
        *,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str = "ADMIN",
    ) -> MenuCategory:
        """Update an existing category with uniqueness checks and audit logging."""
        category = await cls.get_category(session, category_id)
        old_val: dict[str, Any] = {
            "name": category.name,
            "description": category.description,
            "display_order": category.display_order,
            "is_active": category.is_active,
        }

        if data.name is not None:
            clean_name = data.name.strip()
            if clean_name.lower() != category.name.lower():
                dup = await session.execute(
                    select(MenuCategory).where(
                        func.lower(MenuCategory.name) == func.lower(clean_name),
                        MenuCategory.id != category_id,
                    )
                )
                if dup.scalar_one_or_none():
                    raise StateConflictError(
                        code="CATEGORY_ALREADY_EXISTS",
                        message=f"Another category with name '{clean_name}' already exists.",
                    )
            category.name = clean_name

        if data.description is not None:
            category.description = data.description.strip() if data.description else None

        if data.display_order is not None:
            category.display_order = data.display_order

        if data.is_active is not None:
            category.is_active = data.is_active

        await session.flush()

        await AuditService.record_event(
            session,
            action_type="MENU_CATEGORY_UPDATED",
            entity_type="menu_category",
            entity_id=str(category.id),
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            old_value=old_val,
            new_value={
                "name": category.name,
                "display_order": category.display_order,
                "is_active": category.is_active,
            },
        )
        return category

    # =========================================================================
    # Menu Item & Variant Management
    # =========================================================================

    @classmethod
    async def list_items(
        cls,
        session: AsyncSession,
        *,
        category_id: uuid.UUID | None = None,
        active_only: bool = False,
    ) -> list[MenuItem]:
        """List menu items with eager loaded variants."""
        stmt = (
            select(MenuItem)
            .options(selectinload(MenuItem.variants))
            .order_by(MenuItem.display_order, MenuItem.name)
        )
        if category_id:
            stmt = stmt.where(MenuItem.category_id == category_id)
        if active_only:
            stmt = stmt.where(MenuItem.is_active.is_(True))

        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def get_item(
        cls,
        session: AsyncSession,
        item_id: uuid.UUID,
    ) -> MenuItem:
        """Get a single menu item with variants or raise ResourceNotFoundError."""
        stmt = (
            select(MenuItem).where(MenuItem.id == item_id).options(selectinload(MenuItem.variants))
        )
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError(
                code="ITEM_NOT_FOUND",
                message=f"Menu item with ID '{item_id}' was not found.",
            )
        return item

    @classmethod
    async def create_item(
        cls,
        session: AsyncSession,
        data: MenuItemCreate,
        *,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str = "ADMIN",
    ) -> MenuItem:
        """Create a new dish along with its initial price variant(s) in one atomic transaction."""
        # 1. Verify category exists
        await cls.get_category(session, data.category_id)

        # 2. Check item_code uniqueness (case-insensitive)
        clean_item_code = data.item_code.strip().upper()
        existing_item = await session.execute(
            select(MenuItem).where(func.upper(MenuItem.item_code) == clean_item_code)
        )
        if existing_item.scalar_one_or_none():
            raise StateConflictError(
                code="ITEM_CODE_ALREADY_EXISTS",
                message=f"Menu item code '{clean_item_code}' is already in use.",
                details={"item_code": clean_item_code},
            )

        # 3. Validate variant codes uniqueness within payload and against database
        input_variant_codes: set[str] = set()
        for v in data.variants:
            if v.variant_code:
                code_upper = v.variant_code.strip().upper()
                if code_upper in input_variant_codes:
                    raise StateConflictError(
                        code="VARIANT_CODE_ALREADY_EXISTS",
                        message=f"Duplicate variant code '{code_upper}' in request.",
                        details={"variant_code": code_upper},
                    )
                input_variant_codes.add(code_upper)

                existing_variant = await session.execute(
                    select(MenuPriceVariant).where(
                        func.upper(MenuPriceVariant.variant_code) == code_upper
                    )
                )
                if existing_variant.scalar_one_or_none():
                    raise StateConflictError(
                        code="VARIANT_CODE_ALREADY_EXISTS",
                        message=f"Variant code '{code_upper}' is already in use by another item.",
                        details={"variant_code": code_upper},
                    )

        # 4. Create MenuItem
        item = MenuItem(
            category_id=data.category_id,
            item_code=clean_item_code,
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            dietary_type=data.dietary_type.value if data.dietary_type else None,
            spice_level=data.spice_level.value if data.spice_level else None,
            image_url=data.image_url,
            tax_rate_override=data.tax_rate_override,
            is_available=data.is_available,
            display_order=data.display_order,
        )
        session.add(item)
        await session.flush()

        # 5. Create variants
        has_default = any(v.is_default for v in data.variants)
        for idx, v_data in enumerate(data.variants):
            is_def = v_data.is_default or (not has_default and idx == 0)
            variant = MenuPriceVariant(
                menu_item_id=item.id,
                variant_code=v_data.variant_code.strip().upper() if v_data.variant_code else None,
                variant_name=v_data.variant_name.strip(),
                quantity_value=v_data.quantity_value,
                unit=v_data.unit.value,
                price=v_data.price,
                is_default=is_def,
                is_available=v_data.is_available,
                display_order=v_data.display_order,
            )
            session.add(variant)

        await session.flush()

        await AuditService.record_event(
            session,
            action_type="MENU_ITEM_CREATED",
            entity_type="menu_item",
            entity_id=str(item.id),
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            new_value={
                "item_code": item.item_code,
                "name": item.name,
                "category_id": str(item.category_id),
                "variant_count": len(data.variants),
            },
        )

        return await cls.get_item(session, item.id)

    @classmethod
    async def update_item(
        cls,
        session: AsyncSession,
        item_id: uuid.UUID,
        data: MenuItemUpdate,
        *,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str = "ADMIN",
    ) -> MenuItem:
        """Update menu item details with code uniqueness validation."""
        item = await cls.get_item(session, item_id)
        old_val: dict[str, Any] = {
            "item_code": item.item_code,
            "name": item.name,
            "category_id": str(item.category_id),
            "is_active": item.is_active,
            "is_available": item.is_available,
        }

        if data.category_id is not None:
            await cls.get_category(session, data.category_id)
            item.category_id = data.category_id

        if data.item_code is not None:
            clean_code = data.item_code.strip().upper()
            if clean_code != item.item_code:
                dup = await session.execute(
                    select(MenuItem).where(
                        func.upper(MenuItem.item_code) == clean_code,
                        MenuItem.id != item_id,
                    )
                )
                if dup.scalar_one_or_none():
                    raise StateConflictError(
                        code="ITEM_CODE_ALREADY_EXISTS",
                        message=f"Menu item code '{clean_code}' is already in use.",
                    )
                item.item_code = clean_code

        if data.name is not None:
            item.name = data.name.strip()
        if data.description is not None:
            item.description = data.description.strip() if data.description else None
        if data.dietary_type is not None:
            item.dietary_type = data.dietary_type.value
        if "spice_level" in data.model_fields_set:
            # explicit null clears the spice level (dish has no spice rating)
            item.spice_level = data.spice_level.value if data.spice_level else None
        if data.tax_rate_override is not None:
            item.tax_rate_override = data.tax_rate_override
        if data.is_available is not None:
            item.is_available = data.is_available
        if data.is_active is not None:
            item.is_active = data.is_active
        if data.display_order is not None:
            item.display_order = data.display_order

        await session.flush()

        await AuditService.record_event(
            session,
            action_type="MENU_ITEM_UPDATED",
            entity_type="menu_item",
            entity_id=str(item.id),
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            old_value=old_val,
            new_value={
                "item_code": item.item_code,
                "name": item.name,
                "category_id": str(item.category_id),
                "is_active": item.is_active,
                "is_available": item.is_available,
            },
        )
        return item

    @classmethod
    async def set_item_availability(
        cls,
        session: AsyncSession,
        item_id: uuid.UUID,
        *,
        is_available: bool,
        reason: str | None = None,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str = "ADMIN",
    ) -> MenuItem:
        """Instant stock toggle (`is_available`), writes audit log and broadcasts event."""
        item = await cls.get_item(session, item_id)
        old_availability = item.is_available
        item.is_available = is_available
        await session.flush()

        await AuditService.record_event(
            session,
            action_type="MENU_ITEM_AVAILABILITY_CHANGED",
            entity_type="menu_item",
            entity_id=str(item.id),
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            reason=reason,
            old_value={"is_available": old_availability},
            new_value={"is_available": is_available},
        )

        # Broadcast realtime menu.availability_changed event post-commit
        event_payload = {
            "event": "menu.availability_changed",
            "event_type": "menu.availability_changed",
            "data": {
                "item_id": str(item.id),
                "item_code": item.item_code,
                "item_name": item.name,
                "category_id": str(item.category_id),
                "is_available": item.is_available,
                "is_active": item.is_active,
                "reason": reason,
                "variants": [
                    {
                        "variant_id": str(v.id),
                        "variant_code": v.variant_code,
                        "variant_name": v.variant_name,
                        "price": str(v.price),
                        "is_available": v.is_available,
                        "is_active": v.is_active,
                    }
                    for v in item.variants
                ],
            },
        }
        await ws_manager.broadcast_to_room("channel:menu", event_payload)
        return item

    # =========================================================================
    # Price Variant Management & Historical Pricing Protection
    # =========================================================================

    @classmethod
    async def create_variant(
        cls,
        session: AsyncSession,
        item_id: uuid.UUID,
        data: MenuPriceVariantCreate,
        *,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str = "ADMIN",
    ) -> MenuPriceVariant:
        """Add a new variant to an existing dish."""
        item = await cls.get_item(session, item_id)

        clean_vcode = data.variant_code.strip().upper() if data.variant_code else None
        if clean_vcode:
            existing = await session.execute(
                select(MenuPriceVariant).where(
                    func.upper(MenuPriceVariant.variant_code) == clean_vcode
                )
            )
            if existing.scalar_one_or_none():
                raise StateConflictError(
                    code="VARIANT_CODE_ALREADY_EXISTS",
                    message=f"Variant code '{clean_vcode}' is already in use.",
                    details={"variant_code": clean_vcode},
                )

        clean_vname = data.variant_name.strip()
        dup_name = await session.execute(
            select(MenuPriceVariant).where(
                MenuPriceVariant.menu_item_id == item_id,
                func.lower(MenuPriceVariant.variant_name) == func.lower(clean_vname),
            )
        )
        if dup_name.scalar_one_or_none():
            raise StateConflictError(
                code="VARIANT_NAME_ALREADY_EXISTS",
                message=f"Variant '{clean_vname}' already exists for item '{item.name}'.",
            )

        if data.is_default:
            # Unset existing defaults
            for v in item.variants:
                if v.is_default:
                    v.is_default = False

        variant = MenuPriceVariant(
            menu_item_id=item_id,
            variant_code=clean_vcode,
            variant_name=clean_vname,
            quantity_value=data.quantity_value,
            unit=data.unit.value,
            price=data.price,
            is_default=data.is_default,
            is_available=data.is_available,
            display_order=data.display_order,
        )
        session.add(variant)
        await session.flush()

        await AuditService.record_event(
            session,
            action_type="MENU_VARIANT_CREATED",
            entity_type="menu_price_variant",
            entity_id=str(variant.id),
            actor_role=actor_role,
            actor_user_id=actor_user_id,
            new_value={
                "variant_code": variant.variant_code,
                "variant_name": variant.variant_name,
                "price": str(variant.price),
            },
        )
        return variant

    @classmethod
    async def update_variant(
        cls,
        session: AsyncSession,
        variant_id: uuid.UUID,
        data: MenuPriceVariantUpdate,
        *,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str = "ADMIN",
    ) -> MenuPriceVariant:
        """Update a price variant.

        HISTORICAL PRICING GUARANTEE:
        Updating `menu_price_variants.price` affects ONLY future orders. Existing `order_items`
        and `bill_items` preserve their immutable unit_price_snapshot values.
        Writes PRICE_VARIANT_PRICE_CHANGED to audit_logs whenever price is updated.
        """
        variant = await session.get(MenuPriceVariant, variant_id)
        if not variant:
            raise ResourceNotFoundError(
                code="VARIANT_NOT_FOUND",
                message=f"Menu price variant with ID '{variant_id}' was not found.",
            )

        old_price = variant.price
        price_changed = data.price is not None and data.price != old_price

        if data.variant_code is not None:
            clean_code = data.variant_code.strip().upper()
            if clean_code != variant.variant_code:
                dup = await session.execute(
                    select(MenuPriceVariant).where(
                        func.upper(MenuPriceVariant.variant_code) == clean_code,
                        MenuPriceVariant.id != variant_id,
                    )
                )
                if dup.scalar_one_or_none():
                    raise StateConflictError(
                        code="VARIANT_CODE_ALREADY_EXISTS",
                        message=f"Variant code '{clean_code}' is already in use.",
                    )
                variant.variant_code = clean_code

        if data.variant_name is not None:
            clean_vname = data.variant_name.strip()
            if clean_vname.lower() != variant.variant_name.lower():
                dup = await session.execute(
                    select(MenuPriceVariant).where(
                        MenuPriceVariant.menu_item_id == variant.menu_item_id,
                        func.lower(MenuPriceVariant.variant_name) == func.lower(clean_vname),
                        MenuPriceVariant.id != variant_id,
                    )
                )
                if dup.scalar_one_or_none():
                    raise StateConflictError(
                        code="VARIANT_NAME_ALREADY_EXISTS",
                        message=f"Variant name '{clean_vname}' already exists for this dish.",
                    )
                variant.variant_name = clean_vname

        if data.quantity_value is not None:
            variant.quantity_value = data.quantity_value
        if data.unit is not None:
            variant.unit = data.unit.value
        if price_changed:
            variant.price = data.price
        if data.is_default is not None:
            if data.is_default:
                # Unset existing defaults
                item = await cls.get_item(session, variant.menu_item_id)
                for v in item.variants:
                    if v.id != variant_id and v.is_default:
                        v.is_default = False
            variant.is_default = data.is_default
        if data.is_available is not None:
            variant.is_available = data.is_available
        if data.is_active is not None:
            variant.is_active = data.is_active
        if data.display_order is not None:
            variant.display_order = data.display_order

        await session.flush()

        # Audit price change explicitly if price was altered
        if price_changed:
            await AuditService.record_event(
                session,
                action_type="PRICE_VARIANT_PRICE_CHANGED",
                entity_type="menu_price_variant",
                entity_id=str(variant.id),
                actor_role=actor_role,
                actor_user_id=actor_user_id,
                old_value={"price": str(old_price)},
                new_value={"price": str(variant.price)},
            )
        else:
            await AuditService.record_event(
                session,
                action_type="MENU_VARIANT_UPDATED",
                entity_type="menu_price_variant",
                entity_id=str(variant.id),
                actor_role=actor_role,
                actor_user_id=actor_user_id,
                new_value={
                    "variant_name": variant.variant_name,
                    "is_available": variant.is_available,
                    "is_active": variant.is_active,
                },
            )

        # Notify clients about menu update
        await ws_manager.broadcast_to_room(
            "channel:menu",
            {
                "event": "menu.availability_changed",
                "event_type": "menu.availability_changed",
                "data": {
                    "variant_id": str(variant.id),
                    "variant_code": variant.variant_code,
                    "price": str(variant.price),
                    "is_available": variant.is_available,
                    "is_active": variant.is_active,
                },
            },
        )
        return variant

    # =========================================================================
    # Waiter Dual Short-Code & Full-Name Search (Section 9.4)
    # =========================================================================

    @classmethod
    async def search_waiter_menu(
        cls,
        session: AsyncSession,
        query: str,
        *,
        category_id: uuid.UUID | None = None,
    ) -> list[WaiterSearchResultItem]:
        """Dual Short-Code & Full-Name Search for rapid table-side waiter entry.

        Ranking hierarchy:
        1. Exact Variant Code Match (e.g. UPPER(variant_code) == 'CB-H') -> EXACT_VARIANT_CODE
        2. Exact Item Code Match (e.g. UPPER(item_code) == 'CB') -> EXACT_ITEM_CODE
        3. Prefix Item Code Match (e.g. UPPER(item_code) LIKE 'CB%') -> PREFIX_CODE
        4. Dish Name Substring Match (e.g. name ILIKE '%chicken biryani%') -> NAME_MATCH
        """
        clean_q = query.strip()
        if not clean_q:
            return []

        upper_q = clean_q.upper()
        lower_q = clean_q.lower()

        # Fetch active items with active categories and active variants
        stmt = (
            select(MenuItem)
            .join(MenuItem.category)
            .where(
                MenuItem.is_active.is_(True),
                MenuCategory.is_active.is_(True),
            )
            .options(
                selectinload(MenuItem.category),
                selectinload(MenuItem.variants),
            )
        )
        if category_id:
            stmt = stmt.where(MenuItem.category_id == category_id)

        result = await session.execute(stmt)
        items = list(result.scalars().all())

        ranked_results: list[tuple[int, MenuItem, str, uuid.UUID | None]] = []

        for item in items:
            best_rank = 999
            best_match_type = ""
            matched_var_id: uuid.UUID | None = None

            # Check 1: Exact Variant Code match
            for v in item.variants:
                if v.is_active and v.variant_code and v.variant_code.upper() == upper_q:
                    best_rank = 1
                    best_match_type = "EXACT_VARIANT_CODE"
                    matched_var_id = v.id
                    break

            # Check 2: Exact Item Code match
            if best_rank > 2 and item.item_code.upper() == upper_q:
                best_rank = 2
                best_match_type = "EXACT_ITEM_CODE"

            # Check 3: Prefix Item Code match
            if best_rank > 3 and item.item_code.upper().startswith(upper_q):
                best_rank = 3
                best_match_type = "PREFIX_CODE"

            # Check 4: Dish Name substring match
            if best_rank > 4 and lower_q in item.name.lower():
                best_rank = 4
                best_match_type = "NAME_MATCH"

            if best_rank < 999:
                ranked_results.append((best_rank, item, best_match_type, matched_var_id))

        # Sort: best_rank asc, display_order asc, item name asc
        ranked_results.sort(key=lambda r: (r[0], r[1].display_order, r[1].name))

        output: list[WaiterSearchResultItem] = []
        for _rank, item, match_type, matched_var_id in ranked_results:
            active_variants = [
                WaiterSearchVariant(
                    variant_id=v.id,
                    variant_code=v.variant_code,
                    variant_name=v.variant_name,
                    quantity_value=v.quantity_value,
                    unit=v.unit,
                    price=v.price,
                    is_available=v.is_available,
                )
                for v in sorted(item.variants, key=lambda x: (x.display_order, x.price))
                if v.is_active
            ]

            output.append(
                WaiterSearchResultItem(
                    item_id=item.id,
                    item_code=item.item_code,
                    name=item.name,
                    category_name=item.category.name,
                    is_available=item.is_available,
                    match_type=match_type,  # type: ignore[arg-type]
                    matched_variant_id=matched_var_id,
                    variants=active_variants,
                )
            )

        return output

    # =========================================================================
    # Customer Menu Catalog (Section 6)
    # =========================================================================

    @classmethod
    async def get_customer_menu(
        cls,
        session: AsyncSession,
        *,
        category_id: uuid.UUID | None = None,
        dietary_type: str | None = None,
        available_only: bool = False,
    ) -> CustomerMenuResponse:
        """Retrieve the complete active menu grouped by active categories.

        Includes currency, tax rates from RestaurantSettings singleton, and active variants.
        """
        # Fetch restaurant settings (singleton id=1)
        settings_row = await session.get(RestaurantSettings, 1)
        currency_sym = settings_row.currency_symbol if settings_row else "₹"
        prices_inc_tax = settings_row.prices_include_tax if settings_row else False
        cgst = settings_row.cgst_percentage if settings_row else Decimal("2.50")
        sgst = settings_row.sgst_percentage if settings_row else Decimal("2.50")

        # Fetch active categories
        cat_stmt = (
            select(MenuCategory)
            .where(MenuCategory.is_active.is_(True))
            .order_by(MenuCategory.display_order, MenuCategory.name)
        )
        if category_id:
            cat_stmt = cat_stmt.where(MenuCategory.id == category_id)

        categories = list((await session.execute(cat_stmt)).scalars().all())

        # Fetch active items with active variants
        item_stmt = (
            select(MenuItem)
            .join(MenuItem.category)
            .where(
                MenuItem.is_active.is_(True),
                MenuCategory.is_active.is_(True),
            )
            .options(selectinload(MenuItem.variants))
            .order_by(MenuItem.display_order, MenuItem.name)
        )
        if category_id:
            item_stmt = item_stmt.where(MenuItem.category_id == category_id)
        if dietary_type:
            item_stmt = item_stmt.where(MenuItem.dietary_type == dietary_type)
        if available_only:
            item_stmt = item_stmt.where(MenuItem.is_available.is_(True))

        items = list((await session.execute(item_stmt)).scalars().all())

        # Group items by category
        items_by_cat: dict[uuid.UUID, list[CustomerMenuItem]] = {c.id: [] for c in categories}
        for item in items:
            if item.category_id not in items_by_cat:
                continue

            active_variants = [
                CustomerMenuVariant(
                    id=v.id,
                    variant_code=v.variant_code,
                    variant_name=v.variant_name,
                    quantity_value=v.quantity_value,
                    unit=v.unit,
                    price=v.price,
                    is_default=v.is_default,
                    is_available=v.is_available,
                )
                for v in sorted(item.variants, key=lambda x: (x.display_order, x.price))
                if v.is_active and (not available_only or v.is_available)
            ]

            if not active_variants:
                continue

            items_by_cat[item.category_id].append(
                CustomerMenuItem(
                    id=item.id,
                    item_code=item.item_code,
                    name=item.name,
                    description=item.description,
                    dietary_type=item.dietary_type,
                    spice_level=item.spice_level,
                    image_url=item.image_url,
                    is_available=item.is_available,
                    variants=active_variants,
                )
            )

        cat_responses: list[CustomerMenuCategory] = []
        for cat in categories:
            cat_items = items_by_cat.get(cat.id, [])
            cat_responses.append(
                CustomerMenuCategory(
                    id=cat.id,
                    name=cat.name,
                    description=cat.description,
                    display_order=cat.display_order,
                    items=cat_items,
                )
            )

        popular_ids = await cls._popular_item_ids(
            session,
            {it.id for cat_items in items_by_cat.values() for it in cat_items if it.is_available},
        )

        return CustomerMenuResponse(
            currency_symbol=currency_sym,
            prices_include_tax=prices_inc_tax,
            cgst_percentage=cgst,
            sgst_percentage=sgst,
            categories=cat_responses,
            popular_item_ids=popular_ids,
        )

    @classmethod
    async def _popular_item_ids(
        cls,
        session: AsyncSession,
        orderable_ids: set[uuid.UUID],
        *,
        limit: int = 6,
        days: int = 30,
    ) -> list[uuid.UUID]:
        """Dishes with the highest billed quantity in the last `days` days (best first).

        Rejected/cancelled orders and cancelled quantities are ignored. Only dishes that are
        currently on the menu and in stock are returned.
        """
        if not orderable_ids:
            return []
        since = utc_now() - timedelta(days=days)
        total_qty = func.sum(OrderItem.active_quantity).label("total_qty")
        stmt = (
            select(OrderItem.menu_item_id.label("menu_item_id"), total_qty)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.status.notin_(["REJECTED", "CANCELLED"]),
                Order.placed_at >= since,
                OrderItem.active_quantity > 0,
            )
            .group_by(OrderItem.menu_item_id)
            .order_by(desc(total_qty))
            .limit(limit * 3)
        )
        rows = (await session.execute(stmt)).all()
        result: list[uuid.UUID] = []
        for row in rows:
            item_id = getattr(row, "menu_item_id", None)
            if item_id in orderable_ids and item_id not in result:
                result.append(item_id)
            if len(result) >= limit:
                break
        return result

    @classmethod
    async def get_customer_categories(
        cls,
        session: AsyncSession,
    ) -> list[CustomerCategorySummary]:
        """Retrieve active categories with item count for tab navigation."""
        stmt = (
            select(
                MenuCategory.id,
                MenuCategory.name,
                MenuCategory.description,
                MenuCategory.display_order,
                func.count(MenuItem.id).label("item_count"),
            )
            .outerjoin(
                MenuItem,
                (MenuItem.category_id == MenuCategory.id) & (MenuItem.is_active.is_(True)),
            )
            .where(MenuCategory.is_active.is_(True))
            .group_by(
                MenuCategory.id,
                MenuCategory.name,
                MenuCategory.description,
                MenuCategory.display_order,
            )
            .order_by(MenuCategory.display_order, MenuCategory.name)
        )
        rows = (await session.execute(stmt)).all()
        return [
            CustomerCategorySummary(
                id=r.id,
                name=r.name,
                description=r.description,
                display_order=r.display_order,
                item_count=r.item_count,
            )
            for r in rows
        ]

    @classmethod
    async def get_customer_item(
        cls,
        session: AsyncSession,
        item_id: uuid.UUID,
    ) -> CustomerMenuItem:
        """Retrieve single active dish details and variants for customer dialog."""
        stmt = (
            select(MenuItem)
            .join(MenuItem.category)
            .where(
                MenuItem.id == item_id,
                MenuItem.is_active.is_(True),
                MenuCategory.is_active.is_(True),
            )
            .options(selectinload(MenuItem.variants))
        )
        item = (await session.execute(stmt)).scalar_one_or_none()
        if not item:
            raise ResourceNotFoundError(
                code="ITEM_NOT_FOUND",
                message=f"Menu item '{item_id}' not found or inactive.",
            )

        active_variants = [
            CustomerMenuVariant(
                id=v.id,
                variant_code=v.variant_code,
                variant_name=v.variant_name,
                quantity_value=v.quantity_value,
                unit=v.unit,
                price=v.price,
                is_default=v.is_default,
                is_available=v.is_available,
            )
            for v in sorted(item.variants, key=lambda x: (x.display_order, x.price))
            if v.is_active
        ]

        return CustomerMenuItem(
            id=item.id,
            item_code=item.item_code,
            name=item.name,
            description=item.description,
            dietary_type=item.dietary_type,
            spice_level=item.spice_level,
            image_url=item.image_url,
            is_available=item.is_available,
            variants=active_variants,
        )

    @classmethod
    async def search_customer_menu(
        cls,
        session: AsyncSession,
        query: str,
        *,
        dietary_type: str | None = None,
    ) -> list[CustomerMenuItem]:
        """Customer search by dish name or item code."""
        clean_q = query.strip()
        if not clean_q:
            return []

        lower_q = clean_q.lower()
        upper_q = clean_q.upper()

        stmt = (
            select(MenuItem)
            .join(MenuItem.category)
            .where(
                MenuItem.is_active.is_(True),
                MenuCategory.is_active.is_(True),
                (func.lower(MenuItem.name).contains(lower_q))
                | (func.upper(MenuItem.item_code) == upper_q),
            )
            .options(selectinload(MenuItem.variants))
            .order_by(MenuItem.display_order, MenuItem.name)
        )
        if dietary_type:
            stmt = stmt.where(MenuItem.dietary_type == dietary_type)

        items = list((await session.execute(stmt)).scalars().all())
        results: list[CustomerMenuItem] = []
        for item in items:
            active_variants = [
                CustomerMenuVariant(
                    id=v.id,
                    variant_code=v.variant_code,
                    variant_name=v.variant_name,
                    quantity_value=v.quantity_value,
                    unit=v.unit,
                    price=v.price,
                    is_default=v.is_default,
                    is_available=v.is_available,
                )
                for v in sorted(item.variants, key=lambda x: (x.display_order, x.price))
                if v.is_active
            ]
            results.append(
                CustomerMenuItem(
                    id=item.id,
                    item_code=item.item_code,
                    name=item.name,
                    description=item.description,
                    dietary_type=item.dietary_type,
                    spice_level=item.spice_level,
                    image_url=item.image_url,
                    is_available=item.is_available,
                    variants=active_variants,
                )
            )
        return results
