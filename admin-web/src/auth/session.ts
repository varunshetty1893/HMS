/**
 * Admin session storage, in one place.
 *
 * Two modes, chosen at build time with `VITE_AUTH_COOKIE`:
 *
 * - cookie mode (`VITE_AUTH_COOKIE=true`, recommended): the refresh token lives ONLY in an httpOnly
 *   cookie set by the backend, so page scripts (XSS) can never read it. The short-lived access
 *   token is kept in memory and restored after a reload through a silent refresh.
 *   Requires the web app and the API to share a site (e.g. a Vercel rewrite of `/api/*` to the
 *   backend), otherwise browsers treat the cookie as third-party and may block it.
 * - legacy mode (default): tokens in localStorage, exactly as before. Keeps current deployments
 *   working until the proxy/cookie setup is in place.
 */

import { AUTH_COOKIE_MODE, resolveAdminBaseUrl } from '../utils/env';

const ACCESS_KEY = 'hms_admin_access_token';
const REFRESH_KEY = 'hms_admin_refresh_token';
const USER_KEY = 'hms_admin_user';

export const authCookieMode: boolean = AUTH_COOKIE_MODE;

let memoryAccessToken: string | null = null;

/** Headers that mark a request as coming from our own web app (checked by the backend). */
export function cookieModeHeaders(): Record<string, string> {
  return authCookieMode
    ? { 'X-Auth-Transport': 'cookie', 'X-Requested-With': 'hms-admin-web' }
    : {};
}

export function isAuthEndpoint(endpoint: string): boolean {
  return endpoint.startsWith('/auth/');
}

export function getAccessToken(): string | null {
  return authCookieMode ? memoryAccessToken : localStorage.getItem(ACCESS_KEY);
}

/** Legacy mode only; in cookie mode JavaScript never sees the refresh token. */
export function getRefreshToken(): string | null {
  return authCookieMode ? null : localStorage.getItem(REFRESH_KEY);
}

export function getStoredUser<T>(): T | null {
  if (authCookieMode) return null;
  try {
    const saved = localStorage.getItem(USER_KEY);
    return saved ? (JSON.parse(saved) as T) : null;
  } catch {
    return null;
  }
}

/** Remove anything an earlier (legacy) build left in localStorage. */
function purgeLegacyStorage(): void {
  try {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {
    // storage may be unavailable
  }
}

export function saveSession(session: {
  access_token: string;
  refresh_token?: string;
  user?: unknown;
}): void {
  if (authCookieMode) {
    memoryAccessToken = session.access_token;
    purgeLegacyStorage();
    return;
  }
  localStorage.setItem(ACCESS_KEY, session.access_token);
  if (session.refresh_token) localStorage.setItem(REFRESH_KEY, session.refresh_token);
  if (session.user !== undefined) localStorage.setItem(USER_KEY, JSON.stringify(session.user));
}

/** Forget only the access token (e.g. the WebSocket was told the token is no longer valid). */
export function dropAccessToken(): void {
  memoryAccessToken = null;
  if (!authCookieMode) localStorage.removeItem(ACCESS_KEY);
}

export function clearSession(): void {
  memoryAccessToken = null;
  purgeLegacyStorage();
}

export interface RefreshedTokens {
  access_token: string;
  refresh_token?: string;
}

let inflightRefresh: Promise<RefreshedTokens | null> | null = null;

/**
 * Exchange the refresh token for a new access token.
 * Calls made at the same time share ONE request: refresh tokens rotate, so a second parallel
 * call with the same token would look like token reuse and revoke the whole session.
 */
export function refreshSession(): Promise<RefreshedTokens | null> {
  if (!inflightRefresh) {
    inflightRefresh = doRefresh().finally(() => {
      inflightRefresh = null;
    });
  }
  return inflightRefresh;
}

async function doRefresh(): Promise<RefreshedTokens | null> {
  const legacyToken = getRefreshToken();
  if (!authCookieMode && !legacyToken) return null;
  try {
    const resp = await fetch(`${resolveAdminBaseUrl()}/auth/refresh`, {
      method: 'POST',
      headers: authCookieMode
        ? cookieModeHeaders()
        : { 'Content-Type': 'application/json' },
      credentials: authCookieMode ? 'include' : 'same-origin',
      body: authCookieMode ? undefined : JSON.stringify({ refresh_token: legacyToken }),
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    if (!data?.access_token) return null;
    saveSession({ access_token: data.access_token, refresh_token: data.refresh_token });
    return data as RefreshedTokens;
  } catch {
    return null;
  }
}
