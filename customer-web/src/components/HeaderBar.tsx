import React from 'react';
import { useSession } from '../context/SessionContext';
import { formatInr } from '../utils/currency';
import { UtensilsCrossed, Clock, AlertCircle } from 'lucide-react';

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
    <header className="sticky top-0 z-30 bg-slate-900/90 backdrop-blur-md border-b border-slate-800 text-white px-4 py-3 shadow-lg">
      <div className="max-w-md mx-auto flex items-center justify-between">
        {/* Table Badge */}
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 rounded-lg bg-orange-600/20 border border-orange-500/40 flex items-center justify-center text-orange-400 font-bold text-sm">
            {tableNumber ? `T${tableNumber}` : 'QR'}
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-wide text-slate-100 leading-tight">
              {tableDisplayName || 'Table'}
            </h1>
            <div className="flex items-center space-x-1.5 text-xs text-slate-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>Dine-In Session</span>
            </div>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center space-x-1 bg-slate-800/80 p-1 rounded-xl border border-slate-700/60">
          <button
            onClick={() => onTabChange('menu')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'menu'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <UtensilsCrossed size={14} />
            <span>Menu</span>
          </button>
          <button
            onClick={() => onTabChange('orders')}
            className={`relative flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'orders'
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Clock size={14} />
            <span>Orders</span>
            {ordersCount > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-amber-400 text-slate-950">
                {ordersCount}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Exposure / Outstanding Warning if active session */}
      {outstandingNum > 0 && (
        <div className="max-w-md mx-auto mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
          <span className="text-slate-400">Current Table Outstanding:</span>
          <div className="flex items-center space-x-1 font-medium">
            <span
              className={
                isOverLimit
                  ? 'text-rose-400 font-bold'
                  : isNearLimit
                  ? 'text-amber-400'
                  : 'text-slate-200'
              }
            >
              {formatInr(outstandingNum)}
            </span>
            <span className="text-slate-500">/ {formatInr(limitNum)} limit</span>
            {isOverLimit && <AlertCircle size={12} className="text-rose-400 ml-1 inline" />}
          </div>
        </div>
      )}
    </header>
  );
};
