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

  const canVoid =
    order.status !== 'COMPLETED' &&
    order.status !== 'CANCELLED' &&
    order.status !== 'REJECTED';

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs">
      <div className="w-full max-w-lg bg-slate-900 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-black text-white">{order.order_number}</h2>
              <StatusBadge status={order.status} />
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Table #{order.table_number || '—'} • Source: {order.source} • Placed: {formatDateTimeIst(order.placed_at)}
            </p>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Order Items */}
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
              Order Items ({order.items?.length || 0})
            </h3>
            <div className="divide-y divide-slate-800/60 rounded-2xl border border-slate-800 bg-slate-950/40 overflow-hidden">
              {order.items && order.items.length > 0 ? (
                order.items.map((item) => (
                  <div key={item.id} className="p-3.5 flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-indigo-400 bg-indigo-950/50 px-1.5 py-0.5 rounded border border-indigo-800/40">
                          {item.item_code}
                        </span>
                        <span className="text-sm font-semibold text-white">{item.item_name}</span>
                        <span className="text-xs text-slate-400">({item.variant_name})</span>
                      </div>
                      {item.item_notes && (
                        <p className="text-xs text-amber-400/90 mt-1 italic">Note: "{item.item_notes}"</p>
                      )}
                      <div className="text-xs text-slate-400 mt-1">
                        Qty: <strong className="text-slate-200">{item.active_quantity}</strong>
                        {item.cancelled_quantity > 0 && (
                          <span className="text-rose-400 ml-1.5 font-medium">
                            ({item.cancelled_quantity} cancelled)
                          </span>
                        )}
                        <span className="mx-2">•</span>
                        <span>{formatInr(item.unit_price_snapshot)} each</span>
                      </div>
                    </div>
                    <div className="text-right font-mono font-semibold text-sm text-white">
                      {formatInr(item.line_subtotal)}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 text-xs text-slate-500 text-center">No item data attached</div>
              )}
            </div>

            <div className="mt-4 flex items-center justify-between px-2">
              <span className="text-sm text-slate-400">Subtotal:</span>
              <span className="text-base font-bold font-mono text-white">
                {formatInr(order.order_subtotal)}
              </span>
            </div>
          </div>

          {/* Modification History */}
          {order.modification_events && order.modification_events.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
                <History className="w-4 h-4 text-amber-400" />
                <span>Modification Audit Trail ({order.modification_events.length})</span>
              </div>
              <div className="space-y-2">
                {order.modification_events.map((ev) => (
                  <div
                    key={ev.id}
                    className="p-3 rounded-xl border border-amber-900/30 bg-amber-950/20 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between text-amber-300 font-semibold">
                      <span>{ev.modification_type}</span>
                      <span className="text-[10px] text-slate-400 font-mono">
                        {formatDateTimeIst(ev.created_at)}
                      </span>
                    </div>
                    <p className="text-slate-300">
                      Qty: {ev.previous_quantity} → <strong className="text-white">{ev.new_quantity}</strong> by{' '}
                      <span className="text-amber-400 font-mono">@{ev.modified_by_role}</span>
                    </p>
                    <p className="text-slate-400 italic">"{ev.reason}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reason if cancelled/rejected */}
          {(order.cancellation_reason || order.rejection_reason) && (
            <div className="p-4 rounded-xl border border-rose-900/40 bg-rose-950/20">
              <div className="flex items-center gap-2 text-rose-400 font-bold text-xs uppercase tracking-wider mb-1">
                <AlertCircle className="w-4 h-4" />
                <span>{order.status} Reason</span>
              </div>
              <p className="text-sm text-rose-200">
                {order.cancellation_reason || order.rejection_reason}
              </p>
            </div>
          )}
        </div>

        {/* Footer actions */}
        {canVoid && onRequestVoid && (
          <div className="p-6 border-t border-slate-800 bg-slate-950/40">
            <button
              onClick={() => onRequestVoid(order)}
              className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold text-rose-200 bg-rose-950/60 hover:bg-rose-900/60 border border-rose-800/60 transition"
            >
              Emergency Void Entire Order
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
