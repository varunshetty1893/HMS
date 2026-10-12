import React from 'react';

interface StatusBadgeProps {
  status: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = status.toUpperCase();

  let colorClasses = 'bg-slate-800 text-slate-300 border-slate-700';

  // Order & Process Statuses
  if (normalized === 'PLACED') {
    colorClasses = 'bg-amber-950/60 text-amber-300 border-amber-700/50';
  } else if (normalized === 'ACCEPTED') {
    colorClasses = 'bg-blue-950/60 text-blue-300 border-blue-700/50';
  } else if (normalized === 'PREPARING') {
    colorClasses = 'bg-brand-950/60 text-brand-300 border-brand-700/50';
  } else if (normalized === 'READY') {
    colorClasses = 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50 animate-pulse';
  } else if (normalized === 'SERVED') {
    colorClasses = 'bg-teal-950/60 text-teal-300 border-teal-700/50';
  } else if (normalized === 'COMPLETED' || normalized === 'PAID' || normalized === 'ACTIVE') {
    colorClasses = 'bg-green-950/60 text-green-300 border-green-700/50';
  } else if (normalized === 'CANCELLED' || normalized === 'REJECTED' || normalized === 'DISABLED') {
    colorClasses = 'bg-rose-950/60 text-rose-300 border-rose-700/50';
  } else if (normalized === 'AVAILABLE') {
    colorClasses = 'bg-emerald-950/40 text-emerald-300 border-emerald-700/40';
  } else if (normalized === 'OCCUPIED' || normalized === 'ISSUED') {
    colorClasses = 'bg-amber-950/60 text-amber-300 border-amber-700/50';
  } else if (normalized === 'VOIDED_FOR_REVISION') {
    colorClasses = 'bg-purple-950/60 text-purple-300 border-purple-700/50';
  }

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs font-semibold';

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full border ${colorClasses} ${sizeClasses} tracking-wide`}
    >
      {normalized}
    </span>
  );
};
