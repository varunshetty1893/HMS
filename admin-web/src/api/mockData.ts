import {
  AdminDashboardKPIs,
  AuditLog,
  Bill,
  DailySalesSummary,
  MenuCategory,
  MenuItem,
  Order,
  OrderReportItem,
  Payment,
  RestaurantSettings,
  RestaurantTable,
  User,
} from '@/types/api';

// Persistent in-memory / localStorage store
const STORAGE_PREFIX = 'hms_mock_';

function getStored<T>(key: string, defaultValue: T): T {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key);
    return raw ? JSON.parse(raw) : defaultValue;
  } catch {
    return defaultValue;
  }
}

function setStored<T>(key: string, value: T): void {
  try {
    localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value));
  } catch {
    // ignore
  }
}

// 1. Initial Mock Data
export const INITIAL_USER: User = {
  id: 'usr-admin-1',
  username: 'admin',
  full_name: 'Varun Shetty (Administrator)',
  role: 'ADMIN',
  status: 'ACTIVE',
  is_active: true,
  failed_login_attempts: 0,
  locked_until: null,
  last_login_at: new Date().toISOString(),
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

export const INITIAL_SETTINGS: RestaurantSettings = {
  id: 1,
  restaurant_name: 'Spice Hub Family Restaurant',
  address: '142 MG Road, Indiranagar, Bengaluru, KA 560038',
  phone: '+91 98450 12345',
  gstin: '29AABCU9603R1ZX',
  logo_url: '/logo.png',
  currency_code: 'INR',
  currency_symbol: '₹',
  prices_include_tax: false,
  cgst_percentage: '2.50',
  sgst_percentage: '2.50',
  service_charge_percentage: '0.00',
  default_session_outstanding_limit: '5000.00',
  is_ordering_enabled: true,
  opening_time: '11:00',
  closing_time: '23:30',
  allow_multi_device_per_table: true,
  allow_customer_cancel_placed: true,
  allow_waiter_cancel_preparing_item: false,
  allow_kitchen_mark_served: true,
  kitchen_can_toggle_availability: true,
  limit_includes_estimated_tax: true,
  apply_outstanding_limit_to_waiter_orders: true,
  allow_waiter_discount: true,
  waiter_max_discount_percentage: '10.00',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

export const INITIAL_CATEGORIES: MenuCategory[] = [
  {
    id: 'cat-1',
    name: 'Starters & Tandoor',
    description: 'Fresh clay-oven skewers, tikkas and crispy appetizers',
    display_order: 1,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'cat-2',
    name: 'Main Course (Curries)',
    description: 'Slow-cooked rich gravies and traditional royal curries',
    display_order: 2,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'cat-3',
    name: 'Biryani & Rice',
    description: 'Fragrant aged Basmati dum biryanis and seasoned rice',
    display_order: 3,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'cat-4',
    name: 'Tandoori Breads & Roti',
    description: 'Freshly baked artisan naan, kulcha, and whole wheat rotis',
    display_order: 4,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
  {
    id: 'cat-5',
    name: 'Desserts & Beverages',
    description: 'Traditional sweets, chilled lassis, and refreshing coolers',
    display_order: 5,
    is_active: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

export const INITIAL_ITEMS: MenuItem[] = [
  {
    id: 'item-1',
    category_id: 'cat-1',
    item_code: 'APP01',
    name: 'Tandoori Paneer Tikka',
    description: 'Cottage cheese cubes marinated in spiced yogurt, capsicum & slow-roasted in clay tandoor.',
    dietary_type: 'VEG',
    spice_level: 'MEDIUM',
    image_url: 'https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?auto=format&fit=crop&w=600&q=80',
    is_available: true,
    is_active: true,
    display_order: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    variants: [
      {
        id: 'var-1',
        menu_item_id: 'item-1',
        variant_code: 'FULL',
        variant_name: 'Full Plate (6 pcs)',
        quantity_value: '6',
        unit: 'PIECE',
        price: '240.00',
        is_default: true,
        is_available: true,
        is_active: true,
        display_order: 1,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
  },
  {
    id: 'item-2',
    category_id: 'cat-1',
    item_code: 'APP02',
    name: 'Murgh Malai Kebab',
    description: 'Tender chicken chunks marinated in rich cream, cashew paste & aromatic green cardamom.',
    dietary_type: 'NON_VEG',
    spice_level: 'MILD',
    image_url: 'https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?auto=format&fit=crop&w=600&q=80',
    is_available: true,
    is_active: true,
    display_order: 2,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    variants: [
      {
        id: 'var-2',
        menu_item_id: 'item-2',
        variant_code: 'FULL',
        variant_name: 'Full Plate (6 pcs)',
        quantity_value: '6',
        unit: 'PIECE',
        price: '320.00',
        is_default: true,
        is_available: true,
        is_active: true,
        display_order: 1,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
  },
  {
    id: 'item-3',
    category_id: 'cat-2',
    item_code: 'MC01',
    name: 'Old Delhi Butter Chicken',
    description: 'Char-grilled chicken simmered in a velvety satin tomato, butter, and dried fenugreek sauce.',
    dietary_type: 'NON_VEG',
    spice_level: 'MILD',
    image_url: 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=600&q=80',
    is_available: true,
    is_active: true,
    display_order: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    variants: [
      {
        id: 'var-3-half',
        menu_item_id: 'item-3',
        variant_code: 'HALF',
        variant_name: 'Half Portion (2 pcs)',
        quantity_value: '2',
        unit: 'PORTION',
        price: '280.00',
        is_default: false,
        is_available: true,
        is_active: true,
        display_order: 1,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 'var-3-full',
        menu_item_id: 'item-3',
        variant_code: 'FULL',
        variant_name: 'Full Portion (4 pcs)',
        quantity_value: '4',
        unit: 'PORTION',
        price: '460.00',
        is_default: true,
        is_available: true,
        is_active: true,
        display_order: 2,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
  },
  {
    id: 'item-4',
    category_id: 'cat-2',
    item_code: 'MC02',
    name: 'Dal Makhani Bukhara',
    description: 'Black lentils slow simmered overnight over charcoal embers with churned butter and garlic.',
    dietary_type: 'VEG',
    spice_level: 'MILD',
    image_url: 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=600&q=80',
    is_available: true,
    is_active: true,
    display_order: 2,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    variants: [
      {
        id: 'var-4',
        menu_item_id: 'item-4',
        variant_code: 'PORTION',
        variant_name: 'Regular Bowl',
        quantity_value: '1',
        unit: 'PORTION',
        price: '260.00',
        is_default: true,
        is_available: true,
        is_active: true,
        display_order: 1,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
  },
  {
    id: 'item-5',
    category_id: 'cat-3',
    item_code: 'BR01',
    name: 'Hyderabadi Dum Chicken Biryani',
    description: 'Marinated chicken layered with fragrant saffron rice, fried onions & slow cooked in sealed pot.',
    dietary_type: 'NON_VEG',
    spice_level: 'SPICY',
    image_url: 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80',
    is_available: true,
    is_active: true,
    display_order: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    variants: [
      {
        id: 'var-5',
        menu_item_id: 'item-5',
        variant_code: 'REGULAR',
        variant_name: 'Pot Biryani (with Salan & Raita)',
        quantity_value: '1',
        unit: 'PORTION',
        price: '340.00',
        is_default: true,
        is_available: true,
        is_active: true,
        display_order: 1,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
  },
  {
    id: 'item-6',
    category_id: 'cat-4',
    item_code: 'RO01',
    name: 'Butter Garlic Naan',
    description: 'Refined flour bread cooked in tandoor, brushed with rich garlic butter and fresh coriander.',
    dietary_type: 'VEG',
    spice_level: 'NONE',
    image_url: 'https://images.unsplash.com/photo-1626777552726-4a6b54c97e46?auto=format&fit=crop&w=600&q=80',
    is_available: true,
    is_active: true,
    display_order: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    variants: [
      {
        id: 'var-6',
        menu_item_id: 'item-6',
        variant_code: 'PC',
        variant_name: '1 Piece',
        quantity_value: '1',
        unit: 'PIECE',
        price: '65.00',
        is_default: true,
        is_available: true,
        is_active: true,
        display_order: 1,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
  },
  {
    id: 'item-7',
    category_id: 'cat-5',
    item_code: 'DE01',
    name: 'Gulab Jamun with Rabri',
    description: 'Warm khoya dumplings soaked in saffron-rose syrup served with chilled thickened rabri.',
    dietary_type: 'VEG',
    spice_level: 'NONE',
    image_url: 'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80',
    is_available: true,
    is_active: true,
    display_order: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    variants: [
      {
        id: 'var-7',
        menu_item_id: 'item-7',
        variant_code: 'PORTION',
        variant_name: '2 pcs with Rabri',
        quantity_value: '2',
        unit: 'PORTION',
        price: '140.00',
        is_default: true,
        is_available: true,
        is_active: true,
        display_order: 1,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
  },
];

export const INITIAL_TABLES: RestaurantTable[] = [
  {
    id: 'tbl-1',
    table_number: 1,
    display_name: 'Table 1',
    seating_capacity: 4,
    floor_or_zone: 'Ground Floor (AC)',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 1,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'OCCUPIED',
    active_qr_version: 1,
    active_qr_prefix: 'T01',
    current_session_code: 'SES-01',
    current_outstanding_amount: '1240.00',
  },
  {
    id: 'tbl-2',
    table_number: 2,
    display_name: 'Table 2',
    seating_capacity: 2,
    floor_or_zone: 'Ground Floor (AC)',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 2,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'AVAILABLE',
    active_qr_version: 1,
    active_qr_prefix: 'T02',
    current_outstanding_amount: '0.00',
  },
  {
    id: 'tbl-3',
    table_number: 3,
    display_name: 'Table 3',
    seating_capacity: 6,
    floor_or_zone: 'Ground Floor (AC)',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 3,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'OCCUPIED',
    active_qr_version: 1,
    active_qr_prefix: 'T03',
    current_session_code: 'SES-03',
    current_outstanding_amount: '3450.00',
  },
  {
    id: 'tbl-4',
    table_number: 4,
    display_name: 'Table 4 (Window Side)',
    seating_capacity: 4,
    floor_or_zone: 'Window Section',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 4,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'OCCUPIED',
    active_qr_version: 2,
    active_qr_prefix: 'T04',
    current_session_code: 'SES-04',
    current_outstanding_amount: '890.00',
  },
  {
    id: 'tbl-5',
    table_number: 5,
    display_name: 'Table 5',
    seating_capacity: 4,
    floor_or_zone: 'Window Section',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 5,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'AVAILABLE',
    active_qr_version: 1,
    active_qr_prefix: 'T05',
    current_outstanding_amount: '0.00',
  },
  {
    id: 'tbl-6',
    table_number: 6,
    display_name: 'Table 6 (Balcony)',
    seating_capacity: 2,
    floor_or_zone: 'Balcony Outdoor',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 6,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'AVAILABLE',
    active_qr_version: 1,
    active_qr_prefix: 'T06',
    current_outstanding_amount: '0.00',
  },
  {
    id: 'tbl-7',
    table_number: 7,
    display_name: 'Table 7 (Balcony)',
    seating_capacity: 4,
    floor_or_zone: 'Balcony Outdoor',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 7,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'OCCUPIED',
    active_qr_version: 1,
    active_qr_prefix: 'T07',
    current_session_code: 'SES-07',
    current_outstanding_amount: '2180.00',
  },
  {
    id: 'tbl-8',
    table_number: 8,
    display_name: 'Table 8',
    seating_capacity: 8,
    floor_or_zone: 'Family Dining',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 8,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'AVAILABLE',
    active_qr_version: 1,
    active_qr_prefix: 'T08',
    current_outstanding_amount: '0.00',
  },
  {
    id: 'tbl-9',
    table_number: 9,
    display_name: 'Table 9',
    seating_capacity: 8,
    floor_or_zone: 'Family Dining',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 9,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'AVAILABLE',
    active_qr_version: 1,
    active_qr_prefix: 'T09',
    current_outstanding_amount: '0.00',
  },
  {
    id: 'tbl-10',
    table_number: 10,
    display_name: 'Table 10 (Private Suite)',
    seating_capacity: 6,
    floor_or_zone: 'Private Lounge',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 10,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'OCCUPIED',
    active_qr_version: 1,
    active_qr_prefix: 'T10',
    current_session_code: 'SES-10',
    current_outstanding_amount: '4820.00',
  },
  {
    id: 'tbl-11',
    table_number: 11,
    display_name: 'Table 11 (High Top)',
    seating_capacity: 2,
    floor_or_zone: 'Bar & Lounge',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 11,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'AVAILABLE',
    active_qr_version: 1,
    active_qr_prefix: 'T11',
    current_outstanding_amount: '0.00',
  },
  {
    id: 'tbl-12',
    table_number: 12,
    display_name: 'Table 12 (High Top)',
    seating_capacity: 2,
    floor_or_zone: 'Bar & Lounge',
    operational_status: 'ENABLED',
    is_active: true,
    display_order: 12,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    occupancy_status: 'AVAILABLE',
    active_qr_version: 1,
    active_qr_prefix: 'T12',
    current_outstanding_amount: '0.00',
  },
];

export const INITIAL_ORDERS: Order[] = [
  {
    id: 'ord-101',
    order_number: 'ORD-101',
    table_id: 'tbl-1',
    table_number: 1,
    table_session_id: 'SES-01',
    source: 'CUSTOMER_QR',
    status: 'PREPARING',
    order_subtotal: '1240.00',
    placed_at: new Date(Date.now() - 18 * 60000).toISOString(),
    accepted_at: new Date(Date.now() - 15 * 60000).toISOString(),
    preparing_at: new Date(Date.now() - 10 * 60000).toISOString(),
    ready_at: null,
    served_at: null,
    completed_at: null,
    cancelled_at: null,
    rejected_at: null,
    cancellation_reason: null,
    rejection_reason: null,
    version: 2,
    has_unacknowledged_mods: false,
    items: [
      {
        id: 'oi-101-1',
        order_id: 'ord-101',
        menu_price_variant_id: 'var-3-full',
        item_code: 'MC01',
        item_name: 'Old Delhi Butter Chicken',
        variant_name: 'Full Portion (4 pcs)',
        original_quantity: 2,
        active_quantity: 2,
        cancelled_quantity: 0,
        unit_price_snapshot: '460.00',
        line_subtotal: '920.00',
        item_notes: 'Boneless preferred',
      },
      {
        id: 'oi-101-2',
        order_id: 'ord-101',
        menu_price_variant_id: 'var-6',
        item_code: 'RO01',
        item_name: 'Butter Garlic Naan',
        variant_name: '1 Piece',
        original_quantity: 4,
        active_quantity: 4,
        cancelled_quantity: 0,
        unit_price_snapshot: '65.00',
        line_subtotal: '260.00',
        item_notes: 'Crispy',
      },
    ],
  },
  {
    id: 'ord-102',
    order_number: 'ORD-102',
    table_id: 'tbl-3',
    table_number: 3,
    table_session_id: 'SES-03',
    source: 'WAITER',
    status: 'READY',
    order_subtotal: '3450.00',
    placed_at: new Date(Date.now() - 25 * 60000).toISOString(),
    accepted_at: new Date(Date.now() - 22 * 60000).toISOString(),
    preparing_at: new Date(Date.now() - 16 * 60000).toISOString(),
    ready_at: new Date(Date.now() - 2 * 60000).toISOString(),
    served_at: null,
    completed_at: null,
    cancelled_at: null,
    rejected_at: null,
    cancellation_reason: null,
    rejection_reason: null,
    version: 3,
    has_unacknowledged_mods: false,
    items: [
      {
        id: 'oi-102-1',
        order_id: 'ord-102',
        menu_price_variant_id: 'var-1',
        item_code: 'APP01',
        item_name: 'Tandoori Paneer Tikka',
        variant_name: 'Full Plate (6 pcs)',
        original_quantity: 2,
        active_quantity: 2,
        cancelled_quantity: 0,
        unit_price_snapshot: '240.00',
        line_subtotal: '480.00',
        item_notes: null,
      },
      {
        id: 'oi-102-2',
        order_id: 'ord-102',
        menu_price_variant_id: 'var-4',
        item_code: 'MC02',
        item_name: 'Dal Makhani Bukhara',
        variant_name: 'Regular Bowl',
        original_quantity: 3,
        active_quantity: 3,
        cancelled_quantity: 0,
        unit_price_snapshot: '260.00',
        line_subtotal: '780.00',
        item_notes: null,
      },
    ],
  },
  {
    id: 'ord-103',
    order_number: 'ORD-103',
    table_id: 'tbl-4',
    table_number: 4,
    table_session_id: 'SES-04',
    source: 'CUSTOMER_QR',
    status: 'ACCEPTED',
    order_subtotal: '890.00',
    placed_at: new Date(Date.now() - 5 * 60000).toISOString(),
    accepted_at: new Date(Date.now() - 2 * 60000).toISOString(),
    preparing_at: null,
    ready_at: null,
    served_at: null,
    completed_at: null,
    cancelled_at: null,
    rejected_at: null,
    cancellation_reason: null,
    rejection_reason: null,
    version: 1,
    has_unacknowledged_mods: false,
    items: [
      {
        id: 'oi-103-1',
        order_id: 'ord-103',
        menu_price_variant_id: 'var-5',
        item_code: 'BR01',
        item_name: 'Hyderabadi Dum Chicken Biryani',
        variant_name: 'Pot Biryani',
        original_quantity: 2,
        active_quantity: 2,
        cancelled_quantity: 0,
        unit_price_snapshot: '340.00',
        line_subtotal: '680.00',
        item_notes: 'Extra spicy salan',
      },
    ],
  },
  {
    id: 'ord-104',
    order_number: 'ORD-104',
    table_id: 'tbl-7',
    table_number: 7,
    table_session_id: 'SES-07',
    source: 'WAITER',
    status: 'SERVED',
    order_subtotal: '2180.00',
    placed_at: new Date(Date.now() - 40 * 60000).toISOString(),
    accepted_at: new Date(Date.now() - 36 * 60000).toISOString(),
    preparing_at: new Date(Date.now() - 28 * 60000).toISOString(),
    ready_at: new Date(Date.now() - 14 * 60000).toISOString(),
    served_at: new Date(Date.now() - 8 * 60000).toISOString(),
    completed_at: null,
    cancelled_at: null,
    rejected_at: null,
    cancellation_reason: null,
    rejection_reason: null,
    version: 4,
    has_unacknowledged_mods: false,
    items: [
      {
        id: 'oi-104-1',
        order_id: 'ord-104',
        menu_price_variant_id: 'var-2',
        item_code: 'APP02',
        item_name: 'Murgh Malai Kebab',
        variant_name: 'Full Plate (6 pcs)',
        original_quantity: 2,
        active_quantity: 2,
        cancelled_quantity: 0,
        unit_price_snapshot: '320.00',
        line_subtotal: '640.00',
        item_notes: null,
      },
    ],
  },
];

export const INITIAL_BILLS: Bill[] = [
  {
    id: 'bill-1',
    bill_number: 'BILL-2026-001',
    table_session_id: 'SES-01',
    table_number: 1,
    status: 'ISSUED',
    subtotal_amount: '1180.00',
    discount_amount: '0.00',
    taxable_amount: '1180.00',
    cgst_percentage: '2.50',
    cgst_amount: '29.50',
    sgst_percentage: '2.50',
    sgst_amount: '29.50',
    service_charge_amount: '0.00',
    rounding_adjustment: '1.00',
    grand_total: '1240.00',
    discount_reason: null,
    generated_at: new Date(Date.now() - 15 * 60000).toISOString(),
    generated_by_name: 'Varun Shetty (Admin)',
    line_items: [],
    payments: [],
  },
  {
    id: 'bill-2',
    bill_number: 'BILL-2026-002',
    table_session_id: 'SES-03',
    table_number: 3,
    status: 'ISSUED',
    subtotal_amount: '3285.00',
    discount_amount: '0.00',
    taxable_amount: '3285.00',
    cgst_percentage: '2.50',
    cgst_amount: '82.13',
    sgst_percentage: '2.50',
    sgst_amount: '82.13',
    service_charge_amount: '0.00',
    rounding_adjustment: '0.74',
    grand_total: '3450.00',
    discount_reason: null,
    generated_at: new Date(Date.now() - 30 * 60000).toISOString(),
    generated_by_name: 'Varun Shetty (Admin)',
    line_items: [],
    payments: [],
  },
  {
    id: 'bill-3',
    bill_number: 'BILL-2026-003',
    table_session_id: 'SES-04',
    table_number: 4,
    status: 'ISSUED',
    subtotal_amount: '848.00',
    discount_amount: '0.00',
    taxable_amount: '848.00',
    cgst_percentage: '2.50',
    cgst_amount: '21.20',
    sgst_percentage: '2.50',
    sgst_amount: '21.20',
    service_charge_amount: '0.00',
    rounding_adjustment: '-0.40',
    grand_total: '890.00',
    discount_reason: null,
    generated_at: new Date(Date.now() - 5 * 60000).toISOString(),
    generated_by_name: 'Varun Shetty (Admin)',
    line_items: [],
    payments: [],
  },
  {
    id: 'bill-4',
    bill_number: 'BILL-2026-000',
    table_session_id: 'SES-02',
    table_number: 2,
    status: 'PAID',
    subtotal_amount: '209.52',
    discount_amount: '0.00',
    taxable_amount: '209.52',
    cgst_percentage: '2.50',
    cgst_amount: '5.24',
    sgst_percentage: '2.50',
    sgst_amount: '5.24',
    service_charge_amount: '0.00',
    rounding_adjustment: '0.00',
    grand_total: '220.00',
    discount_reason: null,
    generated_at: new Date(Date.now() - 60 * 60000).toISOString(),
    generated_by_name: 'Varun Shetty (Admin)',
    payments: [
      {
        id: 'pmt-1',
        bill_id: 'bill-4',
        payment_method: 'UPI',
        amount_paid: '220.00',
        status: 'COMPLETED',
        reference_number: 'UPI983421776510',
        recorded_by_name: 'Varun Shetty (Admin)',
        completed_at: new Date(Date.now() - 55 * 60000).toISOString(),
      },
    ],
  },
];

export const INITIAL_STAFF: User[] = [
  INITIAL_USER,
  {
    id: 'usr-waiter-1',
    username: 'rahul_waiter',
    full_name: 'Rahul Sharma',
    role: 'WAITER',
    status: 'ACTIVE',
    is_active: true,
    failed_login_attempts: 0,
    locked_until: null,
    last_login_at: new Date(Date.now() - 120 * 60000).toISOString(),
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  },
  {
    id: 'usr-waiter-2',
    username: 'priya_waiter',
    full_name: 'Priya Nair',
    role: 'WAITER',
    status: 'ACTIVE',
    is_active: true,
    failed_login_attempts: 0,
    locked_until: null,
    last_login_at: new Date(Date.now() - 60 * 60000).toISOString(),
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  },
  {
    id: 'usr-kitchen-1',
    username: 'chef_anand',
    full_name: 'Chef Anand Kumar (Head Chef)',
    role: 'KITCHEN',
    status: 'ACTIVE',
    is_active: true,
    failed_login_attempts: 0,
    locked_until: null,
    last_login_at: new Date(Date.now() - 180 * 60000).toISOString(),
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  },
  {
    id: 'usr-kitchen-2',
    username: 'chef_vikram',
    full_name: 'Chef Vikram Singh',
    role: 'KITCHEN',
    status: 'ACTIVE',
    is_active: true,
    failed_login_attempts: 0,
    locked_until: null,
    last_login_at: new Date(Date.now() - 240 * 60000).toISOString(),
    created_at: '2026-01-02T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
  },
];

export const INITIAL_AUDIT_LOGS: AuditLog[] = [
  {
    id: 'aud-1',
    actor_user_id: 'usr-admin-1',
    actor_customer_session_id: null,
    actor_role: 'ADMIN',
    action_type: 'AUTH_LOGIN',
    entity_type: 'USER',
    entity_id: 'usr-admin-1',
    reason: 'Successful Admin Portal login',
    old_value_json: null,
    new_value_json: { ip: '127.0.0.1', user: 'admin' },
    metadata_json: {},
    ip_hash: 'sha256-local',
    created_at: new Date(Date.now() - 5 * 60000).toISOString(),
  },
  {
    id: 'aud-2',
    actor_user_id: 'usr-admin-1',
    actor_customer_session_id: null,
    actor_role: 'ADMIN',
    action_type: 'QR_REGENERATED',
    entity_type: 'RESTAURANT_TABLE',
    entity_id: 'tbl-4',
    reason: 'Periodic security rotation',
    old_value_json: { version: 1 },
    new_value_json: { version: 2 },
    metadata_json: {},
    ip_hash: 'sha256-local',
    created_at: new Date(Date.now() - 30 * 60000).toISOString(),
  },
  {
    id: 'aud-3',
    actor_user_id: 'usr-waiter-1',
    actor_customer_session_id: null,
    actor_role: 'WAITER',
    action_type: 'ORDER_PLACED',
    entity_type: 'ORDER',
    entity_id: 'ord-102',
    reason: 'Waiter floor order entry',
    old_value_json: null,
    new_value_json: { table_number: 3, total: '3450.00' },
    metadata_json: {},
    ip_hash: 'sha256-local',
    created_at: new Date(Date.now() - 25 * 60000).toISOString(),
  },
];

// Helper mock store getters & mutators
export function getMockCategories(): MenuCategory[] {
  return getStored('categories', INITIAL_CATEGORIES);
}

export function saveMockCategory(cat: MenuCategory): void {
  const list = getMockCategories();
  const idx = list.findIndex((c) => c.id === cat.id);
  if (idx >= 0) list[idx] = cat;
  else list.push(cat);
  setStored('categories', list);
}

export function getMockItems(): MenuItem[] {
  return getStored('items', INITIAL_ITEMS);
}

export function saveMockItem(item: MenuItem): void {
  const list = getMockItems();
  const idx = list.findIndex((i) => i.id === item.id);
  if (idx >= 0) list[idx] = item;
  else list.push(item);
  setStored('items', list);
}

export function getMockTables(): RestaurantTable[] {
  return getStored('tables', INITIAL_TABLES);
}

export function saveMockTable(tbl: RestaurantTable): void {
  const list = getMockTables();
  const idx = list.findIndex((t) => t.id === tbl.id);
  if (idx >= 0) list[idx] = tbl;
  else list.push(tbl);
  setStored('tables', list);
}

export function getMockOrders(): Order[] {
  return getStored('orders', INITIAL_ORDERS);
}

export function saveMockOrder(ord: Order): void {
  const list = getMockOrders();
  const idx = list.findIndex((o) => o.id === ord.id);
  if (idx >= 0) list[idx] = ord;
  else list.push(ord);
  setStored('orders', list);
}

export function getMockBills(): Bill[] {
  return getStored('bills', INITIAL_BILLS);
}

export function saveMockBill(b: Bill): void {
  const list = getMockBills();
  const idx = list.findIndex((item) => item.id === b.id);
  if (idx >= 0) list[idx] = b;
  else list.push(b);
  setStored('bills', list);
}

export function getMockStaff(): User[] {
  return getStored('staff', INITIAL_STAFF);
}

export function saveMockStaff(u: User): void {
  const list = getMockStaff();
  const idx = list.findIndex((item) => item.id === u.id);
  if (idx >= 0) list[idx] = u;
  else list.push(u);
  setStored('staff', list);
}

export function getMockSettings(): RestaurantSettings {
  return getStored('settings', INITIAL_SETTINGS);
}

export function saveMockSettings(s: RestaurantSettings): void {
  setStored('settings', s);
}

export function getMockAuditLogs(): AuditLog[] {
  return getStored('audit_logs', INITIAL_AUDIT_LOGS);
}

export function getMockKPIs(): AdminDashboardKPIs {
  const orders = getMockOrders();
  const tables = getMockTables();
  const occupied = tables.filter((t) => t.occupancy_status === 'OCCUPIED').length;
  const activeOrders = orders.filter((o) => ['PLACED', 'ACCEPTED', 'PREPARING', 'READY'].includes(o.status)).length;

  const ordersByStatus: Record<string, number> = {};
  orders.forEach((o) => {
    ordersByStatus[o.status] = (ordersByStatus[o.status] || 0) + 1;
  });

  return {
    today_revenue: '48650.00',
    active_occupied_tables: occupied,
    total_tables: tables.length,
    active_orders_count: activeOrders,
    orders_by_status: ordersByStatus,
    unpaid_bills_count: 3,
    unpaid_exposure_amount: '5580.00',
    recent_rejections_cancellations: 0,
  };
}

export function getMockDailySales(): DailySalesSummary[] {
  return [
    {
      date: '2026-10-11',
      gross_subtotal: '49200.00',
      total_discounts: '550.00',
      cgst_amount: '1216.25',
      sgst_amount: '1216.25',
      net_collected_revenue: '51082.50',
      total_bills: 28,
      total_orders: 42,
      completed_sessions: 26,
      average_bill_value: '1824.38',
    },
    {
      date: '2026-10-10',
      gross_subtotal: '62400.00',
      total_discounts: '800.00',
      cgst_amount: '1540.00',
      sgst_amount: '1540.00',
      net_collected_revenue: '64680.00',
      total_bills: 36,
      total_orders: 54,
      completed_sessions: 34,
      average_bill_value: '1796.67',
    },
    {
      date: '2026-10-09',
      gross_subtotal: '38900.00',
      total_discounts: '320.00',
      cgst_amount: '964.50',
      sgst_amount: '964.50',
      net_collected_revenue: '40509.00',
      total_bills: 22,
      total_orders: 31,
      completed_sessions: 21,
      average_bill_value: '1841.32',
    },
  ];
}
