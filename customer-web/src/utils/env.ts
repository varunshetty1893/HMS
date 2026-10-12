/**
 * Centralized environment configuration and mode detection for Customer Web.
 *
 * Enforces strict separation between Development and Production environments:
 * - Production builds unconditionally disable all demo shortcuts, fake tokens,
 *   and fallback mocks.
 * - Missing production configurations fail safely.
 */

export const isDev: boolean = import.meta.env.DEV;
export const isProd: boolean = import.meta.env.PROD || import.meta.env.MODE === 'production';

/**
 * Returns true if development demo shortcuts are permitted.
 * In production mode, this ALWAYS returns false regardless of any environment variables.
 */
export function isDevDemoEnabled(): boolean {
  if (isProd) return false;
  // In development, enabled unless explicitly disabled via VITE_DISABLE_DEV_DEMO=true
  return import.meta.env.VITE_DISABLE_DEV_DEMO !== 'true';
}

/**
 * Resolves the API Base URL for HTTP requests.
 * Guaranteed to end with '/api/v1' without a trailing slash.
 */
export function resolveApiBaseUrl(): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
  if (!envUrl) return '/api/v1';
  return envUrl.endsWith('/api/v1') ? envUrl : `${envUrl}/api/v1`;
}

/**
 * Resolves the WebSocket Base URL.
 */
export function resolveWsBaseUrl(): string {
  const customWs = (import.meta.env.VITE_WS_URL || '').trim();
  if (customWs) {
    return customWs.replace(/\/+$/, '');
  }
  const apiBase = (import.meta.env.VITE_API_BASE_URL || '').trim();
  if (apiBase) {
    const cleanApi = apiBase.replace(/\/+$/, '');
    const wsScheme = cleanApi.startsWith('https://') ? 'wss://' : 'ws://';
    const withoutScheme = cleanApi.replace(/^https?:\/\//, '');
    const baseWithWs = withoutScheme.endsWith('/api/v1')
      ? `${withoutScheme}/ws`
      : `${withoutScheme}/api/v1/ws`;
    return `${wsScheme}${baseWithWs}`;
  }
  if (typeof window !== 'undefined' && window.location) {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/api/v1/ws`;
  }
  return 'ws://localhost:8000/api/v1/ws';
}

/**
 * Safety cleanup: Purges any demo tokens or mock state from storage when running in production.
 */
export function purgeDemoStorageIfProduction(): void {
  if (!isProd) return;
  try {
    const token = sessionStorage.getItem('hms_customer_token');
    if (token && token.startsWith('demo-')) {
      sessionStorage.removeItem('hms_customer_token');
      sessionStorage.removeItem('hms_table_name');
      sessionStorage.removeItem('hms_table_number');
      sessionStorage.removeItem('hms_table_id');
      sessionStorage.removeItem('hms_table_session_id');
      sessionStorage.removeItem('hms_demo_orders');
    }
  } catch {
    // Ignore storage access errors in restricted iframe environments
  }
}
