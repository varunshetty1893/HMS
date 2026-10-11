import React, { useEffect, useState } from 'react';
import { adminWs } from '@/realtime/adminWs';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { LogOut, Moon, Sun, Wifi, WifiOff } from 'lucide-react';

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
    backgroundColor: isLight ? '#FFF8ED' : '#0f172a',
    borderBottomColor: isLight ? '#e4d9c8' : '#1e293b',
  };

  const clockStyle: React.CSSProperties = {
    backgroundColor: isLight ? '#f5f0e8' : 'rgba(2,6,23,0.6)',
    borderColor: isLight ? '#e4d9c8' : '#1e293b',
    color: isLight ? '#5a5545' : '#94a3b8',
  };

  return (
    <header
      className="h-16 border-b px-6 flex items-center justify-between no-print"
      style={headerStyle}
    >
      {/* Left: Real-time network badge & Live IST Clock */}
      <div className="flex items-center gap-4">
        {wsStatus === 'CONNECTED' ? (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold"
            style={{ backgroundColor: isLight ? '#dcfce7' : 'rgba(5,46,22,0.6)', color: isLight ? '#15803d' : '#4ade80', border: `1px solid ${isLight ? '#bbf7d0' : 'rgba(74,222,128,0.2)'}` }}>
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <Wifi className="w-3.5 h-3.5" />
            <span>LIVE SYNC</span>
          </div>
        ) : wsStatus === 'CONNECTING' ? (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold"
            style={{ backgroundColor: isLight ? '#fff7ed' : 'rgba(67,20,7,0.6)', color: isLight ? '#c2410c' : '#fb923c', border: `1px solid ${isLight ? '#fed7aa' : 'rgba(251,146,60,0.2)'}` }}>
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span>RECONNECTING...</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold"
            style={{ backgroundColor: isLight ? '#fee2e2' : 'rgba(69,10,10,0.6)', color: isLight ? '#b91c1c' : '#f87171', border: `1px solid ${isLight ? '#fecaca' : 'rgba(248,113,113,0.2)'}` }}>
            <WifiOff className="w-3.5 h-3.5" />
            <span>OFFLINE</span>
          </div>
        )}

        <div
          className="hidden sm:flex items-center gap-1.5 text-xs font-mono px-3 py-1 rounded-xl"
          style={clockStyle}
        >
          <span className="font-sans font-medium" style={{ color: isLight ? '#9b8e7a' : '#64748b' }}>IST:</span>
          <span>{currentTime || '—'}</span>
        </div>
      </div>

      {/* Right: Theme toggle, Staff profile & Logout */}
      <div className="flex items-center gap-3">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          title={isLight ? 'Switch to dark mode' : 'Switch to light mode'}
          className="flex items-center justify-center w-9 h-9 rounded-xl transition-all"
          style={{
            backgroundColor: isLight ? '#f5f0e8' : 'rgba(30,41,59,0.6)',
            border: `1px solid ${isLight ? '#e4d9c8' : '#334155'}`,
            color: isLight ? '#D95D2B' : '#94a3b8',
          }}
        >
          {isLight ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
        </button>

        <div className="text-right">
          <p className="text-sm font-semibold" style={{ color: isLight ? '#282820' : '#f8fafc' }}>
            {user?.full_name || 'Administrator'}
          </p>
          <p className="text-xs font-medium" style={{ color: '#D95D2B' }}>
            @{user?.username || 'admin'} • ADMIN
          </p>
        </div>

        <button
          onClick={logout}
          title="Sign out"
          className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium transition-all"
          style={{
            backgroundColor: isLight ? 'transparent' : 'transparent',
            border: `1px solid ${isLight ? '#e4d9c8' : '#334155'}`,
            color: isLight ? '#5a5545' : '#94a3b8',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.color = '#ef4444';
            (e.currentTarget as HTMLButtonElement).style.borderColor = '#fca5a5';
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = isLight ? '#fee2e2' : 'rgba(69,10,10,0.3)';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.color = isLight ? '#5a5545' : '#94a3b8';
            (e.currentTarget as HTMLButtonElement).style.borderColor = isLight ? '#e4d9c8' : '#334155';
            (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent';
          }}
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden md:inline">Sign Out</span>
        </button>
      </div>
    </header>
  );
};
