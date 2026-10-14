import React, { useState } from 'react';
import type { CustomerItemChange, MenuItem, OrderResponse } from '../types';
import { OrderEditPanel } from './OrderEditPanel';
import { formatInr } from '../utils/currency';
import {
  CheckCircle2,
  Clock,
  ChefHat,
  BellRing,
  Utensils,
  XCircle,
  FileText,
  Loader2,
  AlertTriangle,
  Pencil,
} from 'lucide-react';

interface OrderStatusTimelineProps {
  order: OrderResponse;
  onCancelOrder?: (orderId: string) => Promise<void>;
  /** Save quantity / portion edits (PLACED/ACCEPTED: anything; PREPARING: increase only) */
  onModifyOrder?: (
    orderId: string,
    expectedVersion: number,
    changes: CustomerItemChange[],
  ) => Promise<void>;
  /** menu_item_id -> menu item, used to offer cheaper portions (Full -> Half) */
  menuItems?: Record<string, MenuItem>;
}

const STEPS = [
  { key: 'PLACED', label: 'Placed', icon: Clock },
  { key: 'ACCEPTED', label: 'Accepted', icon: CheckCircle2 },
  { key: 'PREPARING', label: 'Cooking', icon: ChefHat },
  { key: 'READY', label: 'Ready', icon: BellRing },
  { key: 'SERVED', label: 'Served', icon: Utensils },
];

