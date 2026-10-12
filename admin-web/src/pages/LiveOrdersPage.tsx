import React, { useEffect, useState } from 'react';
import { ordersBillsApi } from '@/api/ordersBillsApi';
import { adminWs } from '@/realtime/adminWs';
import { formatInr } from '@/utils/currency';
import { formatDateTimeIst } from '@/utils/dateIst';
import { StatusBadge } from '@/components/common/StatusBadge';
import { OrderDetailDrawer } from '@/components/orders/OrderDetailDrawer';
import { ConfirmModal } from '@/components/common/ConfirmModal';
import { usePageTheme } from '@/hooks/usePageTheme';
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Flame,
  Search,
  X,
} from 'lucide-react';
import { Order, OrderReportItem } from '@/types/api';

const STATUS_TABS: { label: string; value: string }[] = [
  { label: 'Active Orders', value: 'ACTIVE' },
  { label: 'All Orders', value: 'ALL' },
  { label: 'New (Placed)', value: 'PLACED' },
  { label: 'Accepted', value: 'ACCEPTED' },
  { label: 'Cooking', value: 'PREPARING' },
  { label: 'Ready to Serve', value: 'READY' },
  { label: 'Served', value: 'SERVED' },
  { label: 'Completed', value: 'COMPLETED' },
  { label: 'Cancelled', value: 'CANCELLED' },
];

