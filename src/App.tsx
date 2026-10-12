import React, { useState, useEffect } from 'react';
import AdminApp from '../admin-web/src/App';
import CustomerApp from '../customer-web/src/App';
import { Smartphone, ShieldCheck, ChevronRight, UtensilsCrossed } from 'lucide-react';

export const App: React.FC = () => {
  const [activePortal, setActivePortal] = useState<'admin' | 'customer'>(() => {
    const pathMatches = window.location.pathname.match(/\/q\/([^/?#]+)/);
    const urlParams = new URLSearchParams(window.location.search);
    const hasQrQuery = urlParams.has('qr') || urlParams.has('token');
    const isCustomerView = urlParams.get('view') === 'customer';
    const hasHash = window.location.hash.includes('/q/') || window.location.hash.includes('customer');
    if (pathMatches || hasQrQuery || isCustomerView || hasHash) {
      return 'customer';
    }
    return 'admin';
  });

  useEffect(() => {
    const handlePopState = () => {
      const urlParams = new URLSearchParams(window.location.search);
      if (urlParams.get('view') === 'customer' || window.location.pathname.includes('/q/')) {
        setActivePortal('customer');
      } else if (urlParams.get('view') === 'admin') {
        setActivePortal('admin');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const handleSwitchToCustomer = (tableNum = 4) => {
    sessionStorage.setItem('hms_table_number', tableNum.toString());
    sessionStorage.setItem('hms_table_name', `Table ${tableNum} (Dining)`);
    sessionStorage.setItem('hms_table_id', `table-demo-${tableNum}`);
    sessionStorage.setItem('hms_customer_token', `demo-token-table-${tableNum}`);
    setActivePortal('customer');
  };

  const handleSwitchToAdmin = () => {
    setActivePortal('admin');
  };

  return (
    <div className="relative min-h-screen w-full">
      {/* Active Portal */}
      {activePortal === 'admin' ? <AdminApp /> : <CustomerApp />}

      {/* Floating Portal Switcher Banner / Quick Nav (Development Only) */}
      {import.meta.env.DEV && (
        <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 drop-shadow-2xl no-print">
          {activePortal === 'admin' ? (
            <div className="flex items-center gap-1.5 p-1.5 rounded-full bg-slate-900/95 border border-slate-700/80 shadow-2xl backdrop-blur-md text-xs">
              <span className="pl-3 pr-2 font-medium text-slate-300 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Admin Mode</span>
              </span>
              <button
                onClick={() => handleSwitchToCustomer(4)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow transition cursor-pointer"
                title="[DEV ONLY] Open the customer QR ordering web app as Table 4"
              >
                <Smartphone className="w-3.5 h-3.5" />
                <span>Test Customer QR</span>
                <ChevronRight className="w-3.5 h-3.5 opacity-70" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 p-1.5 rounded-full bg-white/95 border border-stone-300 shadow-2xl backdrop-blur-md text-xs">
              <span className="pl-3 pr-2 font-medium text-stone-700 flex items-center gap-1.5">
                <UtensilsCrossed className="w-3.5 h-3.5 text-amber-600" />
                <span>Customer Mobile Web</span>
              </span>
              <button
                onClick={handleSwitchToAdmin}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-full font-semibold bg-slate-900 hover:bg-slate-800 text-white shadow transition cursor-pointer"
                title="[DEV ONLY] Switch back to Admin Management Portal"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Back to Admin</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default App;
