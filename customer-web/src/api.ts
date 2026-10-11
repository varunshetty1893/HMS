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

const BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1';

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
  return request<QrResolutionResponse>('/public/qr/resolve', {
    method: 'POST',
    body: JSON.stringify({ qr_token: qrToken }),
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// Customer Session
// ─────────────────────────────────────────────────────────────────────────────

export async function getSession(): Promise<CustomerSession> {
  return request<CustomerSession>('/customer/session');
}

// ─────────────────────────────────────────────────────────────────────────────
// Menu
// ─────────────────────────────────────────────────────────────────────────────

export async function getMenu(params?: {
  category_id?: string;
  dietary_type?: string;
  available_only?: boolean;
}): Promise<CustomerMenuResponse> {
  const qs = new URLSearchParams();
  if (params?.category_id) qs.set('category_id', params.category_id);
  if (params?.dietary_type) qs.set('dietary_type', params.dietary_type);
  if (params?.available_only) qs.set('available_only', 'true');
  const query = qs.toString();
  return request<CustomerMenuResponse>(`/customer/menu${query ? `?${query}` : ''}`);
}

// ─────────────────────────────────────────────────────────────────────────────
// Orders
// ─────────────────────────────────────────────────────────────────────────────

export async function placeOrder(
  payload: OrderCreate,
  idempotencyKey: string,
): Promise<{ data: OrderCreateResponse; httpStatus: number }> {
  // We need the raw Response to detect 200 vs 201, so bypass the helper
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Idempotency-Key': idempotencyKey,
  };
  if (_sessionToken) headers['X-Customer-Session-Token'] = _sessionToken;

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
}

export async function listOrders(): Promise<OrderResponse[]> {
  return request<OrderResponse[]>('/customer/orders');
}
