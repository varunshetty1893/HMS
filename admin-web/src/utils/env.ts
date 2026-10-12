/**
 * Centralized environment configuration and mode detection for Admin Web.
 *
 * Enforces strict separation between Development and Production environments:
 * - Production builds unconditionally disable mock fallbacks, demo staff shortcuts,
 *   and synthetic auth credentials.
 * - Missing production configurations fail safely without falling back to local mocks.
 */

export const isDev: boolean = import.meta.env.DEV;
export const isProd: boolean = import.meta.env.PROD || import.meta.env.MODE === 'production';

/**
 * Returns true if developer demo shortcuts (e.g. test customer button, staff credential badge) are permitted.
 * In production mode, this ALWAYS returns false.
 */
export function isDevDemoEnabled(): boolean {
  if (isProd) return false;
  return import.meta.env.VITE_DISABLE_DEV_DEMO !== 'true';
}

/**
 * Returns true if the HTTP client is allowed to fall back to the in-memory mockRouter.
 * In production mode, this ALWAYS returns false.
 * In development, it requires explicit opt-in via VITE_ENABLE_DEV_MOCKS=true (or running in AI Studio preview if set).
 */
export function isDevMockAllowed(): boolean {
  if (isProd) return false;
  return import.meta.env.VITE_ENABLE_DEV_MOCKS === 'true';
}

/**
 * Resolves the API Base URL for HTTP requests.
 * Guaranteed to end with '/api/v1' without a trailing slash.
 */
export function resolveAdminBaseUrl(): string {
  const envUrl = (import.meta.env.VITE_API_BASE_URL || '').trim().replace(/\/+$/, '');
  if (!envUrl) return '/api/v1';
  return envUrl.endsWith('/api/v1') ? envUrl : `${envUrl}/api/v1`;
}

/**
 * Resolves the WebSocket Base URL for administrative real-time updates.
 */
export function resolveAdminWsUrl(): string {
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
  const protocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = typeof window !== 'undefined' ? window.location.host : 'localhost:8000';
  return `${protocol}//${host}/api/v1/ws`;
}

/**
 * Purge any mock tokens from localStorage if running in production.
 */
export function purgeAdminMockStorageIfProduction(): void {
  if (!isProd) return;
  try {
    const token = localStorage.getItem('hms_admin_access_token');
    if (token && token.startsWith('mock-')) {
      localStorage.removeItem('hms_admin_access_token');
      localStorage.removeItem('hms_admin_refresh_token');
      localStorage.removeItem('hms_admin_user');
    }
  } catch {
    // Ignore storage restrictions
  }
}
