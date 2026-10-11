/**
 * WebSocket client for Admin Web.
 * Subscribes to room:admin, room:tables, room:waiters, room:kitchen, room:menu.
 */

type EventHandler = (data: any) => void;
type ConnectionStatus = 'CONNECTED' | 'CONNECTING' | 'DISCONNECTED';

class AdminWebSocketClient {
  private ws: WebSocket | null = null;
  private statusListeners: Set<(status: ConnectionStatus) => void> = new Set();
  private eventListeners: Map<string, Set<EventHandler>> = new Map();
  private reconnectTimeout: any = null;
  private currentStatus: ConnectionStatus = 'DISCONNECTED';
  private shouldReconnect = true;

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

  public connect(): void {
    const token = localStorage.getItem('hms_admin_access_token');
    if (!token) {
      this.setStatus('DISCONNECTED');
      return;
    }

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.setStatus('CONNECTING');
    this.shouldReconnect = true;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl =
      import.meta.env.VITE_WS_URL ||
      `${protocol}//${host}/api/v1/ws?token=${encodeURIComponent(token)}`;

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

      this.ws.onclose = () => {
        this.setStatus('DISCONNECTED');
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
