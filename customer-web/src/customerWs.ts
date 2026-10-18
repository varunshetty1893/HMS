// ─────────────────────────────────────────────────────────────────────────────
// customerWs.ts — WebSocket client for live order status updates
//
// Follows docs/08 reconnect spec:
// - Exponential backoff with jitter (1s → 2s → 4s → max 30s)
// - 30s heartbeat ping
// - Reconnects automatically on disconnect / mobile app resume
// - 250-event deduplication ring buffer (sequence-based)
// ─────────────────────────────────────────────────────────────────────────────

import { resolveWsBaseUrl } from './utils/env';

const WS_BASE = resolveWsBaseUrl();
const MAX_BACKOFF_MS = 30_000;
const HEARTBEAT_INTERVAL_MS = 30_000;
const MAX_DEDUPE_RING = 250;

type WsEventHandler = (event: WsEvent) => void;

export interface WsEvent {
  event: string;
  [key: string]: unknown;
}

class CustomerWebSocketClient {
  private ws: WebSocket | null = null;
  private sessionToken: string | null = null;
  private reconnectAttempt = 0;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private seenEventIds = new Set<string>();
  private seenRing: string[] = [];
  private handlers: WsEventHandler[] = [];
  private destroyed = false;

  connect(sessionToken: string): void {
    this.sessionToken = sessionToken;
    this.destroyed = false;
    this._doConnect();
  }

  disconnect(): void {
    this.destroyed = true;
    this._clearTimers();
    if (this.ws) {
      this.ws.close(1000, 'CLIENT_DISCONNECT');
      this.ws = null;
    }
  }

  onEvent(handler: WsEventHandler): () => void {
    this.handlers.push(handler);
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler);
    };
  }

  private _doConnect(): void {
    if (this.destroyed) return;

    const url = `${WS_BASE}?customer_token=${encodeURIComponent(this.sessionToken ?? '')}`;
    try {
      this.ws = new WebSocket(url);
    } catch {
      this._scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempt = 0;
      this._startHeartbeat();
    };

    this.ws.onmessage = (msg: MessageEvent<string>) => {
      try {
        const data = JSON.parse(msg.data) as WsEvent;
        if (this._isDuplicate(data)) return;
        this.handlers.forEach((h) => h(data));
      } catch { /* ignore malformed frames */ }
    };

    this.ws.onclose = () => {
      this._clearTimers();
      if (!this.destroyed) this._scheduleReconnect();
    };

    this.ws.onerror = () => {
      this.ws?.close();
    };
  }

  private _isDuplicate(event: WsEvent): boolean {
    // Prefer event_id (globally unique UUID hex, stable across reconnects) over
    // sequence (per-connection counter that resets to 0 on every new socket).
    // Using sequence as the primary key caused legitimate new events arriving
    // after a reconnect to be silently dropped because their low sequence numbers
    // matched previously-seen values from the prior connection.
    const id =
      (event.event_id as string | undefined) ??
      (event.sequence !== undefined ? `seq:${event.sequence}` : undefined);
    if (!id) return false;
    if (this.seenEventIds.has(id)) return true;
    this.seenEventIds.add(id);
    this.seenRing.push(id);
    if (this.seenRing.length > MAX_DEDUPE_RING) {
      const evicted = this.seenRing.shift()!;
      this.seenEventIds.delete(evicted);
    }
    return false;
  }

  private _startHeartbeat(): void {
    this._clearTimers();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, HEARTBEAT_INTERVAL_MS);
  }

  private _scheduleReconnect(): void {
    if (this.destroyed) return;
    this.reconnectAttempt++;
    const baseDelay = Math.min(1000 * 2 ** (this.reconnectAttempt - 1), MAX_BACKOFF_MS);
    const jitter = Math.random() * 500;
    this.reconnectTimer = setTimeout(() => this._doConnect(), baseDelay + jitter);
  }

  private _clearTimers(): void {
    if (this.heartbeatTimer !== null) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
}

export const customerWs = new CustomerWebSocketClient();
