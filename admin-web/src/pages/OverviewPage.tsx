import React, { useEffect, useState } from 'react';
import { reportsApi } from '@/api/reportsApi';
import { adminWs } from '@/realtime/adminWs';
import { formatInr } from '@/utils/currency';
import { useTheme } from '@/context/ThemeContext';
import {
  ArrowRight,
  Flame,
  Receipt,
  TrendingUp,
  Users,
  Utensils,
} from 'lucide-react';
import { AdminDashboardKPIs } from '@/types/api';
import { AdminModule } from '@/components/layout/AdminSidebar';

interface OverviewPageProps {
  onNavigate: (module: AdminModule) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({ onNavigate }) => {
  const { theme } = useTheme();
  const L = theme === 'light';

  const [kpis, setKpis] = useState<AdminDashboardKPIs | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchKpis = async () => {
    try {
      const data = await reportsApi.getDashboardKpis();
      setKpis(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch dashboard metrics');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchKpis();
    const unsub = adminWs.on('*', () => { fetchKpis(); });
    return () => { unsub(); };
  }, []);

  // ── Shared style helpers ──────────────────────────────────────────────────
  const card = {
    backgroundColor: L ? '#ffffff' : 'rgba(15,23,42,0.9)',
    border: `1px solid ${L ? '#e4d9c8' : '#1e293b'}`,
  } as React.CSSProperties;

  const cardInner = {
    backgroundColor: L ? '#faf7f2' : '#020617',
    border: `1px solid ${L ? '#e4d9c8' : '#1e293b'}`,
  } as React.CSSProperties;

  const headingColor = L ? '#282820' : '#f8fafc';
  const labelColor = L ? '#756a56' : '#64748b';
  const valueColor = L ? '#282820' : '#f8fafc';
  const subColor = L ? '#756a56' : '#64748b';

  if (isLoading) {
    return (
      <div className="p-8 space-y-6">
        <div className="h-8 w-48 rounded animate-pulse" style={{ backgroundColor: L ? '#e4d9c8' : '#1e293b' }} />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 rounded-3xl animate-pulse" style={{ backgroundColor: L ? '#f5f0e8' : '#0f172a', border: `1px solid ${L ? '#e4d9c8' : '#1e293b'}` }} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Top Banner */}
      <div>
        <h1 className="text-2xl font-black tracking-tight" style={{ color: headingColor }}>
          Live Operations Overview
        </h1>
        <p className="text-sm mt-1" style={{ color: subColor }}>
          Real-time floor state, active orders, and revenue metrics
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-2xl text-xs" style={{ backgroundColor: L ? '#fee2e2' : 'rgba(69,10,10,0.5)', border: `1px solid ${L ? '#fecaca' : 'rgba(248,113,113,0.3)'}`, color: L ? '#b91c1c' : '#f87171' }}>
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Card 1: Today Revenue */}
        <div className="p-6 rounded-3xl shadow-lg relative overflow-hidden" style={card}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider" style={{ color: labelColor }}>Today's Revenue</span>
            <div className="p-2.5 rounded-2xl" style={{ backgroundColor: L ? '#dcfce7' : 'rgba(5,46,22,0.6)', border: `1px solid ${L ? '#bbf7d0' : 'rgba(74,222,128,0.2)'}` }}>
              <TrendingUp className="w-5 h-5" style={{ color: L ? '#15803d' : '#4ade80' }} />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight" style={{ color: valueColor }}>
              {formatInr(kpis?.today_revenue || '0.00')}
            </div>
            <p className="text-xs mt-1" style={{ color: subColor }}>From settled customer bills today</p>
          </div>
        </div>

        {/* Card 2: Occupied Tables */}
        <div
          onClick={() => onNavigate('tables-qr')}
          className="p-6 rounded-3xl shadow-lg relative overflow-hidden cursor-pointer transition-all hover:scale-[1.01]"
          style={{ ...card, cursor: 'pointer' }}
          onMouseEnter={(e) => (e.currentTarget as HTMLDivElement).style.borderColor = '#D95D2B'}
          onMouseLeave={(e) => (e.currentTarget as HTMLDivElement).style.borderColor = L ? '#e4d9c8' : '#1e293b'}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider" style={{ color: labelColor }}>Table Occupancy</span>
            <div className="p-2.5 rounded-2xl" style={{ backgroundColor: L ? '#eff6ff' : 'rgba(30,27,75,0.6)', border: `1px solid ${L ? '#bfdbfe' : 'rgba(99,102,241,0.3)'}` }}>
              <Users className="w-5 h-5" style={{ color: L ? '#1d4ed8' : '#818cf8' }} />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight" style={{ color: valueColor }}>
              {kpis?.active_occupied_tables || 0}{' '}
              <span className="text-lg font-sans font-normal" style={{ color: subColor }}>/ {kpis?.total_tables || 0}</span>
            </div>
            <p className="text-xs mt-1" style={{ color: subColor }}>Active dining sessions on floor</p>
          </div>
        </div>

        {/* Card 3: Active Orders */}
        <div
          onClick={() => onNavigate('live-orders')}
          className="p-6 rounded-3xl shadow-lg relative overflow-hidden cursor-pointer transition-all hover:scale-[1.01]"
          style={{ ...card, cursor: 'pointer' }}
          onMouseEnter={(e) => (e.currentTarget as HTMLDivElement).style.borderColor = '#D95D2B'}
          onMouseLeave={(e) => (e.currentTarget as HTMLDivElement).style.borderColor = L ? '#e4d9c8' : '#1e293b'}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider" style={{ color: labelColor }}>Active Kitchen Orders</span>
            <div className="p-2.5 rounded-2xl" style={{ backgroundColor: L ? '#fff7ed' : 'rgba(67,20,7,0.6)', border: `1px solid ${L ? '#fed7aa' : 'rgba(251,146,60,0.3)'}` }}>
              <Flame className="w-5 h-5" style={{ color: L ? '#c2410c' : '#fb923c' }} />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight" style={{ color: valueColor }}>
              {kpis?.active_orders_count || 0}
            </div>
            <p className="text-xs mt-1" style={{ color: subColor }}>Placed / Preparing / Ready</p>
          </div>
        </div>

        {/* Card 4: Unpaid Exposure */}
        <div
          onClick={() => onNavigate('billing')}
          className="p-6 rounded-3xl shadow-lg relative overflow-hidden cursor-pointer transition-all hover:scale-[1.01]"
          style={{ ...card, cursor: 'pointer' }}
          onMouseEnter={(e) => (e.currentTarget as HTMLDivElement).style.borderColor = '#D95D2B'}
          onMouseLeave={(e) => (e.currentTarget as HTMLDivElement).style.borderColor = L ? '#e4d9c8' : '#1e293b'}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider" style={{ color: labelColor }}>Unpaid Bills Exposure</span>
            <div className="p-2.5 rounded-2xl" style={{ backgroundColor: L ? '#fee2e2' : 'rgba(69,10,10,0.6)', border: `1px solid ${L ? '#fecaca' : 'rgba(248,113,113,0.3)'}` }}>
              <Receipt className="w-5 h-5" style={{ color: L ? '#b91c1c' : '#f87171' }} />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight" style={{ color: valueColor }}>
              {formatInr(kpis?.unpaid_exposure_amount || '0.00')}
            </div>
            <p className="text-xs mt-1 font-medium" style={{ color: L ? '#b91c1c' : '#f87171' }}>
              {kpis?.unpaid_bills_count || 0} unpaid issued bills pending
            </p>
          </div>
        </div>
      </div>

      {/* Floor Status Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Orders by status breakdown */}
        <div className="lg:col-span-2 p-6 rounded-3xl space-y-4" style={card}>
          <h2 className="text-base font-bold" style={{ color: headingColor }}>Floor Order Pipeline</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {['PLACED', 'ACCEPTED', 'PREPARING', 'READY'].map((st) => {
              const count = kpis?.orders_by_status?.[st] || 0;
              return (
                <div key={st} className="p-4 rounded-2xl flex flex-col items-center justify-center text-center" style={cardInner}>
                  <span className="text-xs font-bold" style={{ color: labelColor }}>{st}</span>
                  <span className="text-2xl font-black font-mono mt-1" style={{ color: valueColor }}>{count}</span>
                </div>
              );
            })}
          </div>

          <div className="pt-2 flex items-center justify-between text-xs" style={{ color: labelColor }}>
            <span>
              Cancelled/Rejected today:{' '}
              <strong style={{ color: L ? '#b91c1c' : '#f87171' }}>{kpis?.recent_rejections_cancellations || 0}</strong>
            </span>
            <button
              onClick={() => onNavigate('live-orders')}
              className="flex items-center gap-1 font-semibold hover:underline"
              style={{ color: '#D95D2B' }}
            >
              <span>View live queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right: Quick Operational Shortcuts */}
        <div className="p-6 rounded-3xl space-y-4" style={card}>
          <h2 className="text-base font-bold" style={{ color: headingColor }}>Operational Shortcuts</h2>
          <div className="space-y-2.5">
            {[
              { label: 'Settle Unpaid Bills', icon: Receipt, color: L ? '#15803d' : '#4ade80', mod: 'billing' as AdminModule },
              { label: 'Print Table Standees', icon: Users, color: L ? '#1d4ed8' : '#818cf8', mod: 'tables-qr' as AdminModule },
              { label: "86'd Stock Toggle / Menu", icon: Utensils, color: L ? '#c2410c' : '#fb923c', mod: 'menu' as AdminModule },
              { label: 'Download Sales CSV', icon: TrendingUp, color: L ? '#7e22ce' : '#c084fc', mod: 'reports' as AdminModule },
            ].map(({ label, icon: Icon, color, mod }) => (
              <button
                key={mod}
                onClick={() => onNavigate(mod)}
                className="w-full p-3.5 rounded-2xl flex items-center justify-between text-left transition-all"
                style={cardInner}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = '#D95D2B';
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = L ? '#fef3e2' : '#1e293b';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = L ? '#e4d9c8' : '#1e293b';
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = L ? '#faf7f2' : '#020617';
                }}
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4" style={{ color }} />
                  <span className="text-sm font-semibold" style={{ color: L ? '#282820' : '#e2e8f0' }}>{label}</span>
                </div>
                <ArrowRight className="w-4 h-4" style={{ color: labelColor }} />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
