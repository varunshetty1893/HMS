import React, { useEffect, useState } from 'react';
import { adminWs } from '@/realtime/adminWs';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { LogOut, Moon, Sun, Wifi, Smartphone } from 'lucide-react';
import { isDevDemoEnabled } from '@/utils/env';

export const TopStatusHeader: React.FC = () => {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [wsStatus, setWsStatus] = useState<'CONNECTED' | 'CONNECTING' | 'DISCONNECTED'>('DISCONNECTED');
  const [currentTime, setCurrentTime] = useState<string>('');

  const isLight = theme === 'light';

  useEffect(() => {
    const unsub = adminWs.onStatusChange((status) => {
      setWsStatus(status);
    });

    const updateClock = () => {
      const now = new Date();
      setCurrentTime(
        new Intl.DateTimeFormat('en-IN', {
          timeZone: 'Asia/Kolkata',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit',
          hour12: true,
        }).format(now)
      );
    };

    updateClock();
    const interval = setInterval(updateClock, 1000);

    return () => {
      unsub();
      clearInterval(interval);
    };
  }, []);

  const headerStyle: React.CSSProperties = {
    backgroundColor: '#ffffff',
    borderBottomColor: '#e2e8f0',
  };

  const clockStyle: React.CSSProperties = {
    backgroundColor: '#f8fafc',
    borderColor: '#e2e8f0',
    color: '#475569',
  };

  return (
    <header
      className="h-16 border-b px-6 flex items-center justify-between no-print bg-white"
      style={headerStyle}
    >
      {/* Left: Real-time network badge & Live IST Clock */}
      <div className="flex items-center gap-4">
        {wsStatus === 'CONNECTED' ? (
          <div
            className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200"
            title="Connected to WebSocket real-time event pipeline"
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <Wifi className="w-3.5 h-3.5" />
            <span>LIVE SYNC</span>
          </div>
        ) : wsStatus === 'CONNECTING' ? (
          <div
            className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200"
          >
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
            <span>CONNECTING...</span>
          </div>
        ) : (
          <div
            className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-600 border border-slate-200"
            title="Real-time WebSocket disconnected; automatic reconnect active"
          >
            <span className="w-2 h-2 rounded-full bg-slate-400" />
            <Wifi className="w-3.5 h-3.5" />
            <span>OFFLINE</span>
          </div>
        )}

        <div
          className="hidden sm:flex items-center gap-1.5 text-xs font-mono px-3 py-1 rounded-xl"
          style={clockStyle}
        >
          <span className="font-sans font-medium text-gray-500">IST:</span>
          <span>{currentTime || '—'}</span>
        </div>
      </div>

      {/* Right: Theme toggle, Staff profile & Logout */}
      <div className="flex items-center gap-3">
        {/* Customer Web Preview Link (Omitted in Production) */}
        {isDevDemoEnabled() && (
          <button
            onClick={() => {
              sessionStorage.setItem('hms_table_number', '4');
              sessionStorage.setItem('hms_table_name', 'Table 4 (Window Side)');
              sessionStorage.setItem('hms_table_id', 'table-demo-4');
              sessionStorage.setItem('hms_customer_token', 'demo-token-table-4');
              const url = new URL(window.location.href);
              url.searchParams.set('view', 'customer');
              window.history.pushState({}, '', url.toString());
              window.dispatchEvent(new PopStateEvent('popstate'));
            }}
            title="[DEV ONLY] Open the Customer QR Ordering View"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow transition cursor-pointer"
          >
            <Smartphone className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Customer QR App</span>
          </button>
        )}

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          title="Theme Toggle"
          className="flex items-center justify-center w-9 h-9 rounded-xl transition-all cursor-pointer bg-white border border-gray-200 text-gray-600 hover:text-brand-600 hover:border-gray-300"
        >
          {isLight ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
        </button>

        <div className="text-right">
          <p className="text-sm font-semibold text-gray-900">
            {user?.full_name || 'Administrator'}
          </p>
          <p className="text-xs font-medium text-brand-600">
            @{user?.username || 'admin'} • ADMIN
          </p>
        </div>

        <button
          onClick={logout}
          title="Sign out"
          className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition-all bg-white border border-gray-200 text-gray-600 hover:text-rose-600 hover:border-rose-200 hover:bg-rose-50 cursor-pointer"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden md:inline">Sign Out</span>
        </button>
      </div>
    </header>
  );
};
