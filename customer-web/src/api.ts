// ─────────────────────────────────────────────────────────────────────────────
// API Client — all calls go through here; session token is set once and stored
// in sessionStorage (not localStorage – clears on tab close).
// ─────────────────────────────────────────────────────────────────────────────

import type {
  CustomerMenuResponse,
  CustomerSession,
  OrderCreate,
  OrderCreateResponse,
  OrderResponse,
} from './types';
import { isDevDemoEnabled, isProd, resolveApiBaseUrl } from './utils/env';

const BASE = resolveApiBaseUrl();

let _sessionToken: string | null = sessionStorage.getItem('hms_customer_token');

export function setSessionToken(token: string): void {
  _sessionToken = token;
  sessionStorage.setItem('hms_customer_token', token);
}

export function getSessionToken(): string | null {
  return _sessionToken;
}

export function clearSessionToken(): void {
  _sessionToken = null;
  sessionStorage.removeItem('hms_customer_token');
}

// ─────────────────────────────────────────────────────────────────────────────
// HTTP helpers
// ─────────────────────────────────────────────────────────────────────────────

interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export class HmsApiError extends Error {
  constructor(
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>,
    public readonly httpStatus?: number,
  ) {
    super(message);
    this.name = 'HmsApiError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  idempotencyKey?: string,
): Promise<T> {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {}),
  };

  if (_sessionToken) {
    (headers as Record<string, string>)['X-Customer-Session-Token'] = _sessionToken;
  }
  if (idempotencyKey) {
    (headers as Record<string, string>)['Idempotency-Key'] = idempotencyKey;
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (!res.ok) {
    let err: { error?: ApiError } = {};
    try {
      err = await res.json();
    } catch {
      // ignore parse failure
    }
    throw new HmsApiError(
      err.error?.code ?? 'UNKNOWN_ERROR',
      err.error?.message ?? `HTTP ${res.status}`,
      err.error?.details,
      res.status,
    );
  }

  // 204 No Content
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ─────────────────────────────────────────────────────────────────────────────
// QR Resolution — called on landing page; stores session token
// ─────────────────────────────────────────────────────────────────────────────

export interface QrResolutionResponse {
  session_token: string;
  table_number: number;
  table_display_name: string;
  table_id: string;
  session_id: string;
  expires_at: string;
}

export async function resolveQrToken(qrToken: string): Promise<QrResolutionResponse> {
  try {
    return await request<QrResolutionResponse>('/public/qr/resolve', {
      method: 'POST',
      body: JSON.stringify({ qr_token: qrToken }),
    });
  } catch (err) {
    if (!isDevDemoEnabled()) {
      if (err instanceof HmsApiError) throw err;
      throw new HmsApiError(
        'QR_RESOLUTION_FAILED',
        'Unable to resolve dining table QR code. Please scan a valid table QR standee.',
      );
    }
    // Development-only offline preview fallback
    console.warn('[DEV DEMO] Falling back to local demo table token for QR:', qrToken);
    const match = qrToken.match(/table-?(\d+)/i);
    const tableNum = match ? parseInt(match[1], 10) : 4;
    return {
      session_token: `demo-token-table-${tableNum}`,
      table_number: tableNum,
      table_display_name: `Table ${tableNum}`,
      table_id: `table-demo-${tableNum}`,
      session_id: `session-demo-${tableNum}-${Date.now()}`,
      expires_at: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
    };
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Customer Session
// ─────────────────────────────────────────────────────────────────────────────

import { DEMO_MENU, DEMO_SESSION, getDemoOrders, saveDemoOrder, cancelDemoOrder } from './demoData';

export async function getSession(): Promise<CustomerSession> {
  if (_sessionToken?.startsWith('demo-')) {
    if (!isDevDemoEnabled()) {
      clearSessionToken();
      throw new HmsApiError('INVALID_SESSION', 'Demo sessions are strictly forbidden in production.');
    }
    const tableNum = sessionStorage.getItem('hms_table_number')
      ? parseInt(sessionStorage.getItem('hms_table_number')!, 10)
      : DEMO_SESSION.table_number;
    const tableName = sessionStorage.getItem('hms_table_name') || `Table ${tableNum}`;
    return {
      ...DEMO_SESSION,
      table_number: tableNum,
      table_display_name: tableName,
      table_id: sessionStorage.getItem('hms_table_id') || `table-demo-${tableNum}`,
      session_id: sessionStorage.getItem('hms_table_session_id') || `demo-session-${tableNum}`,
    };
  }
  try {
    return await request<CustomerSession>('/customer/session');
  } catch (err) {
    if (_sessionToken && isDevDemoEnabled()) {
      console.warn('[DEV DEMO] Serving demo session fallback');
      return DEMO_SESSION;
    }
    throw err;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Menu
// ─────────────────────────────────────────────────────────────────────────────

export async function getMenu(params?: {
  category_id?: string;
  dietary_type?: string;
  available_only?: boolean;
}): Promise<CustomerMenuResponse> {
  if (_sessionToken?.startsWith('demo-')) {
    if (!isDevDemoEnabled()) {
      throw new HmsApiError('INVALID_SESSION', 'Demo sessions are strictly forbidden in production.');
    }
    return DEMO_MENU;
  }
  const qs = new URLSearchParams();
  if (params?.category_id) qs.set('category_id', params.category_id);
  if (params?.dietary_type) qs.set('dietary_type', params.dietary_type);
  if (params?.available_only) qs.set('available_only', 'true');
  const query = qs.toString();
  try {
    return await request<CustomerMenuResponse>(`/customer/menu${query ? `?${query}` : ''}`);
  } catch (err) {
    if (isDevDemoEnabled()) {
      console.warn('[DEV DEMO] Backend unreachable, serving local demo menu fallback:', err);
      return DEMO_MENU;
    }
    throw err;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Orders
// ─────────────────────────────────────────────────────────────────────────────

export async function placeOrder(
  payload: OrderCreate,
  idempotencyKey: string,
): Promise<{ data: OrderCreateResponse; httpStatus: number }> {
  if (_sessionToken?.startsWith('demo-')) {
    if (!isDevDemoEnabled()) {
      throw new HmsApiError('INVALID_SESSION', 'Demo sessions are strictly forbidden in production.');
    }
    const demoResp = saveDemoOrder(payload);
    return { data: demoResp, httpStatus: 201 };
  }

  // We need the raw Response to detect 200 vs 201, so bypass the helper
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Idempotency-Key': idempotencyKey,
  };
  if (_sessionToken) headers['X-Customer-Session-Token'] = _sessionToken;

  try {
    const res = await fetch(`${BASE}/customer/orders`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      let err: { error?: ApiError } = {};
      try {
        err = await res.json();
      } catch { /* ignore */ }
      throw new HmsApiError(
        err.error?.code ?? 'UNKNOWN_ERROR',
        err.error?.message ?? `HTTP ${res.status}`,
        err.error?.details,
        res.status,
      );
    }

    return { data: await res.json() as OrderCreateResponse, httpStatus: res.status };
  } catch (err) {
    if (isDevDemoEnabled() && (_sessionToken?.startsWith('demo-') || err instanceof TypeError)) {
      console.warn('[DEV DEMO] Saving order to local memory in dev demo mode');
      const demoResp = saveDemoOrder(payload);
      return { data: demoResp, httpStatus: 201 };
    }
    throw err;
  }
}

export async function listOrders(): Promise<OrderResponse[]> {
  if (_sessionToken?.startsWith('demo-')) {
    if (!isDevDemoEnabled()) {
      throw new HmsApiError('INVALID_SESSION', 'Demo sessions are strictly forbidden in production.');
    }
    return getDemoOrders();
  }
  try {
    return await request<OrderResponse[]>('/customer/orders');
  } catch (err) {
    if (isDevDemoEnabled()) {
      return getDemoOrders();
    }
    throw err;
  }
}

export async function cancelCustomerOrder(orderId: string): Promise<OrderResponse> {
  if (_sessionToken?.startsWith('demo-')) {
    if (!isDevDemoEnabled()) {
      throw new HmsApiError('INVALID_SESSION', 'Demo sessions are strictly forbidden in production.');
    }
    return cancelDemoOrder(orderId);
  }
  return request<OrderResponse>(`/customer/orders/${orderId}/cancel`, {
    method: 'POST',
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Waiter Requests
// ─────────────────────────────────────────────────────────────────────────────

import type { WaiterRequest, WaiterRequestReason } from './types';

let _demoWaiterRequest: WaiterRequest | null = null;

export async function callWaiter(
  reason: WaiterRequestReason,
  notes?: string,
): Promise<WaiterRequest> {
  if (_sessionToken?.startsWith('demo-')) {
    if (!isDevDemoEnabled()) {
      throw new HmsApiError('INVALID_SESSION', 'Demo sessions are strictly forbidden in production.');
    }
    _demoWaiterRequest = {
      id: `demo-wr-${Date.now()}`,
      customer_session_id: 'demo-session',
      table_session_id: 'demo-ts',
      table_id: 'table-demo-4',
      reason,
      notes: notes ?? null,
      status: 'PENDING',
      claimed_by_user_id: null,
      claimed_at: null,
      completed_at: null,
      completed_by_user_id: null,
      cancelled_at: null,
      expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
      created_at: new Date().toISOString(),
    };
    // Simulate waiter claiming after 2.5s for rich interactive demo feedback
    setTimeout(() => {
      if (_demoWaiterRequest && _demoWaiterRequest.status === 'PENDING') {
        _demoWaiterRequest = {
          ..._demoWaiterRequest,
          status: 'CLAIMED',
          claimed_at: new Date().toISOString(),
        };
      }
    }, 2500);
    return _demoWaiterRequest;
  }
  return request<WaiterRequest>('/customer/waiter-requests', {
    method: 'POST',
    body: JSON.stringify({ reason, notes: notes ?? null }),
  });
}

export async function getActiveWaiterRequest(): Promise<WaiterRequest | null> {
  if (_sessionToken?.startsWith('demo-')) {
    if (!isDevDemoEnabled()) return null;
    return _demoWaiterRequest;
  }
  try {
    const result = await request<WaiterRequest | null>('/customer/waiter-requests/active');
    return result ?? null;
  } catch {
    return null;
  }
}

export async function cancelWaiterRequest(requestId: string): Promise<WaiterRequest> {
  if (_sessionToken?.startsWith('demo-')) {
    if (!isDevDemoEnabled()) {
      throw new HmsApiError('INVALID_SESSION', 'Demo sessions are strictly forbidden in production.');
    }
    if (_demoWaiterRequest) {
      _demoWaiterRequest = { ..._demoWaiterRequest, status: 'CANCELLED' };
    }
    const res = _demoWaiterRequest || {
      id: requestId,
      customer_session_id: 'demo-session',
      table_session_id: 'demo-ts',
      table_id: 'table-demo-4',
      reason: 'OTHER' as WaiterRequestReason,
      notes: null,
      status: 'CANCELLED' as const,
      claimed_by_user_id: null,
      claimed_at: null,
      completed_at: null,
      completed_by_user_id: null,
      cancelled_at: new Date().toISOString(),
      expires_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
    };
    _demoWaiterRequest = null;
    return res;
  }
  return request<WaiterRequest>(`/customer/waiter-requests/${requestId}`, {
    method: 'DELETE',
  });
}
