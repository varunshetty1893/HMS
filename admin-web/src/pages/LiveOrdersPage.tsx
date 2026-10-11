import React, { useEffect, useState } from 'react';
import { ordersBillsApi } from '@/api/ordersBillsApi';
import { adminWs } from '@/realtime/adminWs';
import { formatInr } from '@/utils/currency';
import { formatDateTimeIst } from '@/utils/dateIst';
import { StatusBadge } from '@/components/common/StatusBadge';
import { OrderDetailDrawer } from '@/components/orders/OrderDetailDrawer';
import { ConfirmModal } from '@/components/common/ConfirmModal';
import {
  Flame,
  Search,
} from 'lucide-react';
import { Order, OrderReportItem } from '@/types/api';

export const LiveOrdersPage: React.FC = () => {
  const [orders, setOrders] = useState<OrderReportItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ACTIVE');
  const [sourceFilter, setSourceFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected order for detail drawer
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);

  // Void confirmation
  const [orderToVoid, setOrderToVoid] = useState<Order | null>(null);

  const fetchOrders = async () => {
    try {
      const data = await ordersBillsApi.listOrders({
        status: statusFilter === 'ACTIVE' || statusFilter === 'ALL' ? undefined : statusFilter,
        source: sourceFilter === 'ALL' ? undefined : sourceFilter,
      });
      setOrders(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch floor orders');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();

    const unsub = adminWs.on('*', () => {
      fetchOrders();
    });

    return () => {
      unsub();
    };
  }, [statusFilter, sourceFilter]);

  const handleOpenDetail = (item: OrderReportItem) => {
    // Construct order model for drawer
    const fullOrder: Order = {
      id: item.order_id,
      order_number: item.order_number,
      table_id: '',
      table_session_id: '',
      source: item.source as any,
      status: item.status as any,
      order_subtotal: item.order_subtotal,
      placed_at: item.placed_at,
      accepted_at: null,
      preparing_at: null,
      ready_at: null,
      served_at: null,
      completed_at: item.completed_at,
      cancelled_at: null,
      rejected_at: null,
      cancellation_reason: null,
      rejection_reason: null,
      version: 1,
      has_unacknowledged_mods: false,
      table_number: item.table_number,
    };
    setSelectedOrder(fullOrder);
  };

  const handleConfirmVoid = async (reason?: string) => {
    if (!orderToVoid) return;
    try {
      await ordersBillsApi.voidOrder(
        orderToVoid.id,
        orderToVoid.version || 1,
        reason || 'Admin emergency cancellation'
      );
      alert(`Order ${orderToVoid.order_number} voided.`);
      setOrderToVoid(null);
      setSelectedOrder(null);
      fetchOrders();
    } catch (err: any) {
      alert(err?.message || 'Failed to void order');
    }
  };

  const filteredOrders = orders.filter((o) => {
    if (statusFilter === 'ACTIVE') {
      const activeStatuses = ['PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'SERVED'];
      if (!activeStatuses.includes(o.status)) return false;
    }
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      o.order_number.toLowerCase().includes(q) ||
      String(o.table_number).includes(q)
    );
  });

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white">Live Orders Oversight</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time kitchen order queue, modification diffs, and administrative overrides
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {['ACTIVE', 'ALL', 'PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'SERVED', 'COMPLETED', 'CANCELLED'].map(
            (st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold shrink-0 transition ${
                  statusFilter === st
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                {st}
              </button>
            )
          )}
        </div>

        <div className="flex items-center gap-3">
          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            className="px-3 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none"
          >
            <option value="ALL">All Sources</option>
            <option value="CUSTOMER_QR">Customer QR</option>
            <option value="WAITER">Waiter</option>
          </select>

          <div className="relative w-64">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by ORD # or Table..."
              className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>
      </div>

      {/* Orders List */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Loading orders...</div>
      ) : filteredOrders.length === 0 ? (
        <div className="p-12 text-center rounded-3xl bg-slate-900/40 border border-slate-800 text-slate-400">
          No orders match this status filter.
        </div>
      ) : (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-2xl">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-6 py-4 font-semibold">Order #</th>
                <th className="px-6 py-4 font-semibold">Table</th>
                <th className="px-6 py-4 font-semibold">Source</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold">Placed (IST)</th>
                <th className="px-6 py-4 font-semibold text-right">Subtotal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredOrders.map((o) => (
                <tr
                  key={o.order_id}
                  onClick={() => handleOpenDetail(o)}
                  className="hover:bg-slate-800/40 transition cursor-pointer"
                >
                  <td className="px-6 py-4 font-mono font-bold text-white flex items-center gap-2">
                    <Flame className="w-4 h-4 text-indigo-400" />
                    <span>{o.order_number}</span>
                  </td>
                  <td className="px-6 py-4 font-semibold text-slate-200">Table {o.table_number}</td>
                  <td className="px-6 py-4">
                    <span className="text-xs px-2 py-0.5 rounded font-mono font-semibold bg-slate-800 text-slate-300 border border-slate-700">
                      {o.source}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={o.status} size="sm" />
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-400 font-mono">
                    {formatDateTimeIst(o.placed_at)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono font-bold text-white">
                    {formatInr(o.order_subtotal)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Order Detail Drawer */}
      <OrderDetailDrawer
        order={selectedOrder}
        onClose={() => setSelectedOrder(null)}
        onRequestVoid={(ord) => setOrderToVoid(ord)}
      />

      {/* Emergency Void Confirmation */}
      <ConfirmModal
        isOpen={!!orderToVoid}
        title={`Emergency Void: ${orderToVoid?.order_number}`}
        description="This will immediately cancel all active items in this order, deduct from session exposure, and write an immutable audit log entry. Only perform this for customer walkouts or severe quality complaints."
        confirmLabel="Void Entire Order"
        requireReason={true}
        reasonPlaceholder="Customer complaint / order placed in error..."
        variant="danger"
        onConfirm={handleConfirmVoid}
        onCancel={() => setOrderToVoid(null)}
      />
    </div>
  );
};
