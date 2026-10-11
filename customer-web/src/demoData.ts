import type { CustomerMenuResponse, CustomerSession, OrderResponse, OrderCreate, OrderCreateResponse } from './types';

export const DEMO_SESSION: CustomerSession = {
  session_id: 'demo-session-4',
  table_id: 'table-demo-4',
  table_number: 4,
  table_display_name: 'Table 4 (Window Side)',
  table_status: 'OCCUPIED',
  status: 'ACTIVE',
  expires_at: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
};

export const DEMO_MENU: CustomerMenuResponse = {
  total_items: 12,
  categories: [
    {
      id: 'cat-starters',
      name: 'Starters & Appetizers',
      description: 'Tandoori sizzlers and freshly tossed crunch',
      display_order: 1,
      items: [
        {
          id: 'item-paneer-tikka',
          item_code: 'APP01',
          name: 'Tandoori Paneer Tikka',
          description: 'Cottage cheese cubes marinated in spiced yogurt and roasted in tandoor.',
          dietary_type: 'VEG',
          spice_level: 'MEDIUM',
          image_url: null,
          is_available: true,
          display_order: 1,
          variants: [
            {
              id: 'var-pt-full',
              variant_code: 'FULL',
              variant_name: 'Regular Portion',
              quantity_value: '6',
              unit: 'pcs',
              price: '240.00',
              is_default: true,
              is_available: true,
            },
          ],
        },
        {
          id: 'item-malai-kebab',
          item_code: 'APP02',
          name: 'Murgh Malai Kebab',
          description: 'Tender chicken boneless chunks marinated in rich cream, cashew paste, and aromatic green cardamom.',
          dietary_type: 'NON_VEG',
          spice_level: 'MILD',
          image_url: null,
          is_available: true,
          display_order: 2,
          variants: [
            {
              id: 'var-mmk-full',
              variant_code: 'FULL',
              variant_name: 'Full Plate',
              quantity_value: '6',
              unit: 'pcs',
              price: '320.00',
              is_default: true,
              is_available: true,
            },
          ],
        },
        {
          id: 'item-crispy-corn',
          item_code: 'APP03',
          name: 'Crispy Chilli Babycorn',
          description: 'Golden fried crispy babycorn tossed with spring onions, bell peppers, and oriental spices.',
          dietary_type: 'VEG',
          spice_level: 'HOT',
          image_url: null,
          is_available: true,
          display_order: 3,
          variants: [
            {
              id: 'var-ccb-full',
              variant_code: 'FULL',
              variant_name: 'Regular Portion',
              quantity_value: '1',
              unit: 'plate',
              price: '210.00',
              is_default: true,
              is_available: true,
            },
          ],
        },
        {
          id: 'item-egg-bhurji',
          item_code: 'APP04',
          name: 'Desi Masala Egg Bhurji',
          description: 'Farm fresh eggs scrambled with chopped onions, tomatoes, green chillies, and fresh coriander.',
          dietary_type: 'EGG',
          spice_level: 'MEDIUM',
          image_url: null,
          is_available: true,
          display_order: 4,
          variants: [
            {
              id: 'var-eb-full',
              variant_code: 'FULL',
              variant_name: 'Regular (3 Eggs)',
              quantity_value: '1',
              unit: 'portion',
              price: '160.00',
              is_default: true,
              is_available: true,
            },
          ],
        },
      ],
    },
    {
      id: 'cat-mains',
      name: 'Main Course',
      description: 'Slow-cooked rich gravies and house specialities',
      display_order: 2,
      items: [
        {
          id: 'item-butter-chicken',
          item_code: 'MC01',
          name: 'Old Delhi Butter Chicken',
          description: 'Smoked tandoori chicken simmered in a velvety tomato and butter gravy finished with kasoori methi.',
          dietary_type: 'NON_VEG',
          spice_level: 'MEDIUM',
          image_url: null,
          is_available: true,
          display_order: 1,
          variants: [
            {
              id: 'var-bc-half',
              variant_code: 'HALF',
              variant_name: 'Half (2 pcs)',
              quantity_value: '2',
              unit: 'pcs',
              price: '280.00',
              is_default: true,
              is_available: true,
            },
            {
              id: 'var-bc-full',
              variant_code: 'FULL',
              variant_name: 'Full (4 pcs)',
              quantity_value: '4',
              unit: 'pcs',
              price: '480.00',
              is_default: false,
              is_available: true,
            },
          ],
        },
        {
          id: 'item-paneer-butter-masala',
          item_code: 'MC02',
          name: 'Paneer Butter Masala',
          description: 'Fresh malai paneer simmered in a rich tomato, butter, and cashew nut gravy.',
          dietary_type: 'VEG',
          spice_level: 'MILD',
          image_url: null,
          is_available: true,
          display_order: 2,
          variants: [
            {
              id: 'var-pbm-half',
              variant_code: 'HALF',
              variant_name: 'Half Portion',
              quantity_value: '1',
              unit: 'portion',
              price: '220.00',
              is_default: true,
              is_available: true,
            },
            {
              id: 'var-pbm-full',
              variant_code: 'FULL',
              variant_name: 'Full Portion',
              quantity_value: '2',
              unit: 'portion',
              price: '380.00',
              is_default: false,
              is_available: true,
            },
          ],
        },
        {
          id: 'item-dal-makhani',
          item_code: 'MC03',
          name: 'Dal Makhani Dal Bukhara',
          description: 'Whole black lentils slow-cooked overnight with white butter, cream, and gentle spices.',
          dietary_type: 'VEG',
          spice_level: 'MILD',
          image_url: null,
          is_available: true,
          display_order: 3,
          variants: [
            {
              id: 'var-dm-full',
              variant_code: 'FULL',
              variant_name: 'Regular Bowl',
              quantity_value: '1',
              unit: 'portion',
              price: '240.00',
              is_default: true,
              is_available: true,
            },
          ],
        },
      ],
    },
    {
      id: 'cat-breads-rice',
      name: 'Biryani & Breads',
      description: 'Fragrant basmati rice dum biryanis and clay oven breads',
      display_order: 3,
      items: [
        {
          id: 'item-chicken-biryani',
          item_code: 'BR01',
          name: 'Hyderabadi Chicken Dum Biryani',
          description: 'Long grain basmati rice and marinated chicken cooked under dum with saffron, mint, and fried onions.',
          dietary_type: 'NON_VEG',
          spice_level: 'MEDIUM',
          image_url: null,
          is_available: true,
          display_order: 1,
          variants: [
            {
              id: 'var-cb-half',
              variant_code: 'HALF',
              variant_name: 'Single / Half',
              quantity_value: '1',
              unit: 'portion',
              price: '230.00',
              is_default: true,
              is_available: true,
            },
            {
              id: 'var-cb-full',
              variant_code: 'FULL',
              variant_name: 'Full Pot (Serves 2)',
              quantity_value: '2',
              unit: 'portion',
              price: '390.00',
              is_default: false,
              is_available: true,
            },
          ],
        },
        {
          id: 'item-garlic-naan',
          item_code: 'BR02',
          name: 'Garlic Butter Naan',
          description: 'Refined flour flatbread topped with minced garlic, fresh coriander, and melted butter.',
          dietary_type: 'VEG',
          spice_level: 'MILD',
          image_url: null,
          is_available: true,
          display_order: 2,
          variants: [
            {
              id: 'var-gn-single',
              variant_code: '1PC',
              variant_name: '1 Piece',
              quantity_value: '1',
              unit: 'pc',
              price: '65.00',
              is_default: true,
              is_available: true,
            },
          ],
        },
      ],
    },
    {
      id: 'cat-beverages',
      name: 'Beverages & Desserts',
      description: 'Traditional cooling sips and sweet indulgences',
      display_order: 4,
      items: [
        {
          id: 'item-mango-lassi',
          item_code: 'BV01',
          name: 'Alphonso Mango Lassi',
          description: 'Thick churned creamy yogurt blended with sweet Ratnagiri Alphonso mango pulp.',
          dietary_type: 'VEG',
          spice_level: null,
          image_url: null,
          is_available: true,
          display_order: 1,
          variants: [
            {
              id: 'var-ml-glass',
              variant_code: '300ML',
              variant_name: 'Tall Glass (300ml)',
              quantity_value: '300',
              unit: 'ml',
              price: '95.00',
              is_default: true,
              is_available: true,
            },
          ],
        },
        {
          id: 'item-fresh-lime',
          item_code: 'BV02',
          name: 'Fresh Lime Soda (Sweet & Salt)',
          description: 'Freshly squeezed lime juice with club soda, black salt, and roasted cumin.',
          dietary_type: 'VEG',
          spice_level: null,
          image_url: null,
          is_available: true,
          display_order: 2,
          variants: [
            {
              id: 'var-fls-glass',
              variant_code: '300ML',
              variant_name: 'Glass',
              quantity_value: '300',
              unit: 'ml',
              price: '60.00',
              is_default: true,
              is_available: true,
            },
          ],
        },
        {
          id: 'item-gulab-jamun',
          item_code: 'DS01',
          name: 'Gulab Jamun with Rabdi',
          description: 'Warm khoya dumplings steeped in rose cardamom syrup, served with chilled creamy rabdi.',
          dietary_type: 'VEG',
          spice_level: null,
          image_url: null,
          is_available: true,
          display_order: 3,
          variants: [
            {
              id: 'var-gj-portion',
              variant_code: '2PCS',
              variant_name: '2 Pieces with Rabdi',
              quantity_value: '2',
              unit: 'pcs',
              price: '120.00',
              is_default: true,
              is_available: true,
            },
          ],
        },
      ],
    },
  ],
};

