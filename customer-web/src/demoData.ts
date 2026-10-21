import type {
  CustomerItemChange,
  CustomerMenuResponse,
  CustomerSession,
  OrderResponse,
  OrderCreate,
  OrderCreateResponse,
} from './types';

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
          description: 'Cottage cheese cubes marinated in spiced yogurt, capsicum & roasted in clay tandoor.',
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
          description: 'Tender chicken boneless chunks marinated in rich cream, cashew paste & aromatic green cardamom.',
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
          description: 'Golden fried crispy babycorn tossed with spring onions, bell peppers & oriental wok spices.',
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
          description: 'Farm fresh eggs scrambled with chopped onions, juicy tomatoes, green chillies & fresh coriander.',
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
          item_code: 'VC-PBM',
          name: 'Paneer Butter Masala',
          description: 'Fresh malai paneer simmered in a rich creamy tomato, butter, and cashew nut gravy.',
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
          name: 'Dal Makhani Bukhara',
          description: 'Whole black lentils slow-cooked overnight with white butter, fresh cream & gentle spices.',
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
          description: 'Long grain basmati rice and marinated chicken cooked under dum with saffron, mint & caramelized onions.',
          dietary_type: 'NON_VEG',
          spice_level: 'HOT',
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
          description: 'Refined flour clay oven flatbread topped with minced garlic, fresh coriander & melted desi butter.',
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
          description: 'Thick churned creamy yogurt blended with sweet Ratnagiri Alphonso mango pulp & cardamoms.',
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
          description: 'Freshly squeezed lemon juice with sparkling club soda, black salt & roasted cumin.',
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

  let subtotal = 0;
  const items = payload.items.map((it, idx) => {
    // Find variant from menu
    let variantName = 'Regular';
    let unitPrice = '200.00';
    let itemName = 'Special Dish';
    let itemCode = 'DISH';
    let menuItemId = 'demo-menu-item';

    for (const cat of DEMO_MENU.categories) {
      for (const menuItem of cat.items) {
        const v = menuItem.variants.find((vr) => vr.id === it.variant_id);
        if (v) {
          variantName = v.variant_name;
          unitPrice = v.price || '0';
          itemName = menuItem.name;
          itemCode = menuItem.item_code;
          menuItemId = menuItem.id;
          break;
        }
      }
    }

    const lineTotal = (parseFloat(unitPrice) * it.quantity).toFixed(2);
    subtotal += parseFloat(lineTotal);

    return {
      id: `demo-item-${Date.now()}-${idx}`,
      order_id: `demo-order-${Date.now()}`,
      menu_item_id: menuItemId,
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
    placed_at: new Date().toISOString(),
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

export function cancelDemoOrder(orderId: string): OrderResponse {
  const currentOrders = getDemoOrders();
  const target = currentOrders.find(o => o.id === orderId);
  if (!target) throw new Error("Order not found");
  if (target.status !== 'PLACED' && target.status !== 'SUBMITTED' && target.status !== 'ACCEPTED') {
    throw new Error("Cooking has already started. Order cannot be cancelled.");
  }
  target.status = 'CANCELLED';
  target.order_subtotal = '0.00';
  target.items.forEach(it => {
    it.active_quantity = 0;
    it.line_subtotal = '0.00';
    it.item_status = 'CANCELLED';
  });
  sessionStorage.setItem('hms_demo_orders', JSON.stringify(currentOrders));
  _demoOrders = currentOrders;
  return target;
}


/**
 * DEV-ONLY mirror of the backend edit rules (POST /customer/orders/{id}/modify).
 * Before cooking: any change. While PREPARING: only increases + Full->Half style downgrades.
 */
export function modifyDemoOrder(orderId: string, changes: CustomerItemChange[]): OrderResponse {
  const orders = getDemoOrders();
  const order = orders.find((o) => o.id === orderId);
  if (!order) throw new Error('Order not found');
  const preCooking = ['PLACED', 'SUBMITTED', 'ACCEPTED'].includes(order.status);
  if (!preCooking && order.status !== 'PREPARING') {
    throw new Error('This order can no longer be changed. Please call your waiter.');
  }

  for (const ch of changes) {
    const item = order.items.find((i) => i.id === ch.order_item_id);
    if (!item || item.active_quantity === 0) throw new Error('Item not found or already cancelled');

    if (ch.new_quantity !== undefined) {
      if (ch.new_quantity < item.active_quantity && !preCooking) {
        throw new Error(
          `Cooking has started, so '${item.item_name_snapshot}' can't be reduced or removed. You can still add more.`,
        );
      }
      item.cancelled_quantity += Math.max(0, item.active_quantity - ch.new_quantity);
      item.active_quantity = ch.new_quantity;
      item.item_status = ch.new_quantity === 0 ? 'CANCELLED' : 'MODIFIED';
      item.line_subtotal = (parseFloat(item.unit_price_snapshot) * ch.new_quantity).toFixed(2);
    } else if (ch.switch_to_variant_id) {
      let target = null as null | { id: string; variant_name: string; price: string | null };
      for (const cat of DEMO_MENU.categories) {
        for (const mi of cat.items) {
          if (mi.id !== item.menu_item_id) continue;
          const v = mi.variants.find((vr) => vr.id === ch.switch_to_variant_id);
          if (v) target = v;
        }
      }
      if (!target) throw new Error('That portion size is not available right now.');
      if (parseFloat(target.price || '0') >= parseFloat(item.unit_price_snapshot)) {
        throw new Error('You can only switch to a smaller (cheaper) portion.');
      }
      const move = ch.switch_quantity ?? item.active_quantity;
      item.active_quantity -= move;
      item.cancelled_quantity += move;
      item.item_status = item.active_quantity === 0 ? 'CANCELLED' : 'MODIFIED';
      item.line_subtotal = (parseFloat(item.unit_price_snapshot) * item.active_quantity).toFixed(2);
      order.items.push({
        ...item,
        id: `demo-item-${Date.now()}-sw`,
        menu_price_variant_id: target.id,
        variant_name_snapshot: target.variant_name,
        unit_price_snapshot: target.price || '0',
        original_quantity: move,
        active_quantity: move,
        cancelled_quantity: 0,
        line_subtotal: (parseFloat(target.price || '0') * move).toFixed(2),
        item_status: 'ACTIVE',
      });
    }
  }

  const live = order.items.filter((i) => i.active_quantity > 0);
  order.order_subtotal = live.reduce((sum, i) => sum + parseFloat(i.line_subtotal), 0).toFixed(2);
  if (live.length === 0) {
    order.status = 'CANCELLED';
    order.cancelled_by_role = 'CUSTOMER';
  }
  order.version += 1;
  sessionStorage.setItem('hms_demo_orders', JSON.stringify(orders));
  _demoOrders = orders;
  return order;
}
