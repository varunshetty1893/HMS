import React from 'react';
import { AlertCircle, History, X } from 'lucide-react';
import { formatInr } from '@/utils/currency';
import { formatDateTimeIst } from '@/utils/dateIst';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Order } from '@/types/api';

interface OrderDetailDrawerProps {
  order: Order | null;
  onClose: () => void;
  onRequestVoid?: (order: Order) => void;
}

export const OrderDetailDrawer: React.FC<OrderDetailDrawerProps> = ({
  order,
  onClose,
  onRequestVoid,
}) => {
  if (!order) return null;

  const canCancel =
    order.status !== 'COMPLETED' &&
    order.status !== 'CANCELLED' &&
    order.status !== 'REJECTED';

  const formatSourceLabel = (src: string) => {
    if (src === 'CUSTOMER_QR') return 'Customer QR';
    if (src === 'WAITER') return 'Waiter App';
    return src;
  };

  const formatModType = (mod: string) => {
    switch (mod) {
      case 'ITEM_QUANTITY_INCREASED':
        return 'Quantity Increased';
      case 'ITEM_QUANTITY_DECREASED':
        return 'Quantity Reduced';
      case 'ITEM_CANCELLED':
        return 'Dish Cancelled';
      case 'ORDER_CANCELLED':
        return 'Order Cancelled';
      default:
        return mod.replace(/_/g, ' ');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-xs">
      <div className="w-full max-w-lg bg-white border-l border-gray-200 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-gray-900">{order.order_number}</h2>
              <StatusBadge status={order.status} />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Table #{order.table_number || '—'} • Ordered via: {formatSourceLabel(order.source)} • Placed: {formatDateTimeIst(order.placed_at)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-700 cursor-pointer"
            title="Close details"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Order Items */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-gray-600 mb-3">
              Ordered Dishes ({order.items?.length || 0})
            </h3>
            <div className="divide-y divide-gray-100 rounded-2xl border border-gray-200 bg-slate-50 overflow-hidden">
              {order.items && order.items.length > 0 ? (
                order.items.map((item, idx) => (
                  <div key={item.id || item.item_code || `item-${idx}`} className="p-3.5 flex items-start justify-between bg-white">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-brand-700 bg-orange-100 px-1.5 py-0.5 rounded border border-orange-200">
                          {item.item_code}
                        </span>
                        <span className="text-sm font-semibold text-gray-900">{item.item_name}</span>
                        <span className="text-xs text-gray-500">({item.variant_name})</span>
                      </div>
                      {item.item_notes && (
                        <p className="text-xs text-amber-700 mt-1 italic">Customer Note: "{item.item_notes}"</p>
                      )}
                      <div className="text-xs text-gray-500 mt-1">
                        Qty: <strong className="text-gray-900">{item.active_quantity}</strong>
                        {item.cancelled_quantity > 0 && (
                          <span className="text-rose-600 ml-1.5 font-medium">
                            ({item.cancelled_quantity} cancelled)
                          </span>
                        )}
                        <span className="mx-2">•</span>
                        <span>{formatInr(item.unit_price_snapshot)} each</span>
                      </div>
                    </div>
                    <div className="text-right font-mono font-semibold text-sm text-gray-900">
                      {formatInr(item.line_subtotal)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-6 text-xs text-gray-400 text-center">No dishes attached to this order</div>
              )}
            </div>

            <div className="mt-4 flex items-center justify-between px-2">
              <span className="text-sm text-gray-600">Order Subtotal:</span>
              <span className="text-base font-bold font-mono text-gray-900">
                {formatInr(order.order_subtotal)}
              </span>
            </div>
          </div>

          {/* Modification History */}
          {order.modification_events && order.modification_events.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-600 mb-3">
                <History className="w-4 h-4 text-amber-600" />
                <span>Order Change History ({order.modification_events.length})</span>
              </div>
              <div className="space-y-2">
                {order.modification_events.map((ev, idx) => (
                  <div
                    key={ev.id || `ev-${idx}`}
                    className="p-3 rounded-xl border border-amber-200 bg-amber-50 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between text-amber-800 font-semibold">
                      <span>{formatModType(ev.modification_type)}</span>
                      <span className="text-[10px] text-gray-500 font-mono">
                        {formatDateTimeIst(ev.created_at)}
                      </span>
                    </div>
                    <p className="text-gray-700">
                      Quantity: {ev.previous_quantity} → <strong className="text-gray-900">{ev.new_quantity}</strong> changed by{' '}
                      <span className="text-amber-800 font-mono font-semibold">@{ev.modified_by_role}</span>
                    </p>
                    {ev.reason && <p className="text-gray-600 italic">"{ev.reason}"</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reason if cancelled/rejected */}
          {(order.cancellation_reason || order.rejection_reason) && (
            <div className="p-4 rounded-xl border border-rose-200 bg-rose-50">
              <div className="flex items-center gap-2 text-rose-700 font-bold text-xs uppercase tracking-wider mb-1">
                <AlertCircle className="w-4 h-4" />
                <span>Reason for Cancellation / Rejection</span>
              </div>
              <p className="text-sm text-rose-800">
                {order.cancellation_reason || order.rejection_reason}
              </p>
            </div>
          )}
        </div>

        {/* Footer Emergency Cancel action */}
        {canCancel && onRequestVoid && (
          <div className="p-6 border-t border-gray-200 bg-slate-50">
            <button
              onClick={() => onRequestVoid(order)}
              className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-300 transition cursor-pointer"
            >
              Emergency Cancel Order
            </button>
            <p className="text-[11px] text-gray-500 text-center mt-2">
              Cancels the entire order, stops the kitchen, and removes charges from the bill.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
