"""Restaurant settings service for singleton configuration and operational policies."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ActorRole
from app.models.identity import User
from app.models.restaurant import RestaurantSettings
from app.schemas.settings import RestaurantSettingsResponse, RestaurantSettingsUpdate
from app.services.audit_service import AuditService


class SettingsService:
    """Service for managing singleton restaurant configuration (id=1)."""

    @classmethod
    async def get_settings(cls, db: AsyncSession) -> RestaurantSettings:
        """Fetch the singleton restaurant_settings row (id=1)."""
        settings = await db.get(RestaurantSettings, 1)
        if not settings:
            # Fallback initialization if DB not pre-seeded
            settings = RestaurantSettings(
                id=1,
                restaurant_name="Grand Restaurant",
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
                waiter_max_discount_percentage=Decimal("0.00"),
            )
            db.add(settings)
            await db.flush()
        return settings

    @classmethod
    async def get_settings_response(cls, db: AsyncSession) -> RestaurantSettingsResponse:
        """Return schema representation of settings."""
        settings = await cls.get_settings(db)
        return RestaurantSettingsResponse.model_validate(settings)

    @classmethod
    async def update_settings(
        cls,
        db: AsyncSession,
        payload: RestaurantSettingsUpdate,
        admin_user: User,
    ) -> RestaurantSettingsResponse:
        """Update singleton restaurant configuration and record audit log."""
        settings = await cls.get_settings(db)

        update_dict = payload.model_dump(exclude_unset=True)
        # `allow_waiter_discount` has no database column; ignore it instead of crashing.
        update_dict.pop("allow_waiter_discount", None)
        if not update_dict:
            return RestaurantSettingsResponse.model_validate(settings)

        old_state = {k: getattr(settings, k) for k in update_dict}

        for field, value in update_dict.items():
            setattr(settings, field, value)

        await db.flush()

        # Audit configuration update
        await AuditService.record_event(
            db,
            action_type="RESTAURANT_SETTINGS_UPDATED",
            entity_type="RESTAURANT_SETTINGS",
            entity_id="1",
            actor_role=ActorRole.ADMIN,
            actor_user_id=admin_user.id,
            reason="Admin updated restaurant configuration",
            old_value={k: str(v) if isinstance(v, Decimal) else v for k, v in old_state.items()},
            new_value={k: str(v) if isinstance(v, Decimal) else v for k, v in update_dict.items()},
        )

        return RestaurantSettingsResponse.model_validate(settings)
