import React, { useEffect, useRef, useState } from 'react';
import { useSession } from '../context/SessionContext';
import { formatInr } from '../utils/currency';
import { CallWaiterSheet } from './CallWaiterSheet';
import { UtensilsCrossed, Clock, AlertTriangle, ShieldCheck, Hand } from 'lucide-react';

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
  const { tableDisplayName, tableNumber, currentOutstanding, customLimit, session } = useSession();
  const [isCallWaiterOpen, setIsCallWaiterOpen] = useState(false);
  const headerRef = useRef<HTMLElement>(null);

  const outstandingNum = parseFloat(currentOutstanding) || 0;
  const limitNum = parseFloat(customLimit) || 5000;
  const isNearLimit = outstandingNum >= limitNum * 0.8;
  const isOverLimit = outstandingNum >= limitNum;
  const isDiningActive = session?.table_status === 'OCCUPIED';

  // Publish the real sticky-header height so page content can offset against it
  // (scroll-margin etc.) without hardcoded pixel values.
  useEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    const publish = () =>
      document.documentElement.style.setProperty('--header-h', `${el.offsetHeight}px`);
    publish();
    const ro = new ResizeObserver(publish);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const tabStyle = (active: boolean): React.CSSProperties =>
    active
      ? { background: 'var(--primary)', color: '#fff', border: '1px solid var(--primary)' }
      : { background: 'var(--bg-subtle)', color: 'var(--text-primary)', border: '1px solid var(--border)' };

  return (
    <>
      <header
        ref={headerRef}
        className="sticky top-0 z-30 px-3 pt-[max(0.5rem,env(safe-area-inset-top))] pb-2 shadow-sm"
        style={{ background: 'var(--cream, #FFF8ED)', borderBottom: '1px solid var(--border)' }}
      >
        <div className="max-w-5xl mx-auto space-y-2">
          {/* Row 1: table • brand • call waiter */}
          <div className="flex items-center justify-between gap-1.5">
            <div className="flex items-center gap-1.5 min-w-0 flex-1">
              <div
                className="w-8 h-8 rounded-xl flex items-center justify-center font-bold text-sm flex-shrink-0"
                style={{ background: 'var(--primary-bg)', color: 'var(--primary)' }}
              >
                {tableNumber ? `T${tableNumber}` : '🍽'}
              </div>
              <div className="min-w-0 leading-tight">
                <h1 className="text-[13px] font-bold truncate" style={{ color: 'var(--text-primary)' }}>
                  {tableDisplayName || 'Your Table'}
                </h1>
                <div className="flex items-center gap-1 text-[10px]" style={{ color: 'var(--text-muted)' }}>
                  <span
                    className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                    style={{ background: isDiningActive ? '#22C55E' : '#94A3B8' }}
                  />
                  <span className="truncate">{isDiningActive ? 'Dine-In Active' : 'Ready to order'}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-1 shrink-0" aria-label="SpiceHub Family Restaurant">
              <img src="/logo.png" alt="" className="w-8 h-8 rounded-full object-cover shrink-0" />
              <div className="leading-none min-w-0">
                <div className="text-base font-extrabold tracking-tight" style={{ color: 'var(--primary)' }}>SpiceHub</div>
                <div className="text-[7px] font-bold tracking-[0.08em] mt-0.5 whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>FAMILY RESTAURANT</div>
              </div>
            </div>

            <div className="flex items-center gap-1.5 flex-shrink-0">
              <button
                onClick={() => setIsCallWaiterOpen(true)}
                className="flex items-center gap-1 px-2.5 py-2 rounded-xl text-xs font-bold cursor-pointer active:scale-95 transition whitespace-nowrap"
                style={{
                  background: 'var(--primary-bg)',
                  color: 'var(--primary)',
                  border: '1.5px solid rgba(217, 93, 43, 0.3)',
                }}
                title="Call waiter to table"
              >
                <Hand size={14} />
                <span>Call Waiter</span>
              </button>
              <button
                onClick={() => {
                  const url = new URL(window.location.href);
                  url.searchParams.set('view', 'admin');
                  window.history.pushState({}, '', url.toString());
                  window.dispatchEvent(new PopStateEvent('popstate'));
                }}
                title="Return to Admin Management Portal"
                className="hidden sm:flex items-center gap-1 px-2.5 py-2 rounded-xl text-xs font-medium text-stone-600 hover:text-stone-900 border border-stone-300 hover:bg-stone-100 transition cursor-pointer"
              >
                <ShieldCheck size={13} className="text-emerald-600" />
                <span>Admin</span>
              </button>
            </div>
          </div>

          {/* Row 2: Menu / Orders tabs (directly under the header) */}
          <div className="grid grid-cols-2 gap-2" role="tablist" aria-label="Menu and Orders">
            <button
              id="tab-menu"
              role="tab"
              aria-selected={activeTab === 'menu'}
              onClick={() => onTabChange('menu')}
              className="flex items-center justify-center gap-1.5 py-2 rounded-xl text-sm font-semibold transition-all cursor-pointer"
              style={tabStyle(activeTab === 'menu')}
            >
              <UtensilsCrossed size={15} />
              <span>Menu</span>
            </button>
            <button
              id="tab-orders"
              role="tab"
              aria-selected={activeTab === 'orders'}
              onClick={() => onTabChange('orders')}
              className="flex items-center justify-center gap-1.5 py-2 rounded-xl text-sm font-semibold transition-all cursor-pointer"
              style={tabStyle(activeTab === 'orders')}
            >
              <Clock size={15} />
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

          {/* Compact outstanding line (only when there is a balance) */}
          {outstandingNum > 0 && (
            <div className="flex items-center justify-between text-[11px] leading-none">
              <span style={{ color: 'var(--text-muted)' }}>Table outstanding</span>
              <span className="flex items-center gap-1 font-semibold">
                <span style={{ color: isOverLimit ? '#B91C1C' : isNearLimit ? '#B45309' : 'var(--text-primary)' }}>
                  {formatInr(outstandingNum)}
                </span>
                <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>/ {formatInr(limitNum)}</span>
                {isOverLimit && <AlertTriangle size={11} style={{ color: '#B91C1C' }} />}
              </span>
            </div>
          )}
        </div>
      </header>

      <CallWaiterSheet isOpen={isCallWaiterOpen} onClose={() => setIsCallWaiterOpen(false)} />
    </>
  );
};
