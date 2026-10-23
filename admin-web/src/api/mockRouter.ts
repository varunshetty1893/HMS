import {
  getMockAuditLogs,
  getMockBills,
  getMockCategories,
  getMockDailySales,
  getMockItems,
  getMockKPIs,
  getMockOrders,
  getMockSettings,
  getMockStaff,
  getMockTables,
  INITIAL_USER,
  saveMockBill,
  saveMockCategory,
  saveMockItem,
  saveMockOrder,
  saveMockSettings,
  saveMockStaff,
  saveMockTable,
} from './mockData';

export async function handleMockRequest<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const method = (options.method || 'GET').toUpperCase();
  const urlObj = new URL(endpoint, 'http://localhost');
  const path = urlObj.pathname.replace(/^\/api\/v1/, '');
  let body: any = null;

  if (options.body && typeof options.body === 'string') {
    try {
      body = JSON.parse(options.body);
    } catch {
      body = {};
    }
  }

  // Auth Endpoints
  if (path === '/auth/login' && method === 'POST') {
    const user = { ...INITIAL_USER, last_login_at: new Date().toISOString() };
    return {
      access_token: 'mock-access-token-' + Date.now(),
      refresh_token: 'mock-refresh-token-' + Date.now(),
      token_type: 'bearer',
      expires_in_seconds: 86400,
      user,
    } as unknown as T;
  }

  if (path === '/auth/refresh' && method === 'POST') {
    return {
      access_token: 'mock-access-token-' + Date.now(),
      refresh_token: 'mock-refresh-token-' + Date.now(),
      token_type: 'bearer',
      expires_in_seconds: 86400,
    } as unknown as T;
  }

  if (path === '/auth/me' && method === 'GET') {
    return INITIAL_USER as unknown as T;
  }

  if (
    (path === '/auth/change-password' || path === '/auth/admin-recovery-reset') &&
    method === 'POST'
  ) {
    return { status: 'OK' } as unknown as T;
  }

  if (path === '/auth/logout') {
    return {} as unknown as T;
  }

  // Dashboard KPIs
  if (path === '/admin/dashboard' || path === '/admin/reports/overview') {
    return getMockKPIs() as unknown as T;
  }

  // Menu Categories
  if (path === '/admin/menu/categories') {
    if (method === 'GET') {
      const cats = getMockCategories();
      return cats as unknown as T;
    }
    if (method === 'POST') {
      const newCat = {
        id: 'cat-' + Date.now(),
        name: body?.name || 'New Category',
        description: body?.description || '',
        display_order: body?.display_order || 99,
        is_active: body?.is_active ?? true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      saveMockCategory(newCat);
      return newCat as unknown as T;
    }
  }

  const catMatch = path.match(/^\/admin\/menu\/categories\/([^/]+)$/);
  if (catMatch) {
    const catId = catMatch[1];
    const cats = getMockCategories();
    const existing = cats.find((c) => c.id === catId);
    if (existing) {
      if (method === 'PATCH') {
        const updated = { ...existing, ...body, updated_at: new Date().toISOString() };
        saveMockCategory(updated);
        return updated as unknown as T;
      }
      if (method === 'DELETE') {
        saveMockCategory({ ...existing, is_active: false });
        return {} as unknown as T;
      }
    }
  }

  // Menu Items
  if (path === '/admin/menu/items') {
    if (method === 'GET') {
      const categoryId = urlObj.searchParams.get('category_id');
      const items = getMockItems();
      const filtered = categoryId ? items.filter((i) => i.category_id === categoryId) : items;
      return filtered as unknown as T;
    }
    if (method === 'POST') {
      const newItem = {
        id: 'item-' + Date.now(),
        category_id: body?.category_id || 'cat-1',
        item_code: body?.item_code || 'ITM' + Math.floor(Math.random() * 900 + 100),
        name: body?.name || 'New Dish',
        description: body?.description || '',
        dietary_type: body?.dietary_type || 'VEG',
        spice_level: body?.spice_level || 'MILD',
        image_url: body?.image_url || null,
        is_available: true,
        is_active: true,
        display_order: body?.display_order || 99,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        variants: body?.variants || [
          {
            id: 'var-' + Date.now(),
            menu_item_id: 'item-' + Date.now(),
            variant_code: 'FULL',
            variant_name: 'Regular',
            quantity_value: '1',
            unit: 'PORTION',
            price: body?.price || '250.00',
            is_default: true,
            is_available: true,
            is_active: true,
            display_order: 1,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          },
        ],
      };
      saveMockItem(newItem);
      return newItem as unknown as T;
    }
  }

  const itemMatch = path.match(/^\/admin\/menu\/items\/([^/]+)$/);
  if (itemMatch) {
    const itemId = itemMatch[1];
    const items = getMockItems();
    const existing = items.find((i) => i.id === itemId);
    if (existing) {
      if (method === 'PATCH') {
        const updated = { ...existing, ...body, updated_at: new Date().toISOString() };
        saveMockItem(updated);
        return updated as unknown as T;
      }
      return existing as unknown as T;
    }
  }

  const availMatch = path.match(/^\/admin\/menu\/items\/([^/]+)\/availability$/);
  if (availMatch && method === 'POST') {
    const itemId = availMatch[1];
    const items = getMockItems();
    const existing = items.find((i) => i.id === itemId);
    if (existing) {
      const updated = {
        ...existing,
        is_available: body?.is_available ?? !existing.is_available,
        updated_at: new Date().toISOString(),
      };
      saveMockItem(updated);
      return updated as unknown as T;
    }
  }

  // Tables
  if (path === '/admin/tables') {
    if (method === 'GET') {
      return getMockTables() as unknown as T;
    }
    if (method === 'POST') {
      const newTbl = {
        id: 'tbl-' + Date.now(),
        table_number: body?.table_number || getMockTables().length + 1,
        display_name: body?.display_name || `Table ${body?.table_number}`,
        seating_capacity: body?.seating_capacity || 4,
        floor_or_zone: body?.floor_or_zone || 'Main Dining',
        operational_status: 'ENABLED' as const,
        is_active: true,
        display_order: getMockTables().length + 1,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        occupancy_status: 'AVAILABLE' as const,
        active_qr_version: 1,
        active_qr_prefix: `T${String(body?.table_number).padStart(2, '0')}`,
        current_outstanding_amount: '0.00',
      };
      saveMockTable(newTbl);
      return newTbl as unknown as T;
    }
  }

  const tableMatch = path.match(/^\/admin\/tables\/([^/]+)$/);
  if (tableMatch) {
    const tableId = tableMatch[1];
    const tables = getMockTables();
    const existing = tables.find((t) => t.id === tableId);
    if (existing) {
      if (method === 'PATCH') {
        const updated = { ...existing, ...body, updated_at: new Date().toISOString() };
        saveMockTable(updated);
        return updated as unknown as T;
      }
      return existing as unknown as T;
    }
  }

  const qrRegenMatch = path.match(/^\/admin\/tables\/([^/]+)\/qr\/regenerate$/);
  if (qrRegenMatch && method === 'POST') {
    const tableId = qrRegenMatch[1];
    const tables = getMockTables();
    const existing = tables.find((t) => t.id === tableId);
    const newVersion = (existing?.active_qr_version || 1) + 1;
    if (existing) {
      saveMockTable({ ...existing, active_qr_version: newVersion });
    }
    return {
      table_id: tableId,
      table_number: existing?.table_number || 1,
      token_version: newVersion,
      token_prefix: existing?.active_qr_prefix || 'T01',
      printable_qr_url: `/api/v1/public/qr/${tableId}?v=${newVersion}`,
      activated_at: new Date().toISOString(),
    } as unknown as T;
  }

  const qrPrintMatch = path.match(/^\/admin\/tables\/([^/]+)\/qr-print$/);
  if (qrPrintMatch) {
    const tableId = qrPrintMatch[1];
    const tables = getMockTables();
    const existing = tables.find((t) => t.id === tableId);
    return {
      table_id: tableId,
      table_number: existing?.table_number || 1,
      display_name: existing?.display_name || `Table ${existing?.table_number}`,
      token_version: existing?.active_qr_version || 1,
      token_prefix: existing?.active_qr_prefix || 'T01',
      printable_qr_url: `/api/v1/public/qr/${tableId}`,
      ordering_url: window.location.origin + `/q/table-${existing?.table_number || 1}`,
      restaurant_name: 'Spice Hub Family Restaurant',
    } as unknown as T;
  }

  // Orders
  if (path === '/admin/orders') {
    const orders = getMockOrders();
    const status = urlObj.searchParams.get('status');
    const filtered = status ? orders.filter((o) => o.status === status) : orders;
    return filtered.map((o) => ({
      ...o,
      order_id: o.id,
      table_number: o.table_number || 1,
      item_count: o.items?.length || 0,
    })) as unknown as T;
  }

  const orderVoidMatch = path.match(/^\/admin\/orders\/([^/]+)\/void$/);
  if (orderVoidMatch && method === 'POST') {
    const orderId = orderVoidMatch[1];
    const orders = getMockOrders();
    const ord = orders.find((o) => o.id === orderId);
    if (ord) {
      const updated = {
        ...ord,
        status: 'CANCELLED' as const,
        cancellation_reason: body?.cancellation_reason || 'Voided by Admin',
        cancelled_at: new Date().toISOString(),
        version: ord.version + 1,
      };
      saveMockOrder(updated);
      return updated as unknown as T;
    }
  }

  // Bills
  if (path === '/admin/bills/open-tables') {
    return [] as unknown as T;
  }
  if (path === '/admin/bills') {
    const bills = getMockBills();
    const status = urlObj.searchParams.get('status');
    const filtered = status ? bills.filter((b) => b.status === status) : bills;
    return filtered as unknown as T;
  }

  const billDiscountMatch = path.match(/^\/admin\/bills\/([^/]+)\/discount$/);
  if (billDiscountMatch && method === 'POST') {
    const billId = billDiscountMatch[1];
    const bills = getMockBills();
    const b = bills.find((item) => item.id === billId);
    if (b) {
      const discount = parseFloat(body?.discount_amount || '0');
      const subtotal = parseFloat(b.subtotal_amount);
      const taxable = Math.max(0, subtotal - discount);
      const cgst = taxable * 0.025;
      const sgst = taxable * 0.025;
      const total = taxable + cgst + sgst;
      const updated = {
        ...b,
        discount_amount: discount.toFixed(2),
        discount_reason: body?.discount_reason || 'Admin Courtesy',
        taxable_amount: taxable.toFixed(2),
        cgst_amount: cgst.toFixed(2),
        sgst_amount: sgst.toFixed(2),
        grand_total: Math.round(total).toFixed(2),
      };
      saveMockBill(updated);
      return updated as unknown as T;
    }
  }

  const billVoidMatch = path.match(/^\/admin\/bills\/([^/]+)\/void-for-revision$/);
  if (billVoidMatch && method === 'POST') {
    const billId = billVoidMatch[1];
    const bills = getMockBills();
    const b = bills.find((item) => item.id === billId);
    if (b) {
      const updated = { ...b, status: 'VOIDED_FOR_REVISION' as const };
      saveMockBill(updated);
      return updated as unknown as T;
    }
  }

  // Staff (Users)
  if (path === '/admin/users') {
    if (method === 'GET') {
      const staff = getMockStaff();
      const role = urlObj.searchParams.get('role');
      const filtered = role ? staff.filter((s) => s.role === role) : staff;
      return filtered as unknown as T;
    }
    if (method === 'POST') {
      const newUser = {
        id: 'usr-' + Date.now(),
        username: body?.username || 'staff_' + Date.now(),
        full_name: body?.full_name || 'Staff Member',
        role: body?.role || 'WAITER',
        status: 'ACTIVE' as const,
        is_active: true,
        failed_login_attempts: 0,
        locked_until: null,
        last_login_at: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
      saveMockStaff(newUser);
      return newUser as unknown as T;
    }
  }

  const userMatch = path.match(/^\/admin\/users\/([^/]+)$/);
  if (userMatch) {
    const userId = userMatch[1];
    const staff = getMockStaff();
    const existing = staff.find((u) => u.id === userId);
    if (existing) {
      if (method === 'PATCH') {
        const updated = { ...existing, ...body, updated_at: new Date().toISOString() };
        saveMockStaff(updated);
        return updated as unknown as T;
      }
      return existing as unknown as T;
    }
  }

  // Settings
  if (path === '/admin/settings') {
    if (method === 'GET') {
      return getMockSettings() as unknown as T;
    }
    if (method === 'PATCH') {
      const updated = { ...getMockSettings(), ...body, updated_at: new Date().toISOString() };
      saveMockSettings(updated);
      return updated as unknown as T;
    }
  }

  // Audit Logs
  if (path === '/admin/audit-logs/facets') {
    const logs = getMockAuditLogs();
    const uniq = (xs: string[]) => Array.from(new Set(xs)).sort();
    return {
      action_types: uniq(logs.map((l) => l.action_type)),
      entity_types: uniq(logs.map((l) => l.entity_type)),
      actor_roles: uniq(logs.map((l) => l.actor_role)),
    } as unknown as T;
  }

  if (path === '/admin/audit-logs/export.xlsx') {
    throw new Error('Excel export needs the live backend (not available in mock mode).');
  }

  if (path === '/admin/audit-logs') {
    const sp = urlObj.searchParams;
    const q = (sp.get('q') || '').toLowerCase();
    const from = sp.get('from');
    const to = sp.get('to');
    const istDay = (iso: string) =>
      new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(new Date(iso));
    const logs = getMockAuditLogs().filter((l) => {
      if (sp.get('action_type') && l.action_type !== sp.get('action_type')) return false;
      if (sp.get('entity_type') && l.entity_type !== sp.get('entity_type')) return false;
      if (sp.get('actor_role') && l.actor_role !== sp.get('actor_role')) return false;
      if (from && istDay(l.created_at) < from) return false;
      if (to && istDay(l.created_at) > to) return false;
      if (q) {
        const hay = `${l.action_type} ${l.entity_type} ${l.entity_id} ${l.reason || ''}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
    const pageSize = Number(sp.get('page_size')) || 20;
    const page = Number(sp.get('page')) || 1;
    const totalPages = logs.length ? Math.ceil(logs.length / pageSize) : 0;
    return {
      items: logs.slice((page - 1) * pageSize, page * pageSize),
      pagination: {
        page,
        page_size: pageSize,
        total_items: logs.length,
        total_pages: totalPages,
        has_next: page < totalPages,
        has_prev: page > 1,
      },
    } as unknown as T;
  }

  // Reports
  if (path === '/admin/reports/daily-sales') {
    return getMockDailySales() as unknown as T;
  }

  if (path.startsWith('/admin/reports/')) {
    return [] as unknown as T;
  }

  // Default fallback
  return {} as unknown as T;
}
