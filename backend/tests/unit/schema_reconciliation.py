"""Reconciliation of `docs/04` (canonical) against `docs/13` extras and prose-only columns.

Rule applied: `docs/04` is the base. A `docs/13` column is kept only when a documented business
or security requirement justifies it AND it is not redundant; otherwise it is omitted. Every
column in the models that is not in `docs/04`'s catalog/detail sections must appear in KEPT_*.
Every OMITTED entry must be absent from the models.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Reconciliation:
    table: str
    column: str
    source: str
    purpose: str
    decision: str  # KEEP | OMIT | UNRESOLVED


KEPT_EXTRAS = (
    Reconciliation(
        "users",
        "token_version",
        "docs/13 L635, L664, L880, L948",
        "Invalidate outstanding 15-min access JWTs on deactivation/password reset (security).",
        "KEEP",
    ),
    Reconciliation(
        "staff_refresh_tokens",
        "replaced_by_token_id",
        "docs/13 L636; docs/06 refresh rotation + reuse-attempt logging",
        "Rotation chain so a reused (already rotated) refresh token can be detected and audited.",
        "KEEP",
    ),
    Reconciliation(
        "restaurant_settings",
        "allow_waiter_cancel_preparing_item",
        "docs/13 Sec. 20.1 OD-03; docs/04 Sec. 23 requires OD-01..OD-08 switches",
        "Policy switch (docs/04 names only OD-01/02/05; docs/13 names the rest).",
        "KEEP",
    ),
    Reconciliation(
        "restaurant_settings",
        "allow_kitchen_mark_served",
        "docs/13 Sec. 20.1 OD-04; docs/04 Sec. 23",
        "Policy switch: may Kitchen move READY -> SERVED.",
        "KEEP",
    ),
    Reconciliation(
        "restaurant_settings",
        "limit_includes_estimated_tax",
        "docs/13 Sec. 20.1 OD-06; docs/04 Sec. 23",
        "Policy switch: whether the unpaid-exposure limit counts estimated tax.",
        "KEEP",
    ),
    Reconciliation(
        "restaurant_settings",
        "apply_outstanding_limit_to_waiter_orders",
        "docs/13 Sec. 20.1 OD-07; docs/04 Sec. 23",
        "Policy switch: whether waiter orders also count against the exposure limit.",
        "KEEP",
    ),
    Reconciliation(
        "restaurant_settings",
        "waiter_max_discount_percentage",
        "docs/13 Sec. 20.1 OD-08; docs/04 Sec. 23",
        "Policy value: max discount a waiter may apply without Admin approval.",
        "KEEP",
    ),
    Reconciliation(
        "restaurant_settings",
        "waiter_max_price_override_percentage",
        "Flexible Portions & Live Adjustments specification",
        "Policy value: max price override a waiter may apply without Admin approval.",
        "KEEP",
    ),
    Reconciliation(
        "menu_items",
        "extra_piece_price",
        "Flexible Portions & Extra Items specification",
        "Extra piece addon unit price configurable by admin.",
        "KEEP",
    ),
    Reconciliation(
        "menu_items",
        "pricing_type",
        "Menu Management Redesign specification",
        "Pricing type: FIXED or SEASONAL.",
        "KEEP",
    ),
    Reconciliation(
        "menu_items",
        "serving_description",
        "Menu Management Redesign specification",
        "Customer-facing serving description.",
        "KEEP",
    ),
    Reconciliation(
        "menu_items",
        "imagekit_file_id",
        "ImageKit CDN integration (migration 0010)",
        "ImageKit file ID stored for safe remote CDN deletion when admin replaces or removes a dish photo.",
        "KEEP",
    ),
    Reconciliation(
        "menu_price_variants",
        "is_portion",
        "Menu Management Redesign specification",
        "Whether variant represents a portion/pack.",
        "KEEP",
    ),
    Reconciliation(
        "menu_price_variants",
        "pricing_status",
        "Menu Management Redesign specification",
        "Pricing status: ACTIVE or SEASONAL_UNPRICED.",
        "KEEP",
    ),
    Reconciliation(
        "order_items",
        "base_price_snapshot",
        "Flexible Portions & Live Adjustments specification",
        "Preserves original standard menu price before any item adjustment.",
        "KEEP",
    ),
    Reconciliation(
        "order_items",
        "custom_portion_name",
        "Flexible Portions & Live Adjustments specification",
        "Custom portion label for the order line.",
        "KEEP",
    ),
    Reconciliation(
        "order_items",
        "extra_pieces_count",
        "Flexible Portions & Live Adjustments specification",
        "Number of extra pieces added to the item.",
        "KEEP",
    ),
    Reconciliation(
        "order_items",
        "extra_piece_price",
        "Flexible Portions & Live Adjustments specification",
        "Price charged per extra piece snapshot.",
        "KEEP",
    ),
    Reconciliation(
        "order_items",
        "adjustment_type",
        "Flexible Portions & Live Adjustments specification",
        "Type of live adjustment applied to the item.",
        "KEEP",
    ),
    Reconciliation(
        "order_items",
        "adjustment_amount",
        "Flexible Portions & Live Adjustments specification",
        "Adjustment amount snapshot.",
        "KEEP",
    ),
    Reconciliation(
        "order_items",
        "adjustment_reason",
        "Flexible Portions & Live Adjustments specification",
        "Mandatory explanation for adjustment.",
        "KEEP",
    ),
    Reconciliation(
        "order_items",
        "adjustment_applied_by_user_id",
        "Flexible Portions & Live Adjustments specification",
        "User who applied the adjustment.",
        "KEEP",
    ),
    Reconciliation(
        "order_items",
        "adjustment_approved_by_user_id",
        "Flexible Portions & Live Adjustments specification",
        "Admin user who approved the adjustment if exceeding waiter limit.",
        "KEEP",
    ),
    Reconciliation(
        "bill_items",
        "base_price_snapshot",
        "Flexible Portions & Live Adjustments specification",
        "Preserves original standard menu price on bill.",
        "KEEP",
    ),
    Reconciliation(
        "bill_items",
        "custom_portion_name",
        "Flexible Portions & Live Adjustments specification",
        "Custom portion label on bill.",
        "KEEP",
    ),
    Reconciliation(
        "bill_items",
        "extra_pieces_count",
        "Flexible Portions & Live Adjustments specification",
        "Extra pieces count on bill.",
        "KEEP",
    ),
    Reconciliation(
        "bill_items",
        "adjustment_type",
        "Flexible Portions & Live Adjustments specification",
        "Adjustment type on bill.",
        "KEEP",
    ),
    Reconciliation(
        "bill_items",
        "adjustment_amount",
        "Flexible Portions & Live Adjustments specification",
        "Adjustment amount on bill.",
        "KEEP",
    ),
    Reconciliation(
        "bill_items",
        "adjustment_reason",
        "Flexible Portions & Live Adjustments specification",
        "Adjustment reason on bill.",
        "KEEP",
    ),
    Reconciliation(
        "order_modification_events",
        "modified_by_customer_session_id",
        "Customer self-service order modifications",
        "Tracks customer session that modified the item.",
        "KEEP",
    ),
)

# Columns documented in docs/04 prose (not in its catalog/detail bullet lists).
PROSE_DOCUMENTED = {
    ("orders", "preparing_by_user_id"): "docs/04 Sec. 12.1 lifecycle actors",
    ("orders", "ready_by_user_id"): "docs/04 Sec. 12.1 lifecycle actors",
    ("orders", "served_by_user_id"): "docs/04 Sec. 12.1 lifecycle actors",
    ("orders", "accepted_by_user_id"): "docs/04 Sec. 12.1 lifecycle actors",
    ("orders", "rejected_by_user_id"): "docs/04 Sec. 12.1 lifecycle actors",
    ("orders", "cancelled_by_user_id"): "docs/04 Sec. 12.1 lifecycle actors",
    ("restaurant_settings", "allowed_payment_methods_json"): "docs/04 Sec. 23",
}

OMITTED = (
    Reconciliation(
        "bill_items",
        "quantity_value_snapshot",
        "docs/13 L649 only (docs/04 Sec. 17/catalog #15 omits it)",
        "Portion size on the receipt. Redundant: variant_name_snapshot + unit_snapshot are on the "
        "line and the immutable order_items row (order_item_id FK) holds quantity_value_snapshot.",
        "OMIT",
    ),
    Reconciliation(
        "staff_refresh_tokens",
        "ip_hash",
        "docs/13 L636 only",
        "No documented retention/privacy rule for IPs on refresh tokens; IP correlation is "
        "already served by audit_logs.ip_hash (daily-salted, docs/06 L434). Data minimization.",
        "OMIT",
    ),
    Reconciliation(
        "staff_refresh_tokens",
        "device_info",
        "docs/13 L636",
        "Duplicate of docs/04 `device_label`; docs/04 name is used.",
        "OMIT",
    ),
    Reconciliation(
        "restaurant_settings",
        "<rate-limit thresholds>",
        "docs/04 catalog #20 and Sec. 23 mention them; no document names or types them",
        "Cannot be created without inventing names/types; docs/06 Sec. 'Rate limits' holds the "
        "values (20 scans/min, 3 orders/60s, ...). Needs a decision before Phase 3.",
        "UNRESOLVED",
    ),
)
