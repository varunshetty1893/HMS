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
    <div
      className="rounded-2xl p-4 shadow-sm animate-fade-in"
      style={{
        background: '#FFF1F2',
        border: '1px solid #FECDD3',
        color: '#9F1239',
      }}
    >
      <div className="flex items-start gap-3">
        <div
          className="p-2 rounded-xl shrink-0 mt-0.5"
          style={{ background: '#FFE4E6', color: '#E11D48' }}
        >
          <AlertTriangle size={20} />
        </div>
        <div className="flex-1">
          <h4 className="text-sm font-bold mb-1" style={{ color: '#881337' }}>
            Table Limit (₹5,000.00) Reached
          </h4>
          <p className="text-xs leading-relaxed" style={{ color: '#9F1239' }}>
            {message}
          </p>
          <div
            className="mt-3 flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-lg inline-flex"
            style={{
              background: '#FFE4E6',
              border: '1px solid #FECDD3',
              color: '#BE123C',
            }}
          >
            <UserCheck size={14} />
            <span>Waiter Assistance Required</span>
          </div>
        </div>
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-xs px-2 py-1 rounded-lg hover:bg-rose-100 transition-colors"
            style={{ color: '#BE123C' }}
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
};
