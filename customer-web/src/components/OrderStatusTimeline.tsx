import React from 'react';
import type { OrderResponse } from '../types';
import { formatInr } from '../utils/currency';
import {
  CheckCircle2,
  Clock,
  ChefHat,
  BellRing,
  Utensils,
  XCircle,
} from 'lucide-react';

interface OrderStatusTimelineProps {
  order: OrderResponse;
}

const STEPS = [
  { key: 'PLACED', label: 'Placed', icon: Clock },
  { key: 'ACCEPTED', label: 'Accepted', icon: CheckCircle2 },
  { key: 'PREPARING', label: 'Preparing', icon: ChefHat },
  { key: 'READY', label: 'Ready', icon: BellRing },
  { key: 'SERVED', label: 'Served', icon: Utensils },
];

export const OrderStatusTimeline: React.FC<OrderStatusTimelineProps> = ({ order }) => {
  const currentStatus = order.status;
  const isTerminalCancelled = currentStatus === 'CANCELLED';
  const isTerminalRejected = currentStatus === 'REJECTED';

  const getStepIndex = (status: string) => {
    switch (status) {
      case 'PLACED':
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

  return (
    <div className="bg-slate-800/80 border border-slate-700/80 rounded-2xl p-4 shadow-md space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-700/60">
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-sm text-white font-mono">
              #{order.order_number}
            </span>
            {order.is_first_qr_order_of_session && (
              <span className="text-[10px] bg-orange-500/20 text-orange-400 border border-orange-500/30 px-2 py-0.5 rounded-full font-semibold">
                Initial Order
              </span>
            )}
          </div>
          <span className="text-xs text-slate-400">Placed at {formattedTime}</span>
        </div>

        <div className="text-right">
          <span className="font-bold text-sm text-slate-100 block">
            {formatInr(order.order_subtotal)}
          </span>
          <span className="text-[11px] text-slate-400">Subtotal</span>
        </div>
      </div>

      {/* Stepper / Timeline */}
      {isTerminalRejected || isTerminalCancelled ? (
        <div className="flex items-center space-x-2 p-3 bg-rose-950/60 border border-rose-800 rounded-xl text-rose-300 text-xs">
          <XCircle size={18} className="text-rose-400 shrink-0" />
          <div>
            <span className="font-bold block">
              Order {isTerminalRejected ? 'Rejected by Kitchen' : 'Cancelled'}
            </span>
            <span className="text-rose-300/80">Please check with restaurant staff.</span>
          </div>
        </div>
      ) : (
        <div className="relative pt-2 pb-1">
          {/* Progress bar background */}
          <div className="absolute top-6 left-5 right-5 h-0.5 bg-slate-700 -z-0" />
          {/* Active progress bar */}
          <div
            className="absolute top-6 left-5 h-0.5 bg-orange-500 transition-all duration-500 -z-0"
            style={{
              width: `${(activeIndex / (STEPS.length - 1)) * 88}%`,
            }}
          />

          <div className="flex justify-between items-start relative z-10">
            {STEPS.map((step, idx) => {
              const Icon = step.icon;
              const isPassed = idx <= activeIndex;
              const isCurrent = idx === activeIndex;

              return (
                <div key={step.key} className="flex flex-col items-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                      isCurrent
                        ? 'bg-orange-500 text-white ring-4 ring-orange-500/20 shadow-md shadow-orange-500/40'
                        : isPassed
                        ? 'bg-orange-500/80 text-white'
                        : 'bg-slate-800 text-slate-500 border border-slate-700'
                    }`}
                  >
                    <Icon size={14} />
                  </div>
                  <span
                    className={`text-[10px] mt-1.5 font-medium ${
                      isCurrent
                        ? 'text-orange-400 font-bold'
                        : isPassed
                        ? 'text-slate-300'
                        : 'text-slate-500'
                    }`}
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
        <div className="text-xs bg-slate-900/60 p-2.5 rounded-xl border border-slate-800 text-slate-300">
          <span className="text-slate-500 font-medium mr-1.5">Note:</span>
          &ldquo;{order.special_instructions}&rdquo;
        </div>
      )}

      {/* Items preview */}
      <div className="space-y-1.5 pt-1">
        {order.items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between text-xs py-1 border-b border-slate-800/60 last:border-0"
          >
            <div className="flex items-center space-x-2">
              <span className="font-bold text-slate-300 w-5">
                {item.active_quantity}x
              </span>
              <div>
                <span className="text-slate-200 font-medium">
                  {item.item_name_snapshot}
                </span>
                <span className="text-slate-400 ml-1.5 text-[11px]">
                  ({item.variant_name_snapshot})
                </span>
                {item.item_notes && (
                  <p className="text-[10px] text-slate-500 italic">
                    {item.item_notes}
                  </p>
                )}
              </div>
            </div>
            <span className="font-mono text-slate-300">
              {formatInr(item.line_subtotal)}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
