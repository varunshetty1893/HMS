import React, { useEffect, useState } from 'react';
import { reportsApi } from '@/api/reportsApi';
import { formatInr } from '@/utils/currency';
import { formatDateIst, formatDateTimeIst } from '@/utils/dateIst';
import {
  Calendar,
  CreditCard,
  Download,
  Flame,
  LayoutGrid,
  TrendingUp,
  UserCheck,
  Utensils,
} from 'lucide-react';
import {
  CancelledRejectedReportItem,
  DailySalesSummary,
  KitchenActivityReportItem,
  PaymentMethodReportItem,
  PopularDishReportItem,
  TableUsageReportItem,
  WaiterActivityReportItem,
} from '@/types/api';

export const ReportsPage: React.FC = () => {
  const todayStr = new Date().toISOString().split('T')[0];
  const [fromDate, setFromDate] = useState(todayStr);
  const [toDate, setToDate] = useState(todayStr);
  const [activeTab, setActiveTab] = useState<'sales' | 'dishes' | 'payments' | 'tables' | 'cancellations' | 'staff'>('sales');

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Report Data
  const [dailySales, setDailySales] = useState<DailySalesSummary[]>([]);
  const [popularDishes, setPopularDishes] = useState<PopularDishReportItem[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethodReportItem[]>([]);
  const [tableUsage, setTableUsage] = useState<TableUsageReportItem[]>([]);
  const [cancellations, setCancellations] = useState<CancelledRejectedReportItem[]>([]);
  const [waiters, setWaiters] = useState<WaiterActivityReportItem[]>([]);
  const [kitchens, setKitchens] = useState<KitchenActivityReportItem[]>([]);

  const fetchReports = async () => {
    setIsLoading(true);
    try {
      const [salesData, dishesData, payData, tablesData, cancelData, waitData, kitchData] =
        await Promise.all([
          reportsApi.getDailySales(fromDate, toDate),
          reportsApi.getPopularDishes(fromDate, toDate, 50),
          reportsApi.getPaymentMethods(fromDate, toDate),
          reportsApi.getTableUsage(fromDate, toDate),
          reportsApi.getCancelledRejected(fromDate, toDate),
          reportsApi.getWaiterActivity(fromDate, toDate),
          reportsApi.getKitchenActivity(fromDate, toDate),
        ]);

      setDailySales(salesData);
      setPopularDishes(dishesData);
      setPaymentMethods(payData);
      setTableUsage(tablesData);
      setCancellations(cancelData);
      setWaiters(waitData);
      setKitchens(kitchData);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch analytics report');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [fromDate, toDate]);

  const handleDownloadCsv = async () => {
    try {
      const csv = await reportsApi.exportSalesCsv(fromDate, toDate);
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.setAttribute('href', url);
      link.setAttribute('download', `sales_report_${fromDate}_${toDate}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: any) {
      alert(err?.message || 'Failed to download CSV');
    }
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header & Date Range Filter */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white">Business Intelligence & Reports</h1>
          <p className="text-sm text-slate-400 mt-1">
            Sales aggregation, tax liabilities, velocity analysis, and staff performance
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-xs text-slate-300">
            <Calendar className="w-4 h-4 text-slate-500" />
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="bg-transparent text-white focus:outline-none"
            />
            <span className="text-slate-600">to</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="bg-transparent text-white focus:outline-none"
            />
          </div>

          <button
            onClick={handleDownloadCsv}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md shadow-indigo-600/30 transition cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Report Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b border-slate-800">
        {[
          { id: 'sales', label: 'Sales & Tax Summary', icon: TrendingUp },
          { id: 'dishes', label: 'Top Dishes & Velocity', icon: Utensils },
          { id: 'payments', label: 'Payment Methods', icon: CreditCard },
          { id: 'tables', label: 'Table Turnover', icon: LayoutGrid },
          { id: 'cancellations', label: 'Wastage & Cancellations', icon: Flame },
          { id: 'staff', label: 'Staff Efficiency', icon: UserCheck },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2.5 border-b-2 text-xs font-semibold shrink-0 transition ${
                isActive
                  ? 'border-indigo-500 text-white bg-slate-900/40 rounded-t-xl'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Generating analytics...</div>
      ) : (
        <div>
          {/* TAB 1: Sales & Tax Summary */}
          {activeTab === 'sales' && (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-2xl">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Date</th>
                    <th className="px-6 py-4 font-semibold text-right">Gross Subtotal</th>
                    <th className="px-6 py-4 font-semibold text-right">Discounts</th>
                    <th className="px-6 py-4 font-semibold text-right">CGST (2.5%)</th>
                    <th className="px-6 py-4 font-semibold text-right">SGST (2.5%)</th>
                    <th className="px-6 py-4 font-semibold text-right">Net Revenue</th>
                    <th className="px-6 py-4 font-semibold text-right">Bills Settled</th>
                    <th className="px-6 py-4 font-semibold text-right">Avg Bill Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {dailySales.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="p-8 text-center text-slate-500 font-sans">
                        No settled sales in this period.
                      </td>
                    </tr>
                  ) : (
                    dailySales.map((d, i) => (
                      <tr key={i} className="hover:bg-slate-800/30">
                        <td className="px-6 py-4 font-semibold text-white font-sans">{formatDateIst(d.date)}</td>
                        <td className="px-6 py-4 text-right text-slate-300">{formatInr(d.gross_subtotal)}</td>
                        <td className="px-6 py-4 text-right text-amber-400">-{formatInr(d.total_discounts)}</td>
                        <td className="px-6 py-4 text-right text-slate-400">{formatInr(d.cgst_amount)}</td>
                        <td className="px-6 py-4 text-right text-slate-400">{formatInr(d.sgst_amount)}</td>
                        <td className="px-6 py-4 text-right font-bold text-emerald-400">
                          {formatInr(d.net_collected_revenue)}
                        </td>
                        <td className="px-6 py-4 text-right text-slate-200">{d.total_bills}</td>
                        <td className="px-6 py-4 text-right text-indigo-300">{formatInr(d.average_bill_value)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 2: Popular Dishes */}
          {activeTab === 'dishes' && (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-2xl">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Rank</th>
                    <th className="px-6 py-4 font-semibold">Item Code</th>
                    <th className="px-6 py-4 font-semibold">Dish Name</th>
                    <th className="px-6 py-4 font-semibold">Portion</th>
                    <th className="px-6 py-4 font-semibold text-right">Units Billed</th>
                    <th className="px-6 py-4 font-semibold text-right">Gross Revenue</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {popularDishes.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-slate-500">
                        No dish sales recorded in this date range.
                      </td>
                    </tr>
                  ) : (
                    popularDishes.map((dish, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/30">
                        <td className="px-6 py-4 font-bold text-slate-500">#{idx + 1}</td>
                        <td className="px-6 py-4 font-mono font-bold text-indigo-400">{dish.item_code}</td>
                        <td className="px-6 py-4 font-semibold text-white">{dish.item_name}</td>
                        <td className="px-6 py-4 text-xs text-slate-400">{dish.variant_name}</td>
                        <td className="px-6 py-4 text-right font-mono font-bold text-slate-200">
                          {dish.quantity_billed}
                        </td>
                        <td className="px-6 py-4 text-right font-mono font-bold text-white">
                          {formatInr(dish.gross_revenue)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 3: Payment Methods */}
          {activeTab === 'payments' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {paymentMethods.map((pm) => (
                <div
                  key={pm.payment_method}
                  className="p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-xl"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      {pm.payment_method}
                    </span>
                    <div className="p-2.5 rounded-2xl bg-indigo-950/60 text-indigo-400 border border-indigo-800/40">
                      <CreditCard className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="mt-4">
                    <div className="text-2xl font-black font-mono text-white">
                      {formatInr(pm.total_amount)}
                    </div>
                    <p className="text-xs text-slate-500 mt-1">{pm.transaction_count} settled transactions</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: Table Turnover */}
          {activeTab === 'tables' && (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-2xl">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Table</th>
                    <th className="px-6 py-4 font-semibold text-right">Completed Sessions</th>
                    <th className="px-6 py-4 font-semibold text-right">Avg Session Duration</th>
                    <th className="px-6 py-4 font-semibold text-right">Total Revenue</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {tableUsage.map((t) => (
                    <tr key={t.table_id} className="hover:bg-slate-800/30">
                      <td className="px-6 py-4 font-semibold text-white">
                        {t.display_name} <span className="text-xs text-slate-500 font-mono">(#{t.table_number})</span>
                      </td>
                      <td className="px-6 py-4 text-right font-mono font-bold text-slate-200">{t.session_count}</td>
                      <td className="px-6 py-4 text-right font-mono text-slate-400">
                        {t.average_session_minutes} mins
                      </td>
                      <td className="px-6 py-4 text-right font-mono font-bold text-emerald-400">
                        {formatInr(t.total_revenue)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 5: Wastage & Cancellations */}
          {activeTab === 'cancellations' && (
            <div className="rounded-3xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-2xl">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Order #</th>
                    <th className="px-6 py-4 font-semibold">Table</th>
                    <th className="px-6 py-4 font-semibold">Outcome</th>
                    <th className="px-6 py-4 font-semibold">Reason</th>
                    <th className="px-6 py-4 font-semibold">Timestamp (IST)</th>
                    <th className="px-6 py-4 font-semibold text-right">Lost Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {cancellations.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-slate-500">
                        Zero cancelled or rejected orders in this period.
                      </td>
                    </tr>
                  ) : (
                    cancellations.map((c) => (
                      <tr key={c.order_id} className="hover:bg-slate-800/30">
                        <td className="px-6 py-4 font-mono font-bold text-white">{c.order_number}</td>
                        <td className="px-6 py-4 font-semibold text-slate-200">Table {c.table_number}</td>
                        <td className="px-6 py-4">
                          <span className="text-xs px-2 py-0.5 rounded font-bold bg-rose-950 text-rose-300 border border-rose-800">
                            {c.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-xs text-slate-300 italic">"{c.reason || 'None provided'}"</td>
                        <td className="px-6 py-4 text-xs font-mono text-slate-400">{formatDateTimeIst(c.occurred_at)}</td>
                        <td className="px-6 py-4 text-right font-mono font-bold text-rose-400">
                          {formatInr(c.order_subtotal)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}

          {/* TAB 6: Staff Efficiency */}
          {activeTab === 'staff' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Waiter Performance */}
              <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-xl space-y-4">
                <h3 className="text-base font-bold text-white">Waiter Operations</h3>
                <div className="divide-y divide-slate-800">
                  {waiters.map((w) => (
                    <div key={w.user_id} className="py-3 flex items-center justify-between text-xs">
                      <div>
                        <div className="font-semibold text-white">{w.full_name}</div>
                        <div className="text-slate-500 font-mono">@{w.username}</div>
                      </div>
                      <div className="text-right space-y-0.5 text-slate-400 font-mono">
                        <div>Orders: <strong className="text-white">{w.orders_placed}</strong></div>
                        <div>Delivered: <strong className="text-emerald-400">{w.items_served}</strong></div>
                        <div>Settled: <strong className="text-indigo-400">{w.payments_recorded}</strong></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Kitchen Performance */}
              <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-xl space-y-4">
                <h3 className="text-base font-bold text-white">Kitchen Turnaround</h3>
                <div className="divide-y divide-slate-800">
                  {kitchens.map((k) => (
                    <div key={k.user_id} className="py-3 flex items-center justify-between text-xs">
                      <div>
                        <div className="font-semibold text-white">{k.full_name}</div>
                        <div className="text-slate-500 font-mono">@{k.username}</div>
                      </div>
                      <div className="text-right space-y-0.5 text-slate-400 font-mono">
                        <div>Accepted: <strong className="text-white">{k.orders_accepted}</strong></div>
                        <div>Ready: <strong className="text-emerald-400">{k.orders_ready}</strong></div>
                        <div>Avg Prep: <strong className="text-indigo-400">{k.avg_prep_minutes}m</strong></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