export const LiveOrdersPage: React.FC = () => {
  const { L, heading, sub, muted, border, card, tableWrap, thead, tbodyRowHover, input, select, tabActive, tabInactive } = usePageTheme();

  const [orders, setOrders] = useState<OrderReportItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ACTIVE');
  const [sourceFilter, setSourceFilter] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Modal / Drawer state
  const [selectedOrder, setSelectedOrder] = useState<Order | null>(null);
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
      setError(err?.message || 'Failed to fetch restaurant orders');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
    const unsub = adminWs.on('*', () => { fetchOrders(); });
    return () => { unsub(); };
  }, [statusFilter, sourceFilter]);

  // Reset pagination to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [statusFilter, sourceFilter, searchQuery, pageSize]);

  const handleOpenDetail = (item: OrderReportItem) => {
    const raw = item as any;
    const fullOrder: Order = {
      id: item.order_id || raw.id || '',
      order_number: item.order_number,
      table_id: raw.table_id || '',
      table_session_id: raw.table_session_id || '',
      source: (item.source || 'CUSTOMER_QR') as any,
      status: (item.status || 'PLACED') as any,
      order_subtotal: item.order_subtotal || '0.00',
      placed_at: item.placed_at,
      accepted_at: raw.accepted_at || null,
      preparing_at: raw.preparing_at || null,
      ready_at: raw.ready_at || null,
      served_at: raw.served_at || null,
      completed_at: item.completed_at || null,
      cancelled_at: raw.cancelled_at || null,
      rejected_at: raw.rejected_at || null,
      cancellation_reason: raw.cancellation_reason || null,
      rejection_reason: raw.rejection_reason || null,
      version: raw.version || 1,
      has_unacknowledged_mods: raw.has_unacknowledged_mods || false,
      table_number: item.table_number,
      items: raw.items || [],
      modification_events: raw.modification_events || [],
    };
    setSelectedOrder(fullOrder);
  };

  const handleConfirmCancelOrder = async (reason?: string) => {
    if (!orderToVoid) return;
    try {
      await ordersBillsApi.voidOrder(
        orderToVoid.id,
        orderToVoid.version || 1,
        reason || 'Emergency cancellation by admin'
      );
      setSuccessBanner(`Order #${orderToVoid.order_number} has been cancelled successfully.`);
      setOrderToVoid(null);
      setSelectedOrder(null);
      fetchOrders();
      setTimeout(() => setSuccessBanner(null), 5000);
    } catch (err: any) {
      setError(err?.message || 'Failed to cancel order');
    }
  };

  // Filter logic
  const filteredOrders = orders.filter((o) => {
    if (statusFilter === 'ACTIVE') {
      if (!['PLACED', 'ACCEPTED', 'PREPARING', 'READY', 'SERVED'].includes(o.status)) {
        return false;
      }
    }
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      o.order_number.toLowerCase().includes(q) ||
      String(o.table_number).includes(q)
    );
  });

  // Pagination calculation
  const totalItems = filteredOrders.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
  const safeCurrentPage = Math.min(currentPage, totalPages);
  const startIndex = (safeCurrentPage - 1) * pageSize;
  const paginatedOrders = filteredOrders.slice(startIndex, startIndex + pageSize);

  return (
    <div className="p-8 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight flex items-center gap-2.5" style={{ color: heading }}>
            <Flame className="w-6 h-6 text-brand-500" />
            <span>Live Orders</span>
          </h1>
          <p className="text-sm mt-1" style={{ color: sub }}>
            Real-time orders from dining tables. Track kitchen cooking progress, see dish details, or cancel orders if a customer walks out.
          </p>
        </div>
      </div>

      {/* Success Banner */}
      {successBanner && (
        <div
          className="p-4 rounded-2xl text-xs flex items-center justify-between animate-in fade-in"
          style={{
            backgroundColor: L ? '#dcfce7' : 'rgba(5,46,22,0.6)',
            borderColor: L ? '#bbf7d0' : '#166534',
            borderWidth: 1,
            borderStyle: 'solid',
            color: L ? '#15803d' : '#86efac',
          }}
        >
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successBanner}</span>
          </div>
          <button onClick={() => setSuccessBanner(null)} className="cursor-pointer opacity-80 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div
          className="p-4 rounded-2xl text-xs flex items-center justify-between"
          style={{
            backgroundColor: L ? '#fee2e2' : 'rgba(69,10,10,0.6)',
            borderColor: L ? '#fecaca' : '#991b1b',
            borderWidth: 1,
            borderStyle: 'solid',
            color: L ? '#b91c1c' : '#fca5a5',
          }}
        >
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="cursor-pointer opacity-80 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Status Filter Tabs & Search Bar */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
          {STATUS_TABS.map((tab) => {
            const isActive = statusFilter === tab.value;
            return (
              <button
                key={tab.value}
                onClick={() => setStatusFilter(tab.value)}
                className="px-3.5 py-1.5 rounded-xl text-xs font-semibold shrink-0 transition cursor-pointer"
                style={isActive ? tabActive : tabInactive}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
          <div className="flex items-center gap-3">
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              className="px-3.5 py-2 rounded-xl text-xs focus:outline-none"
              style={select}
            >
              <option value="ALL">All Ordering Sources</option>
              <option value="CUSTOMER_QR">Customer QR Code</option>
              <option value="WAITER">Waiter App</option>
            </select>

            <span className="text-xs" style={{ color: muted }}>
              Found {totalItems} {totalItems === 1 ? 'order' : 'orders'}
            </span>
          </div>

          <div className="relative w-full sm:w-72">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: muted }} />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by Order # or Table #..."
              className="w-full pl-10 pr-4 py-2 rounded-xl text-xs focus:outline-none"
              style={input}
            />
          </div>
        </div>
      </div>

      {/* Orders Table */}
      {isLoading ? (
        <div
          className="p-16 text-center rounded-2xl"
          style={{ ...card, color: muted }}
        >
          <div className="inline-block w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <p className="mt-3 text-sm">Loading live orders...</p>
        </div>
      ) : paginatedOrders.length === 0 ? (
        <div
          className="p-16 text-center rounded-2xl"
          style={{ ...card, color: sub }}
        >
          <Flame className="w-8 h-8 mx-auto mb-2" style={{ color: muted }} />
          <p className="font-semibold" style={{ color: heading }}>No orders found</p>
          <p className="text-xs mt-1" style={{ color: muted }}>
            {searchQuery
              ? 'No orders match your search criteria.'
              : 'There are no orders with this status right now.'}
          </p>
        </div>
      ) : (
        <div className="rounded-2xl overflow-hidden shadow-xl" style={tableWrap}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm" style={{ color: heading }}>
              <thead className="text-xs uppercase tracking-wider border-b" style={{ ...thead, borderBottomColor: border }}>
                <tr>
                  <th className="px-6 py-4 font-semibold">Order #</th>
                  <th className="px-6 py-4 font-semibold">Table</th>
                  <th className="px-6 py-4 font-semibold">Source</th>
                  <th className="px-6 py-4 font-semibold">Status</th>
                  <th className="px-6 py-4 font-semibold">Placed Time</th>
                  <th className="px-6 py-4 font-semibold text-right">Total Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y" style={{ borderColor: border }}>
                {paginatedOrders.map((o, idx) => {
                  const rowKey = o.order_id || (o as any).id || o.order_number || `live-ord-${startIndex + idx}`;
                  return (
                    <tr
                      key={rowKey}
                      onClick={() => handleOpenDetail(o)}
                      className="transition cursor-pointer border-b"
                      style={{
                        borderBottomColor: border,
                        backgroundColor: 'transparent',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = tbodyRowHover.backgroundColor as string;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      <td className="px-6 py-4 font-mono font-bold flex items-center gap-2" style={{ color: heading }}>
                        <Flame className="w-4 h-4 text-brand-500 shrink-0" />
                        <span>{o.order_number}</span>
                      </td>
                      <td className="px-6 py-4 font-semibold" style={{ color: heading }}>
                        Table {o.table_number}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className="text-xs px-2.5 py-1 rounded-md font-mono font-semibold"
                          style={{
                            backgroundColor: L ? '#f5f0e8' : 'rgba(30,41,59,0.8)',
                            color: L ? '#5a5545' : '#cbd5e1',
                            border: `1px solid ${border}`,
                          }}
                        >
                          {o.source === 'CUSTOMER_QR' ? 'Customer QR' : o.source === 'WAITER' ? 'Waiter App' : o.source}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <StatusBadge status={o.status} size="sm" />
                      </td>
                      <td className="px-6 py-4 text-xs font-mono" style={{ color: muted }}>
                        {formatDateTimeIst(o.placed_at)}
                      </td>
                      <td className="px-6 py-4 text-right font-mono font-bold" style={{ color: heading }}>
                        {formatInr(o.order_subtotal)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          <div
            className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 px-6 py-4 border-t text-xs"
            style={{
              backgroundColor: L ? '#faf7f2' : 'rgba(2,6,23,0.5)',
              borderTopColor: border,
              color: sub,
            }}
          >
            <div className="flex items-center gap-3">
              <span>
                Showing {totalItems === 0 ? 0 : startIndex + 1} to{' '}
                {Math.min(startIndex + pageSize, totalItems)} of {totalItems} orders
              </span>
              <div className="flex items-center gap-1.5 ml-2">
                <span style={{ color: muted }}>Per page:</span>
                <select
                  value={pageSize}
                  onChange={(e) => setPageSize(Number(e.target.value))}
                  className="rounded-lg px-2 py-1 text-xs focus:outline-none"
                  style={select}
                >
                  <option value={5}>5</option>
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                </select>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={safeCurrentPage <= 1}
                className="p-1.5 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                style={{
                  backgroundColor: L ? '#ffffff' : 'rgba(15,23,42,0.8)',
                  border: `1px solid ${border}`,
                  color: heading,
                }}
                title="Previous page"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>

              <span
                className="px-3 py-1 rounded-lg font-semibold"
                style={{
                  backgroundColor: L ? '#ffffff' : 'rgba(15,23,42,0.8)',
                  border: `1px solid ${border}`,
                  color: heading,
                }}
              >
                Page {safeCurrentPage} of {totalPages}
              </span>

              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={safeCurrentPage >= totalPages}
                className="p-1.5 rounded-lg disabled:opacity-40 disabled:cursor-not-allowed transition cursor-pointer"
                style={{
                  backgroundColor: L ? '#ffffff' : 'rgba(15,23,42,0.8)',
                  border: `1px solid ${border}`,
                  color: heading,
                }}
                title="Next page"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Order Detail Drawer */}
      <OrderDetailDrawer
        order={selectedOrder}
        onClose={() => setSelectedOrder(null)}
        onRequestVoid={(ord) => setOrderToVoid(ord)}
      />

      {/* Cancel Confirmation Modal */}
      <ConfirmModal
        isOpen={!!orderToVoid}
        title={`Emergency Cancel: Order #${orderToVoid?.order_number}`}
        description="This will immediately cancel all dishes in this order, notify the kitchen, and remove the charges from the customer's bill. Only use this if the customer walked out or the order was placed in error."
        confirmLabel="Yes, Cancel Order"
        cancelLabel="Keep Order"
        requireReason={true}
        reasonPlaceholder="e.g. Customer walked out / Wrong dishes ordered by mistake"
        variant="danger"
        onConfirm={handleConfirmCancelOrder}
        onCancel={() => setOrderToVoid(null)}
      />
    </div>
  );
};
