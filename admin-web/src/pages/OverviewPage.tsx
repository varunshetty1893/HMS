import React, { useEffect, useState } from 'react';
import { reportsApi } from '@/api/reportsApi';
import { adminWs } from '@/realtime/adminWs';
import { formatInr } from '@/utils/currency';
import { usePageTheme } from '@/hooks/usePageTheme';
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
  const { L, heading, sub, muted, card, cardInner } = usePageTheme();

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

  if (isLoading) {
    return (
      <div className="p-8 space-y-6">
        <div className="h-8 w-48 rounded animate-pulse" style={{ backgroundColor: L ? '#e4d9c8' : '#1e293b' }} />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 rounded-2xl animate-pulse" style={card} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Top Banner */}
      <div>
        <h1 className="text-2xl font-black tracking-tight" style={{ color: heading }}>
          Restaurant Overview
        </h1>
        <p className="text-sm mt-1" style={{ color: sub }}>
          Real-time floor summary, kitchen orders, and sales revenue for today.
        </p>
      </div>

      {error && (
        <div
          className="p-4 rounded-2xl text-xs flex items-center justify-between"
          style={{
            backgroundColor: L ? '#fee2e2' : 'rgba(69,10,10,0.6)',
            borderColor: L ? '#fecaca' : '#991b1b',
            borderWidth: 1,
            borderStyle: 'solid',
            color: L ? '#b91c1c' : '#fca5a5',
          }}
        >
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Card 1: Today Revenue */}
        <div className="p-6 rounded-2xl shadow-xl relative overflow-hidden" style={card}>
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider" style={{ color: sub }}>Today's Revenue</span>
            <div
              className="p-2.5 rounded-xl"
              style={{
                backgroundColor: L ? '#dcfce7' : 'rgba(5,46,22,0.6)',
                color: L ? '#15803d' : '#4ade80',
                border: `1px solid ${L ? '#bbf7d0' : 'rgba(74,222,128,0.2)'}`,
              }}
            >
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight" style={{ color: heading }}>
              {formatInr(kpis?.today_revenue || '0.00')}
            </div>
            <p className="text-xs mt-1" style={{ color: muted }}>Total collected from paid bills today</p>
          </div>
        </div>

        {/* Card 2: Occupied Tables */}
        <div
          onClick={() => onNavigate('tables-qr')}
          className="p-6 rounded-2xl shadow-xl relative overflow-hidden cursor-pointer transition-all"
          style={card}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider" style={{ color: sub }}>Dining Tables</span>
            <div
              className="p-2.5 rounded-xl"
              style={{
                backgroundColor: L ? '#e0e7ff' : 'rgba(49,46,129,0.4)',
                color: L ? '#4338ca' : '#818cf8',
                border: `1px solid ${L ? '#c7d2fe' : 'rgba(129,140,248,0.2)'}`,
              }}
            >
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight" style={{ color: heading }}>
              {kpis?.active_occupied_tables || 0}{' '}
              <span className="text-lg font-sans font-normal" style={{ color: muted }}>/ {kpis?.total_tables || 0}</span>
            </div>
            <p className="text-xs mt-1" style={{ color: muted }}>Occupied dining tables currently active</p>
          </div>
        </div>

        {/* Card 3: Active Orders */}
        <div
          onClick={() => onNavigate('live-orders')}
          className="p-6 rounded-2xl shadow-xl relative overflow-hidden cursor-pointer transition-all"
          style={card}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider" style={{ color: sub }}>Active Kitchen Orders</span>
            <div
              className="p-2.5 rounded-xl"
              style={{
                backgroundColor: L ? '#fef3c7' : 'rgba(120,53,15,0.4)',
                color: L ? '#b45309' : '#fbbf24',
                border: `1px solid ${L ? '#fde68a' : 'rgba(251,191,36,0.2)'}`,
              }}
            >
              <Flame className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight" style={{ color: heading }}>
              {kpis?.active_orders_count || 0}
            </div>
            <p className="text-xs mt-1" style={{ color: muted }}>Placed / Cooking / Ready to serve</p>
          </div>
        </div>

        {/* Card 4: Unpaid Exposure */}
        <div
          onClick={() => onNavigate('billing')}
          className="p-6 rounded-2xl shadow-xl relative overflow-hidden cursor-pointer transition-all"
          style={card}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider" style={{ color: sub }}>Unpaid Bills</span>
            <div
              className="p-2.5 rounded-xl"
              style={{
                backgroundColor: L ? '#fee2e2' : 'rgba(127,29,29,0.4)',
                color: L ? '#b91c1c' : '#f87171',
                border: `1px solid ${L ? '#fecaca' : 'rgba(248,113,113,0.2)'}`,
              }}
            >
              <Receipt className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight" style={{ color: heading }}>
              {formatInr(kpis?.unpaid_exposure_amount || '0.00')}
            </div>
            <p className="text-xs mt-1 font-medium text-rose-500">
              {kpis?.unpaid_bills_count || 0} unpaid bills awaiting customer payment
            </p>
          </div>
        </div>
      </div>

      {/* Floor Status Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Orders by status breakdown */}
        <div className="lg:col-span-2 p-6 rounded-2xl shadow-xl space-y-4" style={card}>
          <h2 className="text-base font-bold" style={{ color: heading }}>Kitchen Order Status Breakdown</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {[
              { key: 'PLACED', label: 'New (Placed)' },
              { key: 'ACCEPTED', label: 'Accepted' },
              { key: 'PREPARING', label: 'Cooking' },
              { key: 'READY', label: 'Ready to Serve' },
            ].map(({ key, label }) => {
              const count = kpis?.orders_by_status?.[key] || 0;
              return (
                <div
                  key={key}
                  className="p-4 rounded-xl flex flex-col items-center justify-center text-center"
                  style={cardInner}
                >
                  <span className="text-xs font-bold" style={{ color: sub }}>{label}</span>
                  <span className="text-2xl font-black font-mono mt-1" style={{ color: heading }}>{count}</span>
                </div>
              );
            })}
          </div>

          <div className="pt-2 flex items-center justify-between text-xs" style={{ color: muted }}>
            <span>
              Cancelled orders today:{' '}
              <strong className="text-rose-500">{kpis?.recent_rejections_cancellations || 0}</strong>
            </span>
            <button
              onClick={() => onNavigate('live-orders')}
              className="flex items-center gap-1 font-semibold text-brand-600 hover:text-brand-500 transition cursor-pointer"
            >
              <span>View Live Orders</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right: Quick Operational Shortcuts */}
        <div className="p-6 rounded-2xl shadow-xl space-y-4" style={card}>
          <h2 className="text-base font-bold" style={{ color: heading }}>Quick Shortcuts</h2>
          <div className="space-y-2.5">
            {[
              { label: 'Settle Unpaid Bills', icon: Receipt, color: 'text-emerald-500', mod: 'billing' as AdminModule },
              { label: 'View Tables & QR Codes', icon: Users, color: 'text-indigo-500', mod: 'tables-qr' as AdminModule },
              { label: 'Menu & Out-of-Stock Dishes', icon: Utensils, color: 'text-amber-500', mod: 'menu' as AdminModule },
              { label: 'Sales Reports & Export', icon: TrendingUp, color: 'text-purple-500', mod: 'reports' as AdminModule },
            ].map(({ label, icon: Icon, color, mod }) => (
              <button
                key={mod}
                onClick={() => onNavigate(mod)}
                className="w-full p-3.5 rounded-xl flex items-center justify-between text-left transition cursor-pointer"
                style={cardInner}
              >
                <div className="flex items-center gap-3">
                  <Icon className={`w-4 h-4 ${color}`} />
                  <span className="text-sm font-semibold" style={{ color: heading }}>{label}</span>
                </div>
                <ArrowRight className="w-4 h-4" style={{ color: muted }} />
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
