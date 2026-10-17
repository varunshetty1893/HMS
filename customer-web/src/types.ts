// ─────────────────────────────────────────────────────────────────────────────
// API Types — mirrors backend Pydantic schemas exactly
// ─────────────────────────────────────────────────────────────────────────────

export interface MenuPriceVariant {
  id: string;
  variant_code: string | null;
  variant_name: string;
  /** Older servers omit this; treat absence as one fixed price. */
  is_portion?: boolean;
  quantity_value: string;
  unit: string;
  price: string | null; // Decimal as string, null if seasonal unpriced
  pricing_status?: 'ACTIVE' | 'SEASONAL_UNPRICED';
  is_default: boolean;
  is_available: boolean;
}

export interface MenuItem {
  id: string;
  item_code: string;
  name: string;
  description: string | null;
  serving_description?: string | null;
  dietary_type: 'VEG' | 'NON_VEG' | 'EGG' | null;
  spice_level: 'MILD' | 'MEDIUM' | 'HOT' | null;
  pricing_type?: 'FIXED' | 'SEASONAL';
  image_url: string | null;
  is_available: boolean;
  display_order: number;
  variants: MenuPriceVariant[];
}

export interface MenuCategory {
  id: string;
  name: string;
  description: string | null;
  display_order: number;
  items: MenuItem[];
}

export interface CustomerMenuResponse {
  categories: MenuCategory[];
  total_items?: number;
  /** Most-ordered in-stock dishes (best first, max 6). Empty until orders exist. */
  popular_item_ids?: string[];
}

export interface CustomerSession {
  session_id: string;
  table_id: string;
  table_number: number;
  table_display_name: string;
  table_status: string;
  table_session_id?: string | null;
  current_outstanding_amount?: string;
  custom_outstanding_limit?: string;
  status: string;
  expires_at: string;
}

export interface OrderItemCreate {
  variant_id: string;
  quantity: number;
  item_notes?: string | null;
}

export interface OrderCreate {
  items: OrderItemCreate[];
  special_instructions?: string | null;
}

export interface OrderItemResponse {
  id: string;
  order_id: string;
  menu_item_id: string;
  menu_price_variant_id: string;
  item_code_snapshot: string;
  item_name_snapshot: string;
  variant_code_snapshot: string | null;
  variant_name_snapshot: string;
  quantity_value_snapshot: string;
  unit_snapshot: string;
  unit_price_snapshot: string;
  tax_rate_snapshot: string;
  original_quantity: number;
  active_quantity: number;
  cancelled_quantity: number;
  line_subtotal: string;
  item_status: string;
  item_notes: string | null;
}

export interface OrderResponse {
  id: string;
  order_number: string;
  table_session_id: string;
  table_id: string;
  source: string;
  customer_session_id: string | null;
  status: string;
  order_subtotal: string;
  special_instructions: string | null;
  is_first_qr_order_of_session: boolean;
  version: number;
  placed_at: string;
  accepted_at: string | null;
  ready_at: string | null;
  served_at: string | null;
  // set when status === 'CANCELLED'
  cancelled_at?: string | null;
  cancelled_by_role?: string | null;
  cancellation_reason?: string | null;
  items: OrderItemResponse[];
}

/**
 * One edit to a line of an existing order. Exactly one mode per line:
 *  - quantity mode: `new_quantity` (absolute; 0 removes the line)
 *  - portion mode : `switch_to_variant_id` (+ `switch_quantity`) -> cheaper variant of same dish
 */
export interface CustomerItemChange {
  order_item_id: string;
  new_quantity?: number;
  switch_to_variant_id?: string;
  switch_quantity?: number;
}

export interface TableSessionInfo {
  session_id: string;
  session_code: string;
  status: string;
  current_outstanding_amount: string;
  custom_outstanding_limit: string;
  is_first_order: boolean;
}

export interface OrderCreateResponse {
  order: OrderResponse;
  table_session: TableSessionInfo;
  is_replay: boolean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Cart types (client-only)
// ─────────────────────────────────────────────────────────────────────────────

export interface CartItem {
  variantId: string;
  menuItemId: string;
  itemName: string;
  variantName: string;
  price: number; // display only; server computes authoritative price
  quantity: number;
  itemNotes?: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// Waiter Request types
// ─────────────────────────────────────────────────────────────────────────────

export type WaiterRequestReason = 'ASSISTANCE' | 'CUTLERY' | 'WATER' | 'OTHER';
export type WaiterRequestStatus = 'PENDING' | 'CLAIMED' | 'COMPLETED' | 'CANCELLED' | 'EXPIRED';

export interface WaiterRequest {
  id: string;
  customer_session_id: string;
  table_session_id: string;
  table_id: string;
  reason: WaiterRequestReason;
  notes: string | null;
  status: WaiterRequestStatus;
  claimed_by_user_id: string | null;
  claimed_at: string | null;
  completed_at: string | null;
  completed_by_user_id: string | null;
  cancelled_at: string | null;
  expires_at: string;
  created_at: string;
}
