/**
 * Base HTTP client for Admin Web.
 * Enforces Bearer JWT injection, 401 refresh token rotation, and error standard handling.
 */

import {
  authCookieMode,
  clearSession,
  cookieModeHeaders,
  getAccessToken,
  isAuthEndpoint,
  refreshSession,
} from '../auth/session';
import { isDevMockAllowed, resolveAdminBaseUrl } from '../utils/env';

/**
 * In-memory mock API, available in `vite dev` only.
 * `import.meta.env.DEV` is replaced by the literal `false` in production builds, so the branch
 * below (and therefore mockRouter.ts + mockData.ts) is removed from the production bundle.
 */
async function loadDevMock<T>(endpoint: string, options: RequestInit): Promise<T> {
  if (import.meta.env.DEV) {
    const { handleMockRequest } = await import('./mockRouter');
    return handleMockRequest<T>(endpoint, options as never);
  }
  throw new Error('Mock API is not available in production builds');
}

// In dev without explicit VITE_API_BASE_URL, go through the Vite proxy (/api -> backend)
const BASE_URL = resolveAdminBaseUrl();

export class ApiError extends Error {
  code: string;
  status: number;
  details?: any;

  constructor(message: string, code: string = 'API_ERROR', status: number = 500, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}


const FIELD_LABELS: Record<string, string> = {
  item_code: 'Short code',
  name: 'Name',
  category_id: 'Category',
  dietary_type: 'Veg / Non-veg tag',
  spice_level: 'Spice level',
  variant_name: 'Portion name',
  variant_code: 'Portion code',
  quantity_value: 'Quantity',
  unit: 'Unit',
  price: 'Price',
};

/** Turn FastAPI/Pydantic field issues into one short human sentence. */
function describeFieldIssues(issues: Array<{ field: string; issue: string; type?: string }>): string {
  const lines = issues.slice(0, 4).map((i) => {
    const parts = i.field.split('.');
    const leaf = parts[parts.length - 1];
    const label = FIELD_LABELS[leaf] || leaf;
    const where = parts.includes('variants') ? ` (portion ${Number(parts[parts.indexOf('variants') + 1]) + 1})` : '';
    if (i.type?.includes('extra_forbidden')) return `${label}${where}: not accepted by server`;
    return `${label}${where}: ${i.issue}`;
  });
  return lines.join('\n');
}

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers || {});

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  // Cookie mode: auth endpoints carry the refresh cookie and the anti-CSRF headers.
  let credentials: RequestCredentials | undefined;
  if (authCookieMode && isAuthEndpoint(endpoint)) {
    credentials = 'include';
    for (const [name, value] of Object.entries(cookieModeHeaders())) headers.set(name, value);
  }

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;

  let response: Response;
  try {
    response = await fetch(url, { ...options, headers, ...(credentials ? { credentials } : {}) });
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('text/html')) {
      if (isDevMockAllowed()) {
        console.warn('[DEV MOCK] HTML response received, routing to mock router for:', endpoint);
        return loadDevMock<T>(endpoint, options);
      }
      throw new ApiError(
        'Unexpected HTML response received from server. Check API URL configuration.',
        'UNEXPECTED_HTML',
        response.status
      );
    }
    if (!response.ok && (response.status === 404 || response.status === 502 || response.status === 503)) {
      if (isDevMockAllowed()) {
        console.warn(`[DEV MOCK] HTTP ${response.status} received, routing to mock router for:`, endpoint);
        return loadDevMock<T>(endpoint, options);
      }
      // In production / non-mock mode, fall through to structured HTTP error handling
    }
  } catch (err: any) {
    if (err instanceof ApiError) throw err;
    if (isDevMockAllowed()) {
      console.warn('[DEV MOCK] Network error, routing to mock router for:', endpoint);
      return loadDevMock<T>(endpoint, options);
    }
    throw new ApiError(
      err?.message || 'Network connection failed. Unable to reach backend server.',
      'NETWORK_ERROR',
      0
    );
  }

  // Handle 401 Token Expiration -> Trigger Refresh
  if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(() => apiClient<T>(endpoint, options));
    }

    isRefreshing = true;
    const refreshed = await refreshSession();
    if (refreshed) {
      processQueue(null);
      isRefreshing = false;
      return apiClient<T>(endpoint, options);
    }

    // Refresh failed or no refresh token -> logout
    isRefreshing = false;
    processQueue(new Error('Session expired'));
    clearSession();
    window.location.href = '/login';
    throw new ApiError('Session expired. Please log in again.', 'SESSION_EXPIRED', 401);
  }

  // Handle non-2xx responses
  if (!response.ok) {
    let errJson: any = null;
    try {
      errJson = await response.json();
    } catch {
      // not JSON
    }

    const code = errJson?.error?.code || `HTTP_${response.status}`;
    const details = errJson?.error?.details;
    let message = errJson?.error?.message || `Request failed with status ${response.status}`;
    const fieldIssues = details?.fields;
    if (Array.isArray(fieldIssues) && fieldIssues.length > 0) {
      message = describeFieldIssues(fieldIssues);
    }

    throw new ApiError(message, code, response.status, details);
  }

  if (response.status === 204) {
    return {} as T;
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('text/csv')) {
    const textData = await response.text();
    return textData as unknown as T;
  }

  if (contentType && contentType.includes('spreadsheetml.sheet')) {
    return (await response.blob()) as unknown as T;
  }

  try {
    return await response.json();
  } catch (err: any) {
    if (isDevMockAllowed()) {
      return loadDevMock<T>(endpoint, options);
    }
    throw new ApiError(
      'Invalid JSON response received from backend server',
      'INVALID_JSON_RESPONSE',
      response.status
    );
  }
}