export const OrderStatusTimeline: React.FC<OrderStatusTimelineProps> = ({
  order,
  onCancelOrder,
  onModifyOrder,
  menuItems = {},
}) => {
  const currentStatus = order.status;
  const isTerminalCancelled = currentStatus === 'CANCELLED';
  const isTerminalRejected = currentStatus === 'REJECTED';

  // Can cancel only before cooking starts (while status is PLACED, SUBMITTED, or ACCEPTED)
  const isCancellable =
    currentStatus === 'PLACED' ||
    currentStatus === 'SUBMITTED' ||
    currentStatus === 'ACCEPTED';

  // Cooking has started
  const isCookingOrPast =
    currentStatus === 'PREPARING' ||
    currentStatus === 'READY' ||
    currentStatus === 'SERVED';

  // Editing is allowed until the food is READY (PREPARING = increase-only, enforced server-side)
  const isEditable = isCancellable || currentStatus === 'PREPARING';
  const [isEditing, setIsEditing] = useState(false);

  const [showCancelConfirm, setShowCancelConfirm] = useState(false);
  const [isCancelling, setIsCancelling] = useState(false);
  const [cancelError, setCancelError] = useState<string | null>(null);

  const getStepIndex = (status: string) => {
    switch (status) {
      case 'PLACED':
      case 'SUBMITTED':
        return 0;
      case 'ACCEPTED':
        return 1;
      case 'PREPARING':
        return 2;
      case 'READY':
        return 3;
      case 'SERVED':
        return 4;
      default:
        return 0;
    }
  };

  const activeIndex = getStepIndex(currentStatus);

  // Format placed time
  const placedDate = new Date(order.placed_at);
  const formattedTime = !isNaN(placedDate.getTime())
    ? placedDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '';

  const handleConfirmCancel = async () => {
    if (!onCancelOrder) return;
    setIsCancelling(true);
    setCancelError(null);
    try {
      await onCancelOrder(order.id);
      setShowCancelConfirm(false);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to cancel order.';
      setCancelError(message);
    } finally {
      setIsCancelling(false);
    }
  };

  return (
    <div
      className="rounded-3xl p-5 shadow-sm space-y-4 transition-all"
      style={{
        background: 'var(--white)',
        border: '1px solid var(--border)',
        boxShadow: '0 2px 10px rgba(40, 40, 32, 0.04)',
      }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between pb-3.5"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span
              className="font-bold text-sm font-mono tracking-tight"
              style={{ color: 'var(--text-primary)' }}
            >
              Order #{order.order_number}
            </span>
            {order.is_first_qr_order_of_session && (
              <span
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                style={{
                  background: 'var(--primary-bg)',
                  color: 'var(--primary)',
                  border: '1px solid rgba(217, 93, 43, 0.2)',
                }}
              >
                First Order
              </span>
            )}
          </div>
          <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Placed at {formattedTime}
          </span>
        </div>

        <div className="text-right">
          <span
            className="font-bold text-base block font-mono"
            style={{
              color: isTerminalCancelled ? 'var(--text-muted)' : 'var(--primary)',
              textDecoration: isTerminalCancelled ? 'line-through' : 'none',
            }}
          >
            {formatInr(order.order_subtotal)}
          </span>
          <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            {isTerminalCancelled ? 'Cancelled' : 'Subtotal'}
          </span>
        </div>
      </div>

      {/* Stepper / Timeline */}
      {isTerminalRejected || isTerminalCancelled ? (
        <div
          className="flex items-center gap-3 p-3.5 rounded-2xl text-xs"
          style={{
            background: '#FEF2F2',
            border: '1px solid #FCA5A5',
            color: '#B91C1C',
          }}
        >
          <XCircle size={20} className="shrink-0 text-red-500" />
          <div>
            <span className="font-bold block">
              Order {isTerminalRejected ? 'Rejected by Kitchen' : 'Cancelled'}
            </span>
            <span className="text-red-700/80">
              {isTerminalCancelled
                ? order.cancelled_by_role && order.cancelled_by_role !== 'CUSTOMER'
                  ? `Cancelled by the restaurant${order.cancellation_reason ? `: ${order.cancellation_reason}` : '.'}`
                  : 'This order has been cancelled and will not be prepared.'
                : 'Please check with restaurant staff.'}
            </span>
          </div>
        </div>
      ) : (
        <div className="relative pt-2 pb-1">
          {/* Progress bar background */}
          <div
            className="absolute top-5 left-5 right-5 h-1 rounded-full -z-0"
            style={{ background: 'var(--border)' }}
          />
          {/* Active progress bar */}
          <div
            className="absolute top-5 left-5 h-1 rounded-full transition-all duration-500 -z-0"
            style={{
              background: activeIndex === 4 ? 'var(--green)' : 'var(--primary)',
              width: `${(activeIndex / (STEPS.length - 1)) * 88}%`,
            }}
          />

          <div className="flex justify-between items-start relative z-10">
            {STEPS.map((step, idx) => {
              const Icon = step.icon;
              const isPassed = idx <= activeIndex;
              const isCurrent = idx === activeIndex;

              let iconBg = 'var(--bg-subtle)';
              let iconColor = 'var(--text-muted)';
              let ringClass = '';

              if (isCurrent) {
                iconBg = activeIndex === 4 ? 'var(--green)' : 'var(--primary)';
                iconColor = '#FFFFFF';
                ringClass = 'ring-4 ring-orange-500/20 shadow-md';
              } else if (isPassed) {
                iconBg = activeIndex === 4 ? 'var(--green)' : 'var(--primary)';
                iconColor = '#FFFFFF';
              }

              return (
                <div key={step.key} className="flex flex-col items-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${ringClass}`}
                    style={{
                      background: iconBg,
                      color: iconColor,
                      border: !isPassed ? '1px solid var(--border)' : 'none',
                    }}
                  >
                    <Icon size={14} />
                  </div>
                  <span
                    className="text-[10px] mt-1.5 font-medium"
                    style={{
                      color: isCurrent
                        ? 'var(--primary)'
                        : isPassed
                        ? 'var(--text-primary)'
                        : 'var(--text-muted)',
                      fontWeight: isCurrent ? 700 : 500,
                    }}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Special Instructions note */}
      {order.special_instructions && (
        <div
          className="text-xs p-2.5 rounded-xl flex items-start gap-2"
          style={{
            background: 'var(--bg-subtle)',
            border: '1px solid var(--border)',
            color: 'var(--text-secondary)',
          }}
        >
          <FileText size={14} className="shrink-0 mt-0.5" style={{ color: 'var(--primary)' }} />
          <span>&ldquo;{order.special_instructions}&rdquo;</span>
        </div>
      )}

      {/* Edit panel (replaces the read-only list while editing) */}
      {isEditing && onModifyOrder && (
        <OrderEditPanel
          order={order}
          menuItems={menuItems}
          onSave={onModifyOrder}
          onClose={() => setIsEditing(false)}
        />
      )}

      {/* Items preview */}
      <div className="space-y-2 pt-1" style={{ display: isEditing ? 'none' : undefined }}>
        {order.items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between text-xs py-1.5"
            style={{ borderBottom: '1px dashed var(--border)' }}
          >
            <div className="flex items-center gap-2">
              <span
                className="font-bold w-6 text-center rounded py-0.5"
                style={{
                  background: isTerminalCancelled ? 'var(--bg-subtle)' : 'var(--primary-bg)',
                  color: isTerminalCancelled ? 'var(--text-muted)' : 'var(--primary)',
                }}
              >
                {item.active_quantity}x
              </span>
              <div>
                <span
                  className="font-medium"
                  style={{
                    color: isTerminalCancelled ? 'var(--text-muted)' : 'var(--text-primary)',
                    textDecoration: isTerminalCancelled ? 'line-through' : 'none',
                  }}
                >
                  {item.item_name_snapshot}
                </span>
                <span className="ml-1.5 text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  ({item.variant_name_snapshot})
                </span>
                {item.item_notes && (
                  <p className="text-[10px] italic" style={{ color: 'var(--text-muted)' }}>
                    Note: {item.item_notes}
                  </p>
                )}
              </div>
            </div>
            <span
              className="font-mono font-medium"
              style={{
                color: isTerminalCancelled ? 'var(--text-muted)' : 'var(--text-primary)',
              }}
            >
              {formatInr(item.line_subtotal)}
            </span>
          </div>
        ))}
      </div>

      {/* Edit entry point */}
      {!isTerminalCancelled && !isTerminalRejected && isEditable && onModifyOrder && !isEditing && (
        <button
          type="button"
          onClick={() => setIsEditing(true)}
          className="w-full px-3.5 py-2 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 transition cursor-pointer"
          style={{
            background: 'var(--primary-bg)',
            color: 'var(--primary)',
            border: '1px solid rgba(217, 93, 43, 0.25)',
          }}
        >
          <Pencil size={13} />
          <span>{isCookingOrPast ? 'Add more / change portion' : 'Edit items'}</span>
        </button>
      )}

      {/* ── Cancellation Control Section ── */}
      {!isTerminalCancelled && !isTerminalRejected && (
        <div className="pt-2">
          {/* If cooking has started, show that it cannot be cancelled */}
          {isCookingOrPast ? (
            <div className="flex items-center gap-2 p-2.5 rounded-xl text-[11px] bg-amber-50/80 border border-amber-200/80 text-amber-900">
              <ChefHat size={15} className="text-amber-700 shrink-0" />
              <span className="font-medium">
                Cooking has started in the kitchen • This order can no longer be cancelled
                or reduced. To cancel, please ask your waiter.
              </span>
            </div>
          ) : isCancellable ? (
            /* If still PLACED or ACCEPTED, order is cancellable */
            showCancelConfirm ? (
              <div className="p-3.5 bg-red-50 border border-red-200 rounded-2xl space-y-2.5 animate-fade-in">
                <div className="flex items-center gap-2 text-red-900 font-bold text-xs">
                  <AlertTriangle size={15} className="text-red-600" />
                  <span>Cancel Order #{order.order_number}?</span>
                </div>
                <p className="text-[11px] text-red-800 leading-relaxed">
                  Cooking hasn&apos;t started yet. You can cancel this order before the chef begins preparation.
                </p>
                {cancelError && (
                  <p className="text-[11px] text-red-600 font-semibold">{cancelError}</p>
                )}
                <div className="flex items-center gap-2 pt-1">
                  <button
                    onClick={handleConfirmCancel}
                    disabled={isCancelling}
                    className="px-4 py-2 rounded-xl text-xs font-bold bg-red-600 hover:bg-red-700 text-white shadow-sm transition-all flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
                  >
                    {isCancelling ? <Loader2 size={13} className="animate-spin" /> : null}
                    <span>Yes, Cancel Order</span>
                  </button>
                  <button
                    onClick={() => {
                      setShowCancelConfirm(false);
                      setCancelError(null);
                    }}
                    disabled={isCancelling}
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white border border-stone-300 text-stone-700 hover:bg-stone-50 transition cursor-pointer"
                  >
                    Keep Order
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-between pt-1">
                <span className="text-[11px] text-stone-500">
                  Kitchen has not started cooking yet
                </span>
                <button
                  onClick={() => setShowCancelConfirm(true)}
                  className="px-3.5 py-1.5 rounded-xl text-xs font-bold text-red-600 hover:text-red-700 bg-red-50 hover:bg-red-100 border border-red-200/80 transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  <XCircle size={14} />
                  <span>Cancel Order</span>
                </button>
              </div>
            )
          ) : null}
        </div>
      )}
    </div>
  );
};
