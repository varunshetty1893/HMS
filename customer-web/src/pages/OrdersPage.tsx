import React, { useState, useEffect, useCallback } from 'react';
import { listOrders, cancelCustomerOrder, modifyCustomerOrder, getMenu } from '../api';
import type { CustomerItemChange, MenuItem, OrderResponse } from '../types';
import { OrderStatusTimeline } from '../components/OrderStatusTimeline';
import { useSession } from '../context/SessionContext';
import { customerWs, type WsEvent } from '../customerWs';
import { formatInr } from '../utils/currency';
import { PlusCircle, RefreshCw, AlertCircle, ShoppingBag, Receipt } from 'lucide-react';

interface OrdersPageProps {
  onBackToMenu: () => void;
}

export const OrdersPage: React.FC<OrdersPageProps> = ({ onBackToMenu }) => {
  const { sessionToken, currentOutstanding, customLimit, refreshSession } = useSession();

  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // menu_item_id -> MenuItem, so the edit panel can offer cheaper portions (Full -> Half)
  const [menuItems, setMenuItems] = useState<Record<string, MenuItem>>({});
  useEffect(() => {
    let alive = true;
    getMenu()
      .then((menu) => {
        if (!alive) return;
        const map: Record<string, MenuItem> = {};
        menu.categories.forEach((c) => c.items.forEach((i) => (map[i.id] = i)));
        setMenuItems(map);
      })
      .catch(() => {
        /* edit still works for quantities; portion switch just stays hidden */
      });
    return () => {
      alive = false;
    };
  }, []);

  const loadOrders = useCallback(async (quiet = false) => {
    if (!quiet) setIsLoading(true);
    setError(null);
    try {
      const data = await listOrders();
      setOrders(data);
      if (!quiet) setIsLoading(false);
    } catch {
      if (!quiet) {
        setError('Failed to fetch active orders.');
        setIsLoading(false);
      }
    }
  }, []);

  const handleCancelOrder = useCallback(async (orderId: string) => {
    await cancelCustomerOrder(orderId);
    await loadOrders(false);
    refreshSession();
  }, [loadOrders, refreshSession]);

  const handleModifyOrder = useCallback(
    async (orderId: string, expectedVersion: number, changes: CustomerItemChange[]) => {
      await modifyCustomerOrder(orderId, expectedVersion, changes);
      await loadOrders(true);
      refreshSession();
    },
    [loadOrders, refreshSession],
  );

  useEffect(() => {
    loadOrders();
    refreshSession();
  }, [loadOrders, refreshSession]);

  // Connect WebSocket for live order status updates
  useEffect(() => {
    if (!sessionToken) return;

    customerWs.connect(sessionToken);

    const unsubscribe = customerWs.onEvent((evt: WsEvent) => {
      // Whenever order status change occurs, reload orders quietly
      if (
        evt.event?.startsWith('order.') ||
        evt.event?.startsWith('table.') ||
        evt.type === 'order_status_update'
      ) {
        loadOrders(true);
        refreshSession();
      }
    });

    // Fallback polling every 10s for resilience
    const pollTimer = setInterval(() => {
      loadOrders(true);
    }, 10_000);

    return () => {
      unsubscribe();
      clearInterval(pollTimer);
    };
  }, [sessionToken, loadOrders, refreshSession]);

  const outstandingNum = parseFloat(currentOutstanding) || 0;
  const limitNum = parseFloat(customLimit) || 5000;
  const isLimitLocked = outstandingNum >= limitNum;

  return (
    <div
      className="min-h-screen pb-24"
      style={{ background: 'var(--cream, #FFF8ED)' }}
    >
      <div className="max-w-4xl mx-auto px-4 py-4 space-y-4">
        {/* Top Summary Banner */}
        <div
          className="rounded-2xl p-4 flex items-center justify-between shadow-sm"
          style={{
            background: 'var(--white)',
            border: '1px solid var(--border)',
          }}
        >
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold" style={{ color: 'var(--text-muted)' }}>
              <Receipt size={14} style={{ color: 'var(--primary)' }} />
              <span>Current Table Bill Total</span>
            </div>
            <div className="flex items-baseline gap-2 mt-1">
              <span
                className="text-2xl font-bold font-mono tracking-tight"
                style={{ color: 'var(--text-primary)' }}
              >
                {formatInr(outstandingNum)}
              </span>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                of {formatInr(limitNum)} limit
              </span>
            </div>
            {isLimitLocked && (
              <span className="text-[11px] font-semibold block mt-1.5 text-red-600">
                Limit Reached — Please ask your waiter to settle or verify.
              </span>
            )}
          </div>

          <button
            onClick={() => loadOrders(false)}
            className="p-2.5 rounded-xl transition-all"
            style={{
              background: 'var(--bg-subtle)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border)',
            }}
            title="Refresh orders"
          >
            <RefreshCw size={16} />
          </button>
        </div>

        {/* Action Button: Order More Dishes */}
        <button
          onClick={onBackToMenu}
          className="w-full py-3.5 px-4 rounded-2xl flex items-center justify-center gap-2 text-sm font-semibold transition-all shadow-sm cursor-pointer"
          style={{
            background: 'var(--primary)',
            color: '#FFFFFF',
            boxShadow: '0 4px 14px rgba(217, 93, 43, 0.25)',
          }}
        >
          <PlusCircle size={18} />
          <span>Add More Dishes to Table</span>
        </button>

        {/* Orders List */}
        {isLoading ? (
          <div className="space-y-4 pt-2">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="rounded-2xl p-5 space-y-4 animate-pulse"
                style={{
                  background: 'var(--white)',
                  border: '1px solid var(--border)',
                }}
              >
                <div className="h-4 bg-orange-100/60 rounded w-1/3"></div>
                <div className="h-8 bg-orange-50/50 rounded"></div>
                <div className="h-16 bg-orange-50/30 rounded"></div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div
            className="rounded-2xl p-6 text-center space-y-3"
            style={{
              background: 'var(--white)',
              border: '1px solid var(--border)',
            }}
          >
            <AlertCircle size={32} className="mx-auto text-red-500" />
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {error}
            </p>
            <button
              onClick={() => loadOrders(false)}
              className="text-white text-xs font-semibold px-5 py-2.5 rounded-xl transition-all"
              style={{ background: 'var(--primary)' }}
            >
              Retry
            </button>
          </div>
        ) : orders.length === 0 ? (
          <div
            className="rounded-2xl p-8 text-center space-y-3 my-6"
            style={{
              background: 'var(--white)',
              border: '1px solid var(--border)',
              boxShadow: '0 2px 10px rgba(40, 40, 32, 0.04)',
            }}
          >
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto"
              style={{
                background: 'var(--primary-bg)',
                color: 'var(--primary)',
              }}
            >
              <ShoppingBag size={28} />
            </div>
            <h3
              className="font-bold text-base"
              style={{ color: 'var(--text-primary)' }}
            >
              No orders placed yet
            </h3>
            <p
              className="text-xs max-w-xs mx-auto leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}
            >
              Browse our freshly prepared dishes, customize variants, and place your order directly to the kitchen.
            </p>
            <button
              onClick={onBackToMenu}
              className="mt-2 text-white font-semibold py-2.5 px-6 rounded-xl text-xs inline-flex items-center gap-2 transition-all shadow-md cursor-pointer"
              style={{
                background: 'var(--primary)',
                boxShadow: '0 4px 14px rgba(217, 93, 43, 0.25)',
              }}
            >
              <span>Explore SpiceHub Menu</span>
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs px-1">
              <span
                className="font-bold uppercase tracking-wider text-[11px]"
                style={{ color: 'var(--text-muted)' }}
              >
                Table Orders ({orders.length})
              </span>
              <span
                className="flex items-center gap-1.5 text-[11px] font-semibold"
                style={{ color: 'var(--green)' }}
              >
                <span
                  className="w-2 h-2 rounded-full animate-pulse"
                  style={{ background: 'var(--green)' }}
                />
                <span>Live Kitchen Status</span>
              </span>
            </div>

            {orders.map((order) => (
              <OrderStatusTimeline
                key={order.id}
                order={order}
                onCancelOrder={handleCancelOrder}
                onModifyOrder={handleModifyOrder}
                menuItems={menuItems}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
