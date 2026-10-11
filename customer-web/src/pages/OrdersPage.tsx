import React, { useState, useEffect, useCallback } from 'react';
import { listOrders } from '../api';
import type { OrderResponse } from '../types';
import { OrderStatusTimeline } from '../components/OrderStatusTimeline';
import { useSession } from '../context/SessionContext';
import { customerWs, type WsEvent } from '../customerWs';
import { formatInr } from '../utils/currency';
import { PlusCircle, RefreshCw, AlertCircle, ShoppingBag } from 'lucide-react';

interface OrdersPageProps {
  onBackToMenu: () => void;
}

export const OrdersPage: React.FC<OrdersPageProps> = ({ onBackToMenu }) => {
  const { sessionToken, currentOutstanding, customLimit, refreshSession } = useSession();

  const [orders, setOrders] = useState<OrderResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

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
    <div className="min-h-screen bg-slate-950 text-slate-100 pb-20">
      <div className="max-w-md mx-auto px-4 py-4 space-y-4">
        {/* Top Summary Banner */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4 flex items-center justify-between shadow-sm">
          <div>
            <span className="text-xs text-slate-400 block">Total Table Exposure</span>
            <div className="flex items-baseline space-x-1.5 mt-0.5">
              <span className="text-xl font-bold text-white">
                {formatInr(outstandingNum)}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                / {formatInr(limitNum)}
              </span>
            </div>
            {isLimitLocked && (
              <span className="text-[10px] text-rose-400 font-semibold block mt-1">
                Limit Reached — Ask waiter to settle
              </span>
            )}
          </div>

          <button
            onClick={() => loadOrders(false)}
            className="p-2.5 rounded-xl bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
            title="Refresh orders"
          >
            <RefreshCw size={16} />
          </button>
        </div>

        {/* Action Button: Order More Dishes */}
        <button
          onClick={onBackToMenu}
          className="w-full bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 hover:border-slate-600 text-orange-400 hover:text-orange-300 font-semibold py-3 px-4 rounded-2xl flex items-center justify-center space-x-2 text-xs transition shadow-sm"
        >
          <PlusCircle size={16} />
          <span>Add More Dishes from Menu</span>
        </button>

        {/* Orders List */}
        {isLoading ? (
          <div className="space-y-4 pt-2">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-5 animate-pulse space-y-4"
              >
                <div className="h-4 bg-slate-800 rounded w-1/4"></div>
                <div className="h-8 bg-slate-800/50 rounded"></div>
                <div className="h-16 bg-slate-800/30 rounded"></div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center space-y-3">
            <AlertCircle size={28} className="text-rose-400 mx-auto" />
            <p className="text-xs text-slate-300">{error}</p>
            <button
              onClick={() => loadOrders(false)}
              className="bg-orange-500 text-white text-xs font-semibold px-4 py-2 rounded-xl"
            >
              Retry
            </button>
          </div>
        ) : orders.length === 0 ? (
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-8 text-center space-y-3 my-6">
            <div className="w-12 h-12 rounded-2xl bg-slate-800 text-slate-500 flex items-center justify-center mx-auto">
              <ShoppingBag size={24} />
            </div>
            <h3 className="font-semibold text-slate-200 text-sm">No orders placed yet</h3>
            <p className="text-xs text-slate-400 max-w-xs mx-auto leading-relaxed">
              Scan through our menu, add your favorite items to cart, and send them directly to the kitchen.
            </p>
            <button
              onClick={onBackToMenu}
              className="mt-2 bg-orange-500 hover:bg-orange-600 text-white font-semibold py-2.5 px-5 rounded-xl text-xs inline-flex items-center space-x-2 transition shadow-lg shadow-orange-500/20"
            >
              <span>Explore Menu</span>
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-400 px-1">
              <span className="font-semibold uppercase tracking-wider">
                Live Orders ({orders.length})
              </span>
              <span className="flex items-center space-x-1 text-[11px] text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>Live Status</span>
              </span>
            </div>

            {orders.map((order) => (
              <OrderStatusTimeline key={order.id} order={order} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
