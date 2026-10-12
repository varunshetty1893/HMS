import React, { useEffect, useState } from 'react';
import { ordersBillsApi } from '@/api/ordersBillsApi';
import { formatInr } from '@/utils/currency';
import { formatDateTimeIst } from '@/utils/dateIst';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ConfirmModal } from '@/components/common/ConfirmModal';
import { usePageTheme } from '@/hooks/usePageTheme';
import { CreditCard, Percent, Receipt, RotateCcw, Search, X } from 'lucide-react';
import { Bill } from '@/types/api';

export const BillingAndPaymentsPage: React.FC = () => {
  const t = usePageTheme();
  const [bills, setBills] = useState<Bill[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ISSUED');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedBill, setSelectedBill] = useState<Bill | null>(null);
  const [discountBill, setDiscountBill] = useState<Bill | null>(null);
  const [discountAmount, setDiscountAmount] = useState('50.00');
  const [discountReason, setDiscountReason] = useState('Manager goodwill');
  const [voidBill, setVoidBill] = useState<Bill | null>(null);

  const fetchBills = async () => {
    setIsLoading(true);
    try {
      const data = await ordersBillsApi.listBills({ status: statusFilter === 'ALL' ? undefined : statusFilter });
      setBills(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to load bills');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => { fetchBills(); }, [statusFilter]);

  const handleApplyDiscount = async () => {
    if (!discountBill) return;
    try {
      await ordersBillsApi.applyDiscount(discountBill.id, discountAmount, discountReason);
      alert('Discount applied successfully.');
      setDiscountBill(null);
      setSelectedBill(null);
      fetchBills();
    } catch (err: any) {
      alert(err?.message || 'Failed to apply discount');
    }
  };

  const handleConfirmVoidForRevision = async (reason?: string) => {
    if (!voidBill) return;
    try {
      await ordersBillsApi.voidBillForRevision(voidBill.id, reason || 'Voided for order item revision');
      alert('Bill marked as VOIDED_FOR_REVISION.');
      setVoidBill(null);
      setSelectedBill(null);
      fetchBills();
    } catch (err: any) {
      alert(err?.message || 'Failed to void bill for revision');
    }
  };

  const filteredBills = bills.filter((b) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return b.bill_number.toLowerCase().includes(q) || (b.table_number && String(b.table_number).includes(q));
  });

  const labelStyle = { display: 'block', fontSize: '11px', fontWeight: 700, textTransform: 'uppercase' as const, color: t.muted, marginBottom: 4 };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black tracking-tight" style={{ color: t.heading }}>Billing &amp; Payment Settlements</h1>
        <p className="text-sm mt-1" style={{ color: t.sub }}>
          Unpaid issued bills, tax breakdowns (GST), payments, and audited manager discounts
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-2xl text-xs"
          style={{ backgroundColor: t.L ? '#fee2e2' : 'rgba(69,10,10,0.6)', border: `1px solid ${t.L ? '#fecaca' : '#7f1d1d'}`, color: t.L ? '#b91c1c' : '#f87171' }}>
          {error}
        </div>
      )}

      {/* Filter Tabs + Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {['ISSUED', 'PAID', 'ALL', 'VOIDED_FOR_REVISION'].map((st) => (
            <button key={st} onClick={() => setStatusFilter(st)}
              className="px-3.5 py-1.5 rounded-xl text-xs font-semibold transition"
              style={statusFilter === st ? t.tabActive : t.tabInactive}>
              {st === 'ISSUED' ? 'Unpaid Bills' : st === 'PAID' ? 'Settled Receipts' : st}
            </button>
          ))}
        </div>

        <div className="relative w-64">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: t.muted }} />
          <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search bill # or table..."
            className="w-full pl-10 pr-4 py-2 rounded-xl text-xs focus:outline-none"
            style={t.input} />
        </div>
      </div>

      {/* Bills Table */}
      {isLoading ? (
        <div className="p-12 text-center" style={{ color: t.muted }}>Loading bills...</div>
      ) : filteredBills.length === 0 ? (
        <div className="p-12 text-center rounded-3xl" style={t.emptyState}>No bills found for this status.</div>
      ) : (
        <div className="rounded-3xl overflow-hidden shadow-lg" style={t.tableWrap}>
          <table className="w-full text-left text-sm">
            <thead style={t.thead}>
              <tr>
                {['Invoice #', 'Table', 'Status', 'Generated (IST)', 'Subtotal', 'Discount', 'Grand Total'].map((h, i) => (
                  <th key={h} className={`px-6 py-4 font-semibold text-xs uppercase tracking-wider ${i >= 4 ? 'text-right' : ''}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredBills.map((b) => (
                <tr key={b.id} onClick={() => setSelectedBill(b)}
                  className="transition cursor-pointer"
                  style={{ ...t.tbodyRow, borderBottom: `1px solid ${t.border}` }}
                  onMouseEnter={(e) => (e.currentTarget as HTMLTableRowElement).style.backgroundColor = t.tbodyRowHover.backgroundColor as string}
                  onMouseLeave={(e) => (e.currentTarget as HTMLTableRowElement).style.backgroundColor = ''}>
                  <td className="px-6 py-4 font-mono font-bold flex items-center gap-2" style={{ color: t.value }}>
                    <Receipt className="w-4 h-4" style={{ color: t.accent }} />{b.bill_number}
                  </td>
                  <td className="px-6 py-4 font-semibold" style={{ color: t.value }}>Table {b.table_number || '—'}</td>
                  <td className="px-6 py-4"><StatusBadge status={b.status} size="sm" /></td>
                  <td className="px-6 py-4 text-xs font-mono" style={{ color: t.sub }}>{formatDateTimeIst(b.generated_at)}</td>
                  <td className="px-6 py-4 text-right font-mono" style={{ color: t.sub }}>{formatInr(b.subtotal_amount)}</td>
                  <td className="px-6 py-4 text-right font-mono" style={{ color: '#D97706' }}>
                    {parseFloat(b.discount_amount) > 0 ? `-${formatInr(b.discount_amount)}` : '₹0.00'}
                  </td>
                  <td className="px-6 py-4 text-right font-mono font-black" style={{ color: t.value }}>{formatInr(b.grand_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Bill Detail Modal */}
      {selectedBill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: t.modal.backgroundColor, backdropFilter: 'blur(4px)' }}>
          <div className="w-full max-w-lg rounded-3xl p-6 shadow-2xl relative" style={t.modalInner}>
            <div className="flex items-start justify-between pb-4" style={{ borderBottom: `1px solid ${t.border}` }}>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-black" style={{ color: t.heading }}>{selectedBill.bill_number}</h3>
                  <StatusBadge status={selectedBill.status} size="sm" />
                </div>
                <p className="text-xs mt-1" style={{ color: t.sub }}>
                  Table #{selectedBill.table_number || '—'} • Generated {formatDateTimeIst(selectedBill.generated_at)}
                </p>
              </div>
              <button onClick={() => setSelectedBill(null)} style={{ color: t.muted }}>
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Financial breakdown */}
            <div className="mt-6 space-y-3 p-4 rounded-2xl text-xs font-mono" style={t.cardInner}>
              {[
                { label: 'Subtotal (Items)', val: formatInr(selectedBill.subtotal_amount), color: t.sub },
                ...(parseFloat(selectedBill.discount_amount) > 0 ? [{ label: `Discount (${selectedBill.discount_reason || 'Admin'})`, val: `-${formatInr(selectedBill.discount_amount)}`, color: '#D97706' }] : []),
                { label: 'Taxable Amount', val: formatInr(selectedBill.taxable_amount), color: t.sub },
                { label: `CGST (${selectedBill.cgst_percentage}%)`, val: formatInr(selectedBill.cgst_amount), color: t.sub },
                { label: `SGST (${selectedBill.sgst_percentage}%)`, val: formatInr(selectedBill.sgst_amount), color: t.sub },
              ].map(({ label, val, color }) => (
                <div key={label} className="flex justify-between" style={{ color }}><span>{label}</span><span>{val}</span></div>
              ))}
              <div className="pt-2 flex justify-between text-base font-black" style={{ borderTop: `1px solid ${t.border}`, color: t.heading }}>
                <span className="font-sans">Grand Total</span>
                <span>{formatInr(selectedBill.grand_total)}</span>
              </div>
            </div>

            {/* Payment record */}
            {selectedBill.payments && selectedBill.payments.length > 0 && (
              <div className="mt-4 p-3.5 rounded-2xl text-xs"
                style={{ backgroundColor: t.L ? '#dcfce7' : 'rgba(5,46,22,0.3)', border: `1px solid ${t.L ? '#bbf7d0' : 'rgba(74,222,128,0.2)'}` }}>
                <div className="flex items-center gap-2 font-bold mb-1" style={{ color: t.L ? '#15803d' : '#4ade80' }}>
                  <CreditCard className="w-4 h-4" />
                  <span>Settled via {selectedBill.payments[0].payment_method}</span>
                </div>
                <p style={{ color: t.sub }}>
                  Ref: {selectedBill.payments[0].reference_number || 'N/A'} • Completed {formatDateTimeIst(selectedBill.payments[0].completed_at)}
                </p>
              </div>
            )}

            {/* Admin actions for ISSUED */}
            {selectedBill.status === 'ISSUED' && (
              <div className="mt-6 pt-4 flex items-center gap-3" style={{ borderTop: `1px solid ${t.border}` }}>
                <button onClick={() => setDiscountBill(selectedBill)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl text-xs font-semibold transition cursor-pointer"
                  style={{ backgroundColor: t.L ? '#eff6ff' : '#1e1b4b', color: t.L ? '#1d4ed8' : '#a5b4fc', border: `1px solid ${t.L ? '#bfdbfe' : 'rgba(99,102,241,0.4)'}` }}>
                  <Percent className="w-4 h-4" /><span>Apply Manager Discount</span>
                </button>
                <button onClick={() => setVoidBill(selectedBill)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl text-xs font-semibold transition cursor-pointer"
                  style={{ backgroundColor: t.L ? '#fee2e2' : '#450a0a', color: t.L ? '#b91c1c' : '#fca5a5', border: `1px solid ${t.L ? '#fecaca' : 'rgba(248,113,113,0.3)'}` }}>
                  <RotateCcw className="w-4 h-4" /><span>Void for Revision</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Apply Discount Modal */}
      {discountBill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" style={{ backgroundColor: t.modal.backgroundColor, backdropFilter: 'blur(4px)' }}>
          <div className="w-full max-w-sm rounded-3xl p-6 shadow-2xl" style={t.modalInner}>
            <h3 className="text-base font-bold" style={{ color: t.heading }}>Apply Manager Discount</h3>
            <p className="text-xs mt-1" style={{ color: t.sub }}>Invoice: {discountBill.bill_number}</p>
            <div className="mt-4 space-y-3">
              <div>
                <label style={labelStyle}>Discount Amount (₹)</label>
                <input type="number" step="0.01" value={discountAmount} onChange={(e) => setDiscountAmount(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none" style={t.input} />
              </div>
              <div>
                <label style={labelStyle}>Mandatory Reason</label>
                <input type="text" value={discountReason} onChange={(e) => setDiscountReason(e.target.value)}
                  placeholder="Manager goodwill, long wait complaint..."
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm focus:outline-none" style={t.input} />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button onClick={() => setDiscountBill(null)} className="px-4 py-2 rounded-xl text-xs" style={{ color: t.sub }}>Cancel</button>
              <button onClick={handleApplyDiscount} className="px-4 py-2 rounded-xl text-xs font-bold text-white" style={{ backgroundColor: t.accent }}>
                Apply Discount
              </button>
            </div>
          </div>
        </div>
      )}

      <ConfirmModal
        isOpen={!!voidBill}
        title={`Void Invoice ${voidBill?.bill_number} for Revision`}
        description="Marking this bill as VOIDED_FOR_REVISION unlocks the table session so staff can add or adjust items, then generate a revised bill."
        confirmLabel="Void for Revision"
        requireReason={true}
        reasonPlaceholder="Guest wanted to order extra dishes before final settlement..."
        variant="warning"
        onConfirm={handleConfirmVoidForRevision}
        onCancel={() => setVoidBill(null)}
      />
    </div>
  );
};
