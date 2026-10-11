/**
 * Canonical TypeScript types for Admin Web Dashboard.
 * Matches backend Pydantic schemas and database models.
 */

export type UserRole = 'ADMIN' | 'WAITER' | 'KITCHEN';
export type UserStatus = 'ACTIVE' | 'LOCKED' | 'DISABLED';

export interface User {
  id: string;
  username: string;
  full_name: string;
  role: UserRole;
  status: UserStatus;
  is_active: boolean;
  failed_login_attempts: number;
  locked_until: string | null;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in_seconds: number;
  user: User;
}

export type DietaryType = 'VEG' | 'NON_VEG' | 'EGG';
export type SpiceLevel = 'NONE' | 'MILD' | 'MEDIUM' | 'SPICY' | 'EXTRA_SPICY';
export type PriceUnit = 'PORTION' | 'PIECE' | 'ML' | 'GRAM';

export interface MenuCategory {
  id: string;
  name: string;
  description: string | null;
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MenuPriceVariant {
  id: string;
  menu_item_id: string;
  variant_code: string;
  variant_name: string;
  quantity_value: string;
  unit: PriceUnit;
  price: string;
  is_default: boolean;
  is_available: boolean;
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface MenuItem {
  id: string;
  category_id: string;
  item_code: string;
  name: string;
  description: string | null;
  dietary_type: DietaryType;
  spice_level: SpiceLevel;
  image_url: string | null;
  is_available: boolean;
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
  variants: MenuPriceVariant[];
  category?: MenuCategory;
}

export type TableOperationalStatus = 'ENABLED' | 'MAINTENANCE' | 'DISABLED';
export type TableOccupancyStatus = 'AVAILABLE' | 'OCCUPIED';

export interface RestaurantTable {
  id: string;
  table_number: number;
  display_name: string;
  seating_capacity: number | null;
  floor_or_zone: string | null;
  operational_status: TableOperationalStatus;
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
  occupancy_status?: TableOccupancyStatus;
  active_qr_version?: number;
  active_qr_prefix?: string;
  current_session_code?: string;
  current_outstanding_amount?: string;
}

export interface QrPrintCardResponse {
  table_id: string;
  table_number: number;
  display_name: string;
  token_version: number;
  token_prefix: string;
  printable_qr_url: string;
  ordering_url: string;
  restaurant_name: string;
}

export interface QrRegenerateResponse {
  table_id: string;
  table_number: number;
  token_version: number;
  token_prefix: string;
  printable_qr_url: string;
  activated_at: string;
}

export type OrderStatus =
  | 'PLACED'
  | 'ACCEPTED'
  | 'PREPARING'
  | 'READY'
  | 'SERVED'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'REJECTED';

export interface OrderItem {
  id: string;
  order_id: string;
  menu_price_variant_id: string;
  item_code: string;
  item_name: string;
  variant_name: string;
  original_quantity: number;
  active_quantity: number;
  cancelled_quantity: number;
  unit_price_snapshot: string;
  line_subtotal: string;
  item_notes: string | null;
}

export interface OrderModificationEvent {
  id: string;
  order_id: string;
  order_item_id: string | null;
  modification_type: string;
  previous_quantity: number;
  new_quantity: number;
  reason: string;
  modified_by_role: string;
  created_at: string;
}

export interface Order {
  id: string;
  order_number: string;
  table_id: string;
  table_session_id: string;
  source: 'CUSTOMER_QR' | 'WAITER';
  status: OrderStatus;
  order_subtotal: string;
  placed_at: string;
  accepted_at: string | null;
  preparing_at: string | null;
  ready_at: string | null;
  served_at: string | null;
  completed_at: string | null;
  cancelled_at: string | null;
  rejected_at: string | null;
  cancellation_reason: string | null;
  rejection_reason: string | null;
  version: number;
  has_unacknowledged_mods: boolean;
  table_number?: number;
  items?: OrderItem[];
  modification_events?: OrderModificationEvent[];
}

export type BillStatus = 'ISSUED' | 'PAID' | 'VOIDED_FOR_REVISION';
export type PaymentMethod = 'CASH' | 'UPI' | 'CARD' | 'OTHER';

export interface BillItem {
  id: string;
  bill_id: string;
  order_id: string;
  item_code: string;
  item_name: string;
  variant_name: string;
  quantity_billed: number;
  unit_price_snapshot: string;
  line_total: string;
}

export interface Payment {
  id: string;
  bill_id: string;
  payment_method: PaymentMethod;
  amount_paid: string;
  status: 'COMPLETED' | 'FAILED';
  reference_number: string | null;
  recorded_by_name?: string;
  completed_at: string;
}

export interface Bill {
  id: string;
  bill_number: string;
  table_session_id: string;
  status: BillStatus;
  subtotal_amount: string;
  discount_amount: string;
  taxable_amount: string;
  cgst_percentage: string;
  cgst_amount: string;
  sgst_percentage: string;
  sgst_amount: string;
  service_charge_amount: string;
  rounding_adjustment: string;
  grand_total: string;
  discount_reason: string | null;
  generated_at: string;
  generated_by_name?: string;
  table_number?: number;
  line_items?: BillItem[];
  payments?: Payment[];
}

export interface RestaurantSettings {
  id: number;
  restaurant_name: string;
  address: string | null;
  phone: string | null;
  gstin: string | null;
  logo_url: string | null;
  currency_code: string;
  currency_symbol: string;
  prices_include_tax: boolean;
  cgst_percentage: string;
  sgst_percentage: string;
  service_charge_percentage: string;
  default_session_outstanding_limit: string;
  is_ordering_enabled: boolean;
  opening_time: string | null;
  closing_time: string | null;
  allow_multi_device_per_table: boolean;
  allow_customer_cancel_placed: boolean;
  allow_waiter_cancel_preparing_item: boolean;
  allow_kitchen_mark_served: boolean;
  kitchen_can_toggle_availability: boolean;
  limit_includes_estimated_tax: boolean;
  apply_outstanding_limit_to_waiter_orders: boolean;
  allow_waiter_discount: boolean;
  waiter_max_discount_percentage: string;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: string;
  actor_user_id: string | null;
  actor_customer_session_id: string | null;
  actor_role: string;
  action_type: string;
  entity_type: string;
  entity_id: string;
  reason: string | null;
  old_value_json: any;
  new_value_json: any;
  metadata_json: any;
  ip_hash: string | null;
  created_at: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface AuditLogPageResponse {
  items: AuditLog[];
  pagination: PaginationMeta;
}

export interface AdminDashboardKPIs {
  today_revenue: string;
  active_occupied_tables: number;
  total_tables: number;
  active_orders_count: number;
  orders_by_status: Record<string, number>;
  unpaid_bills_count: number;
  unpaid_exposure_amount: string;
  recent_rejections_cancellations: number;
}

export interface DailySalesSummary {
  date: string;
  gross_subtotal: string;
  total_discounts: string;
  cgst_amount: string;
  sgst_amount: string;
  net_collected_revenue: string;
  total_bills: number;
  total_orders: number;
  completed_sessions: number;
  average_bill_value: string;
}

export interface OrderReportItem {
  order_id: string;
  order_number: string;
  table_number: number;
  source: string;
  status: string;
  placed_at: string;
  completed_at: string | null;
  order_subtotal: string;
  item_count: number;
}

export interface PopularDishReportItem {
  menu_item_id: string;
  item_code: string;
  item_name: string;
  variant_name: string;
  quantity_billed: number;
  gross_revenue: string;
}

export interface RevenueTimeSeriesItem {
  bucket_label: string;
  revenue: string;
  order_count: number;
  bill_count: number;
}

export interface PaymentMethodReportItem {
  payment_method: string;
  transaction_count: number;
  total_amount: string;
}

export interface TableUsageReportItem {
  table_id: string;
  table_number: number;
  display_name: string;
  session_count: number;
  total_revenue: string;
  average_session_minutes: string;
}

export interface OrderStatusReportItem {
  status: string;
  count: number;
  avg_duration_minutes: string | null;
}

export interface UnavailableDishReportItem {
  item_id: string;
  item_code: string;
  name: string;
  category_name: string;
  is_available: boolean;
  updated_at: string;
}

export interface CancelledRejectedReportItem {
  order_id: string;
  order_number: string;
  table_number: number;
  status: string;
  reason: string | null;
  actor_role: string | null;
  occurred_at: string;
  order_subtotal: string;
}

export interface WaiterActivityReportItem {
  user_id: string;
  username: string;
  full_name: string;
  orders_placed: number;
  items_served: number;
  bills_generated: number;
  payments_recorded: number;
}

export interface KitchenActivityReportItem {
  user_id: string;
  username: string;
  full_name: string;
  orders_accepted: number;
  orders_rejected: number;
  orders_ready: number;
  avg_prep_minutes: string | null;
}
