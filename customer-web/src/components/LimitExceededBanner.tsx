import React from 'react';
import { AlertTriangle, UserCheck } from 'lucide-react';

interface LimitExceededBannerProps {
  message?: string;
  onDismiss?: () => void;
}

export const LimitExceededBanner: React.FC<LimitExceededBannerProps> = ({
  message = 'Unpaid table spend limit reached. Please ask your waiter to settle or verify your current orders before placing additional items.',
  onDismiss,
}) => {
  return (
    <div className="bg-rose-950/80 border border-rose-500/60 rounded-2xl p-4 text-rose-200 shadow-xl shadow-rose-950/40 animate-fade-in">
      <div className="flex items-start space-x-3">
        <div className="p-2 rounded-xl bg-rose-500/20 text-rose-400 shrink-0 mt-0.5">
          <AlertTriangle size={20} />
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-bold text-white mb-1">
            Table Limit (₹5,000.00) Reached
          </h4>
          <p className="text-xs text-rose-200/90 leading-relaxed">
            {message}
          </p>
          <div className="mt-3 flex items-center space-x-2 text-xs font-semibold text-rose-300 bg-rose-900/40 px-3 py-1.5 rounded-lg border border-rose-800/60 inline-flex">
            <UserCheck size={14} />
            <span>Waiter Assistance Required</span>
          </div>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-rose-400 hover:text-white text-xs px-2 py-1 rounded-lg hover:bg-rose-900/40"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
};
