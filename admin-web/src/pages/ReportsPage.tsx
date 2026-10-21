import React, { useEffect, useState } from 'react';
import { reportsApi } from '@/api/reportsApi';
import { formatInr } from '@/utils/currency';
import { formatDateIst, formatDateTimeIst, todayIst } from '@/utils/dateIst';
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
  PaymentTransactionReportItem,
  PopularDishReportItem,
  TableUsageReportItem,
  WaiterActivityReportItem,
} from '@/types/api';
import { usePageTheme } from '@/hooks/usePageTheme';
import { PaginationBar, usePagination } from '@/components/common/Pagination';

// ─── Main page ────────────────────────────────────────────────────────────────
export const ReportsPage: React.FC = () => {
  const { L, heading, sub, muted, border, card, tableWrap, thead, tbodyRow, tbodyRowHover } = usePageTheme();
  const todayStr = todayIst();
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
  const [selectedSalesDay, setSelectedSalesDay] = useState<DailySalesSummary | null>(null);
  const [dayTransactions, setDayTransactions] = useState<PaymentTransactionReportItem[]>([]);
  const [isLoadingTransactions, setIsLoadingTransactions] = useState(false);

  // Pagination — one per tab that has a table
  const salesPag = usePagination(dailySales, 15);
  const txnPag = usePagination(dayTransactions, 10);
  const dishesPag = usePagination(popularDishes, 20);
  const tablesPag = usePagination(tableUsage, 15);
  const cancelPag = usePagination(cancellations, 15);

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

  const openSalesDay = async (day: DailySalesSummary) => {
    setSelectedSalesDay(day);
    setDayTransactions([]);
    setIsLoadingTransactions(true);
    try {
      setDayTransactions(await reportsApi.getPaymentTransactions(day.date, day.date));
    } catch (err: any) {
      setError(err?.message || 'Failed to load settlement transactions.');
    } finally {
      setIsLoadingTransactions(false);
    }
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header & Date Range Filter */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight" style={{ color: heading }}>Business Intelligence &amp; Reports</h1>
          <p className="text-sm mt-1" style={{ color: sub }}>
            Sales aggregation, tax liabilities, velocity analysis, and staff performance
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div
            className="flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs shadow-xs"
            style={{
              backgroundColor: L ? '#ffffff' : '#0f172a',
              border: `1px solid ${border}`,
              color: heading,
            }}
          >
            <Calendar className="w-4 h-4 text-brand-600" />
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="bg-transparent focus:outline-none cursor-pointer"
              style={{ color: heading }}
            />
            <span style={{ color: muted }}>to</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="bg-transparent focus:outline-none cursor-pointer"
              style={{ color: heading }}
            />
          </div>

          <button
            onClick={handleDownloadCsv}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-md shadow-brand-600/30 transition cursor-pointer"
          >
            <Download className="w-4 h-4" />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
          {error}
        </div>
      )}

      {/* Report Tabs */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 border-b" style={{ borderBottomColor: border }}>
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
              className="flex items-center gap-2 px-4 py-2.5 border-b-2 text-xs font-semibold shrink-0 transition cursor-pointer"
              style={{
                borderBottomColor: isActive ? '#D95D2B' : 'transparent',
                color: isActive ? '#D95D2B' : sub,
                backgroundColor: isActive ? (L ? '#ffffff' : 'rgba(30,41,59,0.5)') : 'transparent',
                borderRadius: isActive ? '8px 8px 0 0' : undefined,
              }}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab Content */}
      {isLoading ? (
        <div className="p-12 text-center" style={{ color: muted }}>Generating analytics...</div>
      ) : (
        <div>
          {/* TAB 1: Sales & Tax Summary */}
          {activeTab === 'sales' && (
            <div className="rounded-3xl overflow-hidden shadow-sm" style={tableWrap}>
              <table className="w-full text-left text-sm" style={{ color: heading }}>
                <thead className="text-xs uppercase tracking-wider border-b" style={{ ...thead, borderBottomColor: border }}>
                  <tr>
                    <th className="px-6 py-4 font-semibold">Date</th>
                    <th className="px-6 py-4 font-semibold text-right">Gross Subtotal</th>
                    <th className="px-6 py-4 font-semibold text-right">Discounts</th>
                    <th className="px-6 py-4 font-semibold text-right">CGST</th>
                    <th className="px-6 py-4 font-semibold text-right">SGST</th>
                    <th className="px-6 py-4 font-semibold text-right">Net Revenue</th>
                    <th className="px-6 py-4 font-semibold text-right">Cash Received</th>
                    <th className="px-6 py-4 font-semibold text-right">Change Returned</th>
                    <th className="px-6 py-4 font-semibold text-right">Bills Settled</th>
                    <th className="px-6 py-4 font-semibold text-right">Avg Bill Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y font-mono" style={{ borderColor: border }}>
                  {salesPag.slice.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="p-8 text-center font-sans" style={{ color: muted }}>
                        No settled sales in this period.
                      </td>
                    </tr>
                  ) : (
                    salesPag.slice.map((d, i) => (
                      <tr
                        key={i}
                        onClick={() => openSalesDay(d)}
                        className="transition cursor-pointer"
                        style={{ ...tbodyRow, borderBottomColor: border }}
                        onMouseEnter={(e) => {
                          if (tbodyRowHover.backgroundColor) e.currentTarget.style.backgroundColor = tbodyRowHover.backgroundColor as string;
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = 'transparent';
                        }}
                      >
                        <td className="px-6 py-4 font-semibold font-sans" style={{ color: heading }}>{formatDateIst(d.date)}</td>
                        <td className="px-6 py-4 text-right" style={{ color: heading }}>{formatInr(d.gross_subtotal)}</td>
                        <td className="px-6 py-4 text-right text-amber-600">-{formatInr(d.total_discounts)}</td>
                        <td className="px-6 py-4 text-right" style={{ color: sub }}>{formatInr(d.cgst_amount)}</td>
                        <td className="px-6 py-4 text-right" style={{ color: sub }}>{formatInr(d.sgst_amount)}</td>
                        <td className="px-6 py-4 text-right font-bold text-emerald-600">
                          {formatInr(d.net_collected_revenue)}
                        </td>
                        <td className="px-6 py-4 text-right font-bold" style={{ color: heading }}>{formatInr(d.cash_tendered)}</td>
                        <td className="px-6 py-4 text-right text-amber-600">{formatInr(d.cash_change_returned)}</td>
                        <td className="px-6 py-4 text-right" style={{ color: heading }}>{d.total_bills}</td>
                        <td className="px-6 py-4 text-right text-brand-600 font-bold">{formatInr(d.average_bill_value)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              <PaginationBar {...salesPag} border={border} muted={muted} heading={heading} />
            </div>
          )}

          {/* TAB 2: Popular Dishes */}
          {activeTab === 'dishes' && (
            <div className="rounded-3xl overflow-hidden shadow-sm" style={tableWrap}>
              <table className="w-full text-left text-sm" style={{ color: heading }}>
                <thead className="text-xs uppercase tracking-wider border-b" style={{ ...thead, borderBottomColor: border }}>
                  <tr>
                    <th className="px-6 py-4 font-semibold">Rank</th>
                    <th className="px-6 py-4 font-semibold">Item Code</th>
                    <th className="px-6 py-4 font-semibold">Dish Name</th>
                    <th className="px-6 py-4 font-semibold">Portion</th>
                    <th className="px-6 py-4 font-semibold text-right">Units Billed</th>
                    <th className="px-6 py-4 font-semibold text-right">Gross Revenue</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: border }}>
                  {dishesPag.slice.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center" style={{ color: muted }}>
                        No dish sales recorded in this date range.
                      </td>
                    </tr>
                  ) : (
                    dishesPag.slice.map((dish, idx) => (
                      <tr key={idx} style={{ ...tbodyRow, borderBottomColor: border }}>
                        <td className="px-6 py-4 font-bold" style={{ color: muted }}>#{dishesPag.start + idx + 1}</td>
                        <td className="px-6 py-4 font-mono font-bold text-brand-600">{dish.item_code}</td>
                        <td className="px-6 py-4 font-semibold" style={{ color: heading }}>{dish.item_name}</td>
                        <td className="px-6 py-4 text-xs" style={{ color: sub }}>{dish.variant_name}</td>
                        <td className="px-6 py-4 text-right font-mono font-bold" style={{ color: heading }}>
                          {dish.quantity_billed}
                        </td>
                        <td className="px-6 py-4 text-right font-mono font-bold" style={{ color: heading }}>
                          {formatInr(dish.gross_revenue)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              <PaginationBar {...dishesPag} border={border} muted={muted} heading={heading} />
            </div>
          )}

          {/* TAB 3: Payment Methods */}
          {activeTab === 'payments' && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {paymentMethods.map((pm) => (
                <div
                  key={pm.payment_method}
                  className="p-6 rounded-3xl shadow-sm transition hover:shadow-md"
                  style={card}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider" style={{ color: sub }}>
                      {pm.payment_method}
                    </span>
                    <div className="p-2.5 rounded-2xl bg-amber-50 text-amber-700 border border-amber-200">
                      <CreditCard className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="mt-4">
                    <div className="text-2xl font-black font-mono" style={{ color: heading }}>
                      {formatInr(pm.total_amount)}
                    </div>
                    <p className="text-xs mt-1" style={{ color: muted }}>{pm.transaction_count} settled transactions</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: Table Turnover */}
          {activeTab === 'tables' && (
            <div className="rounded-3xl overflow-hidden shadow-sm" style={tableWrap}>
              <table className="w-full text-left text-sm" style={{ color: heading }}>
                <thead className="text-xs uppercase tracking-wider border-b" style={{ ...thead, borderBottomColor: border }}>
                  <tr>
                    <th className="px-6 py-4 font-semibold">Table</th>
                    <th className="px-6 py-4 font-semibold text-right">Completed Sessions</th>
                    <th className="px-6 py-4 font-semibold text-right">Avg Session Duration</th>
                    <th className="px-6 py-4 font-semibold text-right">Total Revenue</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: border }}>
                  {tablesPag.slice.length === 0 ? (
                    <tr>
                      <td colSpan={4} className="p-8 text-center" style={{ color: muted }}>
                        No table sessions recorded in this period.
                      </td>
                    </tr>
                  ) : (
                    tablesPag.slice.map((t) => (
                      <tr key={t.table_id} style={{ ...tbodyRow, borderBottomColor: border }}>
                        <td className="px-6 py-4 font-semibold" style={{ color: heading }}>
                          {t.display_name} <span className="text-xs font-mono" style={{ color: muted }}>(#{t.table_number})</span>
                        </td>
                        <td className="px-6 py-4 text-right font-mono font-bold" style={{ color: heading }}>{t.session_count}</td>
                        <td className="px-6 py-4 text-right font-mono" style={{ color: sub }}>
                          {t.average_session_minutes} mins
                        </td>
                        <td className="px-6 py-4 text-right font-mono font-bold text-emerald-600">
                          {formatInr(t.total_revenue)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              <PaginationBar {...tablesPag} border={border} muted={muted} heading={heading} />
            </div>
          )}

          {/* TAB 5: Wastage & Cancellations */}
          {activeTab === 'cancellations' && (
            <div className="rounded-3xl overflow-hidden shadow-sm" style={tableWrap}>
              <table className="w-full text-left text-sm" style={{ color: heading }}>
                <thead className="text-xs uppercase tracking-wider border-b" style={{ ...thead, borderBottomColor: border }}>
                  <tr>
                    <th className="px-6 py-4 font-semibold">Order #</th>
                    <th className="px-6 py-4 font-semibold">Table</th>
                    <th className="px-6 py-4 font-semibold">Outcome</th>
                    <th className="px-6 py-4 font-semibold">Reason</th>
                    <th className="px-6 py-4 font-semibold">Timestamp (IST)</th>
                    <th className="px-6 py-4 font-semibold text-right">Lost Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y" style={{ borderColor: border }}>
                  {cancelPag.slice.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center" style={{ color: muted }}>
                        Zero cancelled or rejected orders in this period.
                      </td>
                    </tr>
                  ) : (
                    cancelPag.slice.map((c) => (
                      <tr key={c.order_id} style={{ ...tbodyRow, borderBottomColor: border }}>
                        <td className="px-6 py-4 font-mono font-bold" style={{ color: heading }}>{c.order_number}</td>
                        <td className="px-6 py-4 font-semibold" style={{ color: heading }}>Table {c.table_number}</td>
                        <td className="px-6 py-4">
                          <span className="text-xs px-2 py-0.5 rounded font-bold bg-rose-100 text-rose-700 border border-rose-300">
                            {c.status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-xs italic" style={{ color: sub }}>"{c.reason || 'None provided'}"</td>
                        <td className="px-6 py-4 text-xs font-mono" style={{ color: sub }}>{formatDateTimeIst(c.occurred_at)}</td>
                        <td className="px-6 py-4 text-right font-mono font-bold text-rose-600">
                          {formatInr(c.order_subtotal)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
              <PaginationBar {...cancelPag} border={border} muted={muted} heading={heading} />
            </div>
          )}

          {/* TAB 6: Staff Efficiency */}
          {activeTab === 'staff' && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Waiter Performance */}
              <div className="p-6 rounded-3xl shadow-sm space-y-4" style={card}>
                <h3 className="text-base font-bold" style={{ color: heading }}>Waiter Operations</h3>
                <div className="divide-y" style={{ borderColor: border }}>
                  {waiters.length === 0 ? (
                    <p className="text-xs py-4" style={{ color: muted }}>No waiter activity in this period.</p>
                  ) : (
                    waiters.map((w) => (
                      <div key={w.user_id} className="py-3 flex items-center justify-between text-xs" style={{ borderBottomColor: border }}>
                        <div>
                          <div className="font-semibold" style={{ color: heading }}>{w.full_name}</div>
                          <div className="font-mono" style={{ color: muted }}>@{w.username}</div>
                        </div>
                        <div className="text-right space-y-0.5 font-mono" style={{ color: sub }}>
                          <div>Orders: <strong style={{ color: heading }}>{w.orders_placed}</strong></div>
                          <div>Delivered: <strong className="text-emerald-600">{w.items_served}</strong></div>
                          <div>Settled: <strong className="text-brand-600">{w.payments_recorded}</strong></div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Kitchen Performance */}
              <div className="p-6 rounded-3xl shadow-sm space-y-4" style={card}>
                <h3 className="text-base font-bold" style={{ color: heading }}>Kitchen Turnaround</h3>
                <div className="divide-y" style={{ borderColor: border }}>
                  {kitchens.length === 0 ? (
                    <p className="text-xs py-4" style={{ color: muted }}>No kitchen activity in this period.</p>
                  ) : (
                    kitchens.map((k) => (
                      <div key={k.user_id} className="py-3 flex items-center justify-between text-xs" style={{ borderBottomColor: border }}>
                        <div>
                          <div className="font-semibold" style={{ color: heading }}>{k.full_name}</div>
                          <div className="font-mono" style={{ color: muted }}>@{k.username}</div>
                        </div>
                        <div className="text-right space-y-0.5 font-mono" style={{ color: sub }}>
                          <div>Accepted: <strong style={{ color: heading }}>{k.orders_accepted}</strong></div>
                          <div>Ready: <strong className="text-emerald-600">{k.orders_ready}</strong></div>
                          <div>Avg Prep: <strong className="text-brand-600">{k.avg_prep_minutes}m</strong></div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
      {selectedSalesDay && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="w-full max-w-5xl max-h-[85vh] overflow-auto rounded-3xl p-6 shadow-2xl" style={card}>
            <div className="flex items-start justify-between gap-4 mb-5">
              <div><h2 className="text-lg font-black" style={{ color: heading }}>Settled transactions — {formatDateIst(selectedSalesDay.date)}</h2><p className="text-xs mt-1" style={{ color: muted }}>Revenue is the bill amount applied. Cash received and change are shown separately.</p></div>
              <button onClick={() => setSelectedSalesDay(null)} className="px-3 py-2 rounded-xl text-xs font-bold border cursor-pointer" style={{ borderColor: border, color: heading }}>Close</button>
            </div>
            {isLoadingTransactions ? <div className="p-10 text-center text-sm" style={{ color: muted }}>Loading transactions…</div> : (
              <div className="overflow-x-auto rounded-2xl border" style={{ borderColor: border }}><table className="w-full text-left text-xs"><thead style={thead}><tr><th className="px-4 py-3">Bill</th><th className="px-4 py-3">Table</th><th className="px-4 py-3">Method</th><th className="px-4 py-3 text-right">Applied / Revenue</th><th className="px-4 py-3 text-right">Cash Received</th><th className="px-4 py-3 text-right">Change Returned</th><th className="px-4 py-3">Time</th></tr></thead><tbody>{dayTransactions.length === 0 ? <tr><td colSpan={7} className="px-4 py-8 text-center" style={{ color: muted }}>No settled transactions for this date.</td></tr> : txnPag.slice.map((transaction) => <tr key={transaction.payment_id} className="border-t" style={{ borderColor: border }}><td className="px-4 py-3 font-mono font-bold" style={{ color: heading }}>{transaction.bill_number}</td><td className="px-4 py-3" style={{ color: sub }}>{transaction.table_display_name || (transaction.table_number ? `Table ${transaction.table_number}` : '—')}</td><td className="px-4 py-3">{transaction.payment_method}</td><td className="px-4 py-3 text-right font-mono font-bold text-emerald-600">{formatInr(transaction.amount_applied)}</td><td className="px-4 py-3 text-right font-mono">{transaction.payment_method === 'CASH' ? formatInr(transaction.amount_tendered ?? transaction.amount_applied) : '—'}</td><td className="px-4 py-3 text-right font-mono text-amber-600">{transaction.payment_method === 'CASH' ? formatInr(transaction.change_returned) : '—'}</td><td className="px-4 py-3" style={{ color: muted }}>{transaction.completed_at ? formatDateTimeIst(transaction.completed_at) : '—'}</td></tr>)}</tbody></table><PaginationBar {...txnPag} border={border} muted={muted} heading={heading} /></div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