let _demoOrders: OrderResponse[] = [];

export function getDemoOrders(): OrderResponse[] {
  const stored = sessionStorage.getItem('hms_demo_orders');
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      // fallback
    }
  }
  return _demoOrders;
}

export function saveDemoOrder(payload: OrderCreate): OrderCreateResponse {
  const currentOrders = getDemoOrders();
  const orderNum = `#ORD-${1000 + currentOrders.length + 1}`;
  const now = new Date().toISOString();

  let subtotal = 0;
  const items = payload.items.map((it, idx) => {
    // Find variant from menu
    let variantName = 'Regular';
    let unitPrice = '200.00';
    let itemName = 'Special Dish';
    let itemCode = 'DISH';

    for (const cat of DEMO_MENU.categories) {
      for (const menuItem of cat.items) {
        const v = menuItem.variants.find((vr) => vr.id === it.variant_id);
        if (v) {
          variantName = v.variant_name;
          unitPrice = v.price;
          itemName = menuItem.name;
          itemCode = menuItem.item_code;
          break;
        }
      }
    }

    const lineTotal = (parseFloat(unitPrice) * it.quantity).toFixed(2);
    subtotal += parseFloat(lineTotal);

    return {
      id: `demo-item-${Date.now()}-${idx}`,
      order_id: `demo-order-${Date.now()}`,
      menu_item_id: 'demo-menu-item',
      menu_price_variant_id: it.variant_id,
      item_code_snapshot: itemCode,
      item_name_snapshot: itemName,
      variant_code_snapshot: null,
      variant_name_snapshot: variantName,
      quantity_value_snapshot: '1',
      unit_snapshot: 'portion',
      unit_price_snapshot: unitPrice,
      tax_rate_snapshot: '0.05',
      original_quantity: it.quantity,
      active_quantity: it.quantity,
      cancelled_quantity: 0,
      line_subtotal: lineTotal,
      item_status: 'SUBMITTED',
      item_notes: it.item_notes ?? null,
    };
  });


  const newOrder: OrderResponse = {
    id: `demo-order-${Date.now()}`,
    order_number: orderNum,
    table_session_id: 'session-demo-4',
    table_id: 'table-demo-4',
    source: 'CUSTOMER_QR',
    customer_session_id: 'demo-session-4',
    status: 'SUBMITTED',
    order_subtotal: subtotal.toFixed(2),
    special_instructions: payload.special_instructions ?? null,
    is_first_qr_order_of_session: currentOrders.length === 0,
    version: 1,
    placed_at: now,
    accepted_at: null,
    ready_at: null,
    served_at: null,
    items,
  };

  const updated = [newOrder, ...currentOrders];
  sessionStorage.setItem('hms_demo_orders', JSON.stringify(updated));
  _demoOrders = updated;

  return {
    order: newOrder,
    table_session: {
      session_id: 'session-demo-4',
      session_code: 'SESS-401',
      status: 'ACTIVE',
      current_outstanding_amount: subtotal.toFixed(2),
      custom_outstanding_limit: '5000.00',
      is_first_order: currentOrders.length === 0,
    },
    is_replay: false,
  };
}
