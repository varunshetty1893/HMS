import React, { useEffect, useState } from 'react';
import { reportsApi } from '@/api/reportsApi';
import { adminWs } from '@/realtime/adminWs';
import { formatInr } from '@/utils/currency';
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

    // Re-fetch on any floor event
    const unsub = adminWs.on('*', () => {
      fetchKpis();
    });

    return () => {
      unsub();
    };
  }, []);

  if (isLoading) {
    return (
      <div className="p-8 space-y-6">
        <div className="h-8 w-48 bg-slate-800 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-slate-900 border border-slate-800 rounded-3xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-8">
      {/* Top Banner */}
      <div>
        <h1 className="text-2xl font-black tracking-tight text-white">Live Operations Overview</h1>
        <p className="text-sm text-slate-400 mt-1">Real-time floor state, active orders, and revenue metrics</p>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/50 border border-rose-800/40 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Card 1: Today Revenue */}
        <div className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Today's Revenue</span>
            <div className="p-2.5 rounded-2xl bg-emerald-950/60 text-emerald-400 border border-emerald-800/40">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight text-white">
              {formatInr(kpis?.today_revenue || '0.00')}
            </div>
            <p className="text-xs text-slate-500 mt-1">From settled customer bills today</p>
          </div>
        </div>

        {/* Card 2: Occupied Tables */}
        <div
          onClick={() => onNavigate('tables-qr')}
          className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl relative overflow-hidden hover:border-slate-700 transition cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Table Occupancy</span>
            <div className="p-2.5 rounded-2xl bg-indigo-950/60 text-indigo-400 border border-indigo-800/40">
              <Users className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight text-white">
              {kpis?.active_occupied_tables || 0}{' '}
              <span className="text-lg text-slate-500 font-sans font-normal">/ {kpis?.total_tables || 0}</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">Active dining sessions on floor</p>
          </div>
        </div>

        {/* Card 3: Active Orders */}
        <div
          onClick={() => onNavigate('live-orders')}
          className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl relative overflow-hidden hover:border-slate-700 transition cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Active Kitchen Orders</span>
            <div className="p-2.5 rounded-2xl bg-amber-950/60 text-amber-400 border border-amber-800/40">
              <Flame className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight text-white">
              {kpis?.active_orders_count || 0}
            </div>
            <p className="text-xs text-slate-500 mt-1">Placed / Preparing / Ready</p>
          </div>
        </div>

        {/* Card 4: Unpaid Exposure */}
        <div
          onClick={() => onNavigate('billing')}
          className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl relative overflow-hidden hover:border-slate-700 transition cursor-pointer"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Unpaid Bills Exposure</span>
            <div className="p-2.5 rounded-2xl bg-rose-950/60 text-rose-400 border border-rose-800/40">
              <Receipt className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-4">
            <div className="text-3xl font-black font-mono tracking-tight text-white">
              {formatInr(kpis?.unpaid_exposure_amount || '0.00')}
            </div>
            <p className="text-xs text-rose-400 mt-1 font-medium">
              {kpis?.unpaid_bills_count || 0} unpaid issued bills pending
            </p>
          </div>
        </div>
      </div>

      {/* Floor Status Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Orders by status breakdown */}
        <div className="lg:col-span-2 p-6 rounded-3xl bg-slate-900/80 border border-slate-800 space-y-4">
          <h2 className="text-base font-bold text-white">Floor Order Pipeline</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {['PLACED', 'ACCEPTED', 'PREPARING', 'READY'].map((st) => {
              const count = kpis?.orders_by_status?.[st] || 0;
              return (
                <div
                  key={st}
                  className="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex flex-col items-center justify-center text-center"
                >
                  <span className="text-xs font-bold text-slate-400">{st}</span>
                  <span className="text-2xl font-black font-mono text-white mt-1">{count}</span>
                </div>
              );
            })}
          </div>

          <div className="pt-2 flex items-center justify-between text-xs text-slate-400">
            <span>
              Cancelled/Rejected today:{' '}
              <strong className="text-rose-400">{kpis?.recent_rejections_cancellations || 0}</strong>
            </span>
            <button
              onClick={() => onNavigate('live-orders')}
              className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-semibold"
            >
              <span>View live queue</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Right: Quick Operational Shortcuts */}
        <div className="p-6 rounded-3xl bg-slate-900/80 border border-slate-800 space-y-4">
          <h2 className="text-base font-bold text-white">Operational Shortcuts</h2>
          <div className="space-y-2.5">
            <button
              onClick={() => onNavigate('billing')}
              className="w-full p-3.5 rounded-2xl bg-slate-950 hover:bg-slate-800/80 border border-slate-800 flex items-center justify-between text-left transition"
            >
              <div className="flex items-center gap-3">
                <Receipt className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-semibold text-slate-200">Settle Unpaid Bills</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </button>

            <button
              onClick={() => onNavigate('tables-qr')}
              className="w-full p-3.5 rounded-2xl bg-slate-950 hover:bg-slate-800/80 border border-slate-800 flex items-center justify-between text-left transition"
            >
              <div className="flex items-center gap-3">
                <Users className="w-4 h-4 text-indigo-400" />
                <span className="text-sm font-semibold text-slate-200">Print Table Standees</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </button>

            <button
              onClick={() => onNavigate('menu')}
              className="w-full p-3.5 rounded-2xl bg-slate-950 hover:bg-slate-800/80 border border-slate-800 flex items-center justify-between text-left transition"
            >
              <div className="flex items-center gap-3">
                <Utensils className="w-4 h-4 text-amber-400" />
                <span className="text-sm font-semibold text-slate-200">86'd Stock Toggle / Menu</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </button>

            <button
              onClick={() => onNavigate('reports')}
              className="w-full p-3.5 rounded-2xl bg-slate-950 hover:bg-slate-800/80 border border-slate-800 flex items-center justify-between text-left transition"
            >
              <div className="flex items-center gap-3">
                <TrendingUp className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-semibold text-slate-200">Download Sales CSV</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
