/**
 * WebSocket client for Admin Web.
 * Subscribes to room:admin, room:tables, room:waiters, room:kitchen, room:menu.
 *
 * Token refresh: Before each (re)connect attempt, if the stored access token
 * appears expired (via JWT exp claim), a silent refresh is attempted using the
 * stored refresh_token so that WebSocket connections are never rejected with 403.
 */

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

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
  const refreshToken = localStorage.getItem('hms_admin_refresh_token');
  if (!refreshToken) return null;
  try {
    const resp = await fetch(`${BASE_URL}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    if (data.access_token) {
      localStorage.setItem('hms_admin_access_token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('hms_admin_refresh_token', data.refresh_token);
      }
      return data.access_token;
    }
    return null;
  } catch {
    return null;
  }
}

class AdminWebSocketClient {
  private ws: WebSocket | null = null;
  private statusListeners: Set<(status: ConnectionStatus) => void> = new Set();
  private eventListeners: Map<string, Set<EventHandler>> = new Map();
  private reconnectTimeout: any = null;
  private currentStatus: ConnectionStatus = 'DISCONNECTED';
  private shouldReconnect = true;
  private isRefreshing = false;

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
    let token = localStorage.getItem('hms_admin_access_token');

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

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const baseWsUrl =
      import.meta.env.VITE_WS_URL || `${protocol}//${host}/api/v1/ws`;
    const separator = baseWsUrl.includes('?') ? '&' : '?';
    const wsUrl = `${baseWsUrl}${separator}token=${encodeURIComponent(token)}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.setStatus('CONNECTED');
        if (this.reconnectTimeout) {
          clearTimeout(this.reconnectTimeout);
          this.reconnectTimeout = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          const eventName = payload.event || payload.type;
          if (eventName) {
            this.dispatch(eventName, payload.data || payload);
          }
        } catch {
          // Non-JSON ping
        }
      };

      this.ws.onclose = (ev) => {
        this.setStatus('DISCONNECTED');
        // Code 4001 = CLOSE_SESSION_REVOKED from backend (token rejected)
        // In this case force a refresh on next reconnect attempt.
        if (ev.code === 4001 || ev.code === 4008) {
          // Clear the stored token so next connect() triggers a refresh
          localStorage.removeItem('hms_admin_access_token');
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
