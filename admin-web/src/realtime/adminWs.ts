/**
 * WebSocket client for Admin Web.
 * Subscribes to room:admin, room:tables, room:waiters, room:kitchen, room:menu.
 *
 * Token refresh: Before each (re)connect attempt, if the stored access token
 * appears expired (via JWT exp claim), a silent refresh is attempted using the
 * stored refresh_token so that WebSocket connections are never rejected with 403.
 */

import { dropAccessToken, getAccessToken, refreshSession } from '../auth/session';

// In dev, go through the Vite proxy (/api -> backend) so CORS / port mismatches can't break requests.

type EventHandler = (data: any) => void;
type ConnectionStatus = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED';

/** Decode JWT payload without verifying signature (client-side only). */
function jwtPayload(token: string): Record<string, any> | null {
  try {
    const part = token.split('.')[1];
    if (!part) return null;
    const decoded = atob(part.replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

/** Returns true if token is missing or will expire within the next 60 seconds. */
function isTokenExpiredOrSoon(token: string | null): boolean {
  if (!token) return true;
  const payload = jwtPayload(token);
  if (!payload || typeof payload.exp !== 'number') return true;
  const nowSec = Math.floor(Date.now() / 1000);
  return payload.exp - nowSec < 60; // refresh if less than 60 s remaining
}

/** Attempt silent token refresh. Returns the new access token or null on failure. */
async function silentRefresh(): Promise<string | null> {
  const refreshed = await refreshSession();
  return refreshed?.access_token ?? null;
}

class AdminWebSocketClient {
  private ws: WebSocket | null = null;
  private statusListeners: Set<(status: ConnectionStatus) => void> = new Set();
  private eventListeners: Map<string, Set<EventHandler>> = new Map();
  private reconnectTimeout: any = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private currentStatus: ConnectionStatus = 'DISCONNECTED';
  private shouldReconnect = true;
  private isRefreshing = false;
  // Deduplication ring — prefer event_id (UUID) over sequence (per-connection counter)
  private seenEventIds = new Set<string>();
  private seenRing: string[] = [];
  private static readonly MAX_DEDUPE_RING = 250;

  constructor() {
    // Listen for online/offline events
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        if (this.shouldReconnect && this.currentStatus === 'DISCONNECTED') {
          this.connect();
        }
      });
      window.addEventListener('offline', () => {
        this.setStatus('DISCONNECTED');
      });
    }
  }

  public async connect(): Promise<void> {
    if (
      this.ws &&
      (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    this.setStatus('CONNECTING');
    this.shouldReconnect = true;

    // ── Token refresh guard ───────────────────────────────────────────────────
    let token = getAccessToken();

    if (isTokenExpiredOrSoon(token) && !this.isRefreshing) {
      this.isRefreshing = true;
      const refreshed = await silentRefresh();
      this.isRefreshing = false;

      if (refreshed) {
        token = refreshed;
      } else {
        // Refresh failed — session truly expired, don't try to connect
        this.setStatus('DISCONNECTED');
        // Emit a synthetic auth-expired event so the UI can redirect to login
        this.dispatch('auth.expired', {});
        return;
      }
    }

    if (!token) {
      this.setStatus('DISCONNECTED');
      return;
    }
    // ─────────────────────────────────────────────────────────────────────────

    const resolveAdminWs = (): string => {
      const customWs = import.meta.env.VITE_WS_URL;
      if (customWs && typeof customWs === 'string' && customWs.trim()) {
        return customWs.trim().replace(/\/+$/, '');
      }
      const apiBase = import.meta.env.VITE_API_BASE_URL;
      if (apiBase && typeof apiBase === 'string' && apiBase.trim()) {
        const cleanApi = apiBase.trim().replace(/\/+$/, '');
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
    };

    // The token is NOT put in the URL (it would leak into proxy/access logs). It is sent as
    // the first frame right after the socket opens; the backend closes with 4001 if invalid.
    const wsUrl = resolveAdminWs();
    const authToken: string = token;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.ws?.send(JSON.stringify({ type: 'auth', token: authToken }));
        this.setStatus('CONNECTED');
        this.startHeartbeat();
        if (this.reconnectTimeout) {
          clearTimeout(this.reconnectTimeout);
          this.reconnectTimeout = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          // Heartbeat reply: never dispatch it (wildcard listeners would refetch every 30 s).
          if (payload.type === 'pong') return;
          // Deduplicate using event_id (globally unique UUID, stable across reconnects).
          // Fall back to namespaced sequence so reconnects don't match old seq numbers.
          const dedupeId: string | undefined =
            payload.event_id ??
            (payload.sequence !== undefined ? `seq:${payload.sequence}` : undefined);
          if (dedupeId) {
            if (this.seenEventIds.has(dedupeId)) return;
            this.seenEventIds.add(dedupeId);
            this.seenRing.push(dedupeId);
            if (this.seenRing.length > AdminWebSocketClient.MAX_DEDUPE_RING) {
              const evicted = this.seenRing.shift()!;
              this.seenEventIds.delete(evicted);
            }
          }
          const eventName = payload.event || payload.type;
          if (eventName) {
            this.dispatch(eventName, payload.data || payload);
          }
        } catch {
          // Non-JSON ping
        }
      };

      this.ws.onclose = (ev) => {
        this.stopHeartbeat();
        this.setStatus('DISCONNECTED');
        // Code 4001 = CLOSE_SESSION_REVOKED from backend (token rejected)
        // In this case force a refresh on next reconnect attempt.
        if (ev.code === 4001 || ev.code === 4008) {
          // Clear the stored token so next connect() triggers a refresh
          dropAccessToken();
        }
        this.scheduleReconnect();
      };

      this.ws.onerror = () => {
        this.setStatus('DISCONNECTED');
      };
    } catch {
      this.setStatus('DISCONNECTED');
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.shouldReconnect = false;
    this.stopHeartbeat();
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.setStatus('DISCONNECTED');
  }

  /**
   * 30 s application ping (same as the waiter, kitchen and customer clients). It keeps idle
   * proxies from dropping the socket and counts as inbound WebSocket traffic, which delays
   * the Render free-plan idle spin-down while an admin screen is open.
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30_000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (!this.shouldReconnect) return;
    if (this.reconnectTimeout) return;

    this.reconnectTimeout = setTimeout(() => {
      this.reconnectTimeout = null;
      this.connect();
    }, 3000);
  }

  private setStatus(status: ConnectionStatus): void {
    this.currentStatus = status;
    this.statusListeners.forEach((listener) => listener(status));
  }

  public onStatusChange(callback: (status: ConnectionStatus) => void): () => void {
    this.statusListeners.add(callback);
    callback(this.currentStatus);
    return () => {
      this.statusListeners.delete(callback);
    };
  }

  public on(event: string, handler: EventHandler): () => void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(handler);
    return () => {
      this.eventListeners.get(event)?.delete(handler);
    };
  }

  private dispatch(event: string, data: any): void {
    // Specific listeners
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach((h) => h(data));
    }
    // Wildcard listeners
    const allListeners = this.eventListeners.get('*');
    if (allListeners) {
      allListeners.forEach((h) => h({ event, data }));
    }
  }
}

export const adminWs = new AdminWebSocketClient();
