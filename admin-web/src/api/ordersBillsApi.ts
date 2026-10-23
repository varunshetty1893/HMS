import { apiClient } from './client';
import { Bill, Order, TableBillCheck, OrderItemAdjustmentRequest, OrderReportItem, Payment } from '@/types/api';

export interface MenuSearchVariant {
  variant_id: string;
  variant_code: string | null;
  variant_name: string;
  price: string | null;
}

export interface MenuSearchItem {
  item_id: string;
  item_code: string;
  name: string;
  category_name: string;
  is_available: boolean;
  variants: MenuSearchVariant[];
}

export interface TableOrderSummary {
  id: string;
  order_number: string;
  status: string;
  version: number;
}

export const ordersBillsApi = {
  listOrders: async (filters: {
    status?: string;
    source?: string;
    from?: string;
    to?: string;
  } = {}): Promise<OrderReportItem[]> => {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.source) params.append('source', filters.source);
    if (filters.from) params.append('from', filters.from);
    if (filters.to) params.append('to', filters.to);
    return apiClient<OrderReportItem[]>(`/admin/orders?${params.toString()}`);
  },

  getOrder: async (orderId: string): Promise<Order> => {
    return apiClient<Order>(`/admin/orders/${orderId}`);
  },

  adjustOrderItem: async (
    orderId: string,
    orderItemId: string,
    payload: OrderItemAdjustmentRequest
  ): Promise<Order> => {
    return apiClient<Order>(`/admin/orders/${orderId}/items/${orderItemId}/adjust`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  voidOrder: async (
    orderId: string,
    expectedVersion: number,
    cancellationReason: string
  ): Promise<Order> => {
    return apiClient<Order>(`/admin/orders/${orderId}/void`, {
      method: 'POST',
      body: JSON.stringify({
        expected_version: expectedVersion,
        cancellation_reason: cancellationReason,
      }),
    });
  },

  overrideSessionLimit: async (
    sessionId: string,
    newLimit: string,
    reason: string
  ): Promise<{ table_session_id: string; custom_outstanding_limit: string }> => {
    return apiClient<{ table_session_id: string; custom_outstanding_limit: string }>(
      `/admin/table-sessions/${sessionId}/override-limit`,
      {
        method: 'POST',
        body: JSON.stringify({ new_limit: newLimit, reason }),
      }
    );
  },

  unlockSession: async (sessionId: string): Promise<any> => {
    return apiClient<any>(`/admin/table-sessions/${sessionId}/unlock`, {
      method: 'POST',
    });
  },

  listOpenTableChecks: async (): Promise<TableBillCheck[]> => {
    return apiClient<TableBillCheck[]>('/admin/bills/open-tables');
  },

  listBills: async (filters: {
    status?: string;
    from?: string;
    to?: string;
  } = {}): Promise<Bill[]> => {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.from) params.append('from', filters.from);
    if (filters.to) params.append('to', filters.to);
    return apiClient<Bill[]>(`/admin/bills?${params.toString()}`);
  },

  applyDiscount: async (
    billId: string,
    discountAmount: string,
    discountReason: string
  ): Promise<Bill> => {
    return apiClient<Bill>(`/admin/bills/${billId}/discount`, {
      method: 'POST',
      body: JSON.stringify({
        discount_amount: discountAmount,
        discount_reason: discountReason,
      }),
    });
  },

  voidBillForRevision: async (billId: string, voidReason: string): Promise<Bill> => {
    return apiClient<Bill>(`/admin/bills/${billId}/void-for-revision`, {
      method: 'POST',
      body: JSON.stringify({ void_reason: voidReason }),
    });
  },

  getBill: async (billId: string): Promise<Bill> => {
    return apiClient<Bill>(`/bills/${billId}`);
  },

  generateBill: async (
    tableNumber: number,
    options: {
      discount_amount?: string;
      discount_reason?: string | null;
      price_overrides?: {
        order_item_id: string;
        unit_price: string;
        quantity_billed: number;
        reason: string;
      }[];
      custom_line_items?: {
        item_name: string;
        quantity: number;
        unit_price: string;
        reason?: string;
      }[];
    } = {}
  ): Promise<Bill> => {
    return apiClient<Bill>('/bills/generate', {
      method: 'POST',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify({ table_number: tableNumber, ...options }),
    });
  },

  /** Menu lookup by short code or dish name (staff endpoint, admins allowed). */
  searchMenu: async (q: string): Promise<MenuSearchItem[]> => {
    const res = await apiClient<{ results: MenuSearchItem[] }>(
      `/waiter/menu/search?q=${encodeURIComponent(q)}`
    );
    return res.results || [];
  },

  /** Orders of the table's active session, with status and version. */
  getTableOrders: async (tableId: string): Promise<TableOrderSummary[]> => {
    const res = await apiClient<{ orders?: TableOrderSummary[] }>(`/admin/tables/${tableId}/session`);
    return res.orders || [];
  },

  /** READY -> SERVED (admins may serve on behalf of the waiter). */
  serveOrder: async (orderId: string, expectedVersion: number): Promise<void> => {
    await apiClient<unknown>(`/waiter/orders/${orderId}/serve`, {
      method: 'POST',
      body: JSON.stringify({ expected_version: expectedVersion }),
    });
  },

  recordPayment: async (
    billId: string,
    payload: {
      payment_method: 'CASH' | 'UPI' | 'CARD' | 'OTHER';
      /** Exact bill amount applied as revenue. */
      amount_paid: string;
      /** Physical cash handed over; accepted for CASH only. */
      amount_tendered?: string | null;
      reference_number?: string | null;
      notes?: string | null;
    }
  ): Promise<{ bill_status: string }> => {
    return apiClient<{ bill_status: string }>(`/bills/${billId}/payments`, {
      method: 'POST',
      headers: { 'Idempotency-Key': crypto.randomUUID() },
      body: JSON.stringify(payload),
    });
  },

  listPayments: async (filters: {
    status?: string;
    payment_method?: string;
    from?: string;
    to?: string;
  } = {}): Promise<Payment[]> => {
    const params = new URLSearchParams();
    if (filters.status) params.append('status', filters.status);
    if (filters.payment_method) params.append('payment_method', filters.payment_method);
    if (filters.from) params.append('from', filters.from);
    if (filters.to) params.append('to', filters.to);
    return apiClient<Payment[]>(`/admin/payments?${params.toString()}`);
  },
};
