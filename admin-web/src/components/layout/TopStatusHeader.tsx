import React, { useEffect, useState } from 'react';
import { adminWs } from '@/realtime/adminWs';
import { useAuth } from '@/context/AuthContext';
import { LogOut, Wifi, WifiOff } from 'lucide-react';

export const TopStatusHeader: React.FC = () => {
  const { user, logout } = useAuth();
  const [wsStatus, setWsStatus] = useState<'CONNECTED' | 'CONNECTING' | 'DISCONNECTED'>('DISCONNECTED');
  const [currentTime, setCurrentTime] = useState<string>('');

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

  return (
    <header className="h-16 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between no-print">
      {/* Left: Real-time network badge & Live IST Clock */}
      <div className="flex items-center gap-4">
        {wsStatus === 'CONNECTED' ? (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <Wifi className="w-3.5 h-3.5" />
            <span>LIVE SYNC</span>
          </div>
        ) : wsStatus === 'CONNECTING' ? (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-amber-950/60 text-amber-400 border border-amber-800/40">
            <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
            <span>RECONNECTING...</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold bg-rose-950/60 text-rose-400 border border-rose-800/40">
            <WifiOff className="w-3.5 h-3.5" />
            <span>OFFLINE</span>
          </div>
        )}

        <div className="hidden sm:flex items-center gap-1.5 text-xs font-mono text-slate-400 bg-slate-950/60 px-3 py-1 rounded-xl border border-slate-800">
          <span className="text-slate-500 font-sans font-medium">IST:</span>
          <span>{currentTime || '—'}</span>
        </div>
      </div>

      {/* Right: Staff profile & Logout */}
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-semibold text-white">{user?.full_name || 'Administrator'}</p>
          <p className="text-xs text-[#EB7444] font-medium">@{user?.username || 'admin'} • ADMIN</p>
        </div>

        <button
          onClick={logout}
          title="Sign out"
          className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-rose-300 hover:bg-rose-950/30 border border-slate-800 hover:border-rose-900/40 transition"
        >
          <LogOut className="w-4 h-4" />
          <span className="hidden md:inline">Sign Out</span>
        </button>
      </div>
    </header>
  );
};
