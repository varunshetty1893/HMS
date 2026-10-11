import React from 'react';
import { useSession } from '../context/SessionContext';
import { formatInr } from '../utils/currency';
import { UtensilsCrossed, Clock, AlertTriangle } from 'lucide-react';

interface HeaderBarProps {
  activeTab: 'menu' | 'orders';
  onTabChange: (tab: 'menu' | 'orders') => void;
  ordersCount?: number;
}

export const HeaderBar: React.FC<HeaderBarProps> = ({
  activeTab,
  onTabChange,
  ordersCount = 0,
}) => {
  const { tableDisplayName, tableNumber, currentOutstanding, customLimit } = useSession();

  const outstandingNum = parseFloat(currentOutstanding) || 0;
  const limitNum = parseFloat(customLimit) || 5000;
  const isNearLimit = outstandingNum >= limitNum * 0.8;
  const isOverLimit = outstandingNum >= limitNum;

  return (
    <>
      <header
        className="sticky top-0 z-30 px-4 py-3 shadow-sm"
        style={{
          background: 'var(--white)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-3">
          {/* Table Badge */}
          <div className="flex items-center gap-2.5 min-w-0 flex-1">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-sm flex-shrink-0"
              style={{ background: 'var(--primary-bg)', color: 'var(--primary)' }}
            >
              {tableNumber ? `T${tableNumber}` : '🍽'}
            </div>
            <div className="min-w-0">
              <h1
                className="text-sm font-bold leading-tight truncate"
                style={{ color: 'var(--text-primary)' }}
              >
                {tableDisplayName || 'Your Table'}
              </h1>
              <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--text-muted)' }}>
                <span
                  className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                  style={{ background: '#22C55E' }}
                />
                <span>Dine-In Active</span>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div
            className="flex items-center p-0.5 rounded-xl flex-shrink-0"
            style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border)' }}
          >
            <button
              id="tab-menu"
              onClick={() => onTabChange('menu')}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={
                activeTab === 'menu'
                  ? { background: 'var(--primary)', color: '#fff' }
                  : { color: 'var(--text-secondary)', background: 'transparent' }
              }
            >
              <UtensilsCrossed size={13} />
              <span>Menu</span>
            </button>
            <button
              id="tab-orders"
              onClick={() => onTabChange('orders')}
              className="relative flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={
                activeTab === 'orders'
                  ? { background: 'var(--primary)', color: '#fff' }
                  : { color: 'var(--text-secondary)', background: 'transparent' }
              }
            >
              <Clock size={13} />
              <span>Orders</span>
              {ordersCount > 0 && (
                <span
                  className="ml-0.5 px-1.5 rounded-full text-[10px] font-bold"
                  style={{ background: '#F59E0B', color: '#fff' }}
                >
                  {ordersCount}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Outstanding Warning */}
        {outstandingNum > 0 && (
          <div
            className="max-w-5xl mx-auto mt-2 pt-2 flex items-center justify-between text-xs"
            style={{ borderTop: '1px solid var(--border)' }}
          >
            <span style={{ color: 'var(--text-muted)' }}>Table outstanding:</span>
            <div className="flex items-center gap-1.5 font-semibold">
              <span
                style={{
                  color: isOverLimit ? '#B91C1C' : isNearLimit ? '#B45309' : 'var(--text-primary)',
                }}
              >
                {formatInr(outstandingNum)}
              </span>
              <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
                / {formatInr(limitNum)}
              </span>
              {isOverLimit && <AlertTriangle size={12} style={{ color: '#B91C1C' }} />}
            </div>
          </div>
        )}
      </header>
    </>
  );
};
