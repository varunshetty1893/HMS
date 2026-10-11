import React, { useEffect, useState } from 'react';
import { ordersBillsApi } from '@/api/ordersBillsApi';
import { formatInr } from '@/utils/currency';
import { formatDateTimeIst } from '@/utils/dateIst';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ConfirmModal } from '@/components/common/ConfirmModal';
import {
  CreditCard,
  Percent,
  Receipt,
  RotateCcw,
  Search,
  X,
} from 'lucide-react';
import { Bill } from '@/types/api';

export const BillingAndPaymentsPage: React.FC = () => {
  const [bills, setBills] = useState<Bill[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ISSUED');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Selected bill for detail view
  const [selectedBill, setSelectedBill] = useState<Bill | null>(null);

  // Admin discount modal
  const [discountBill, setDiscountBill] = useState<Bill | null>(null);
  const [discountAmount, setDiscountAmount] = useState('50.00');
  const [discountReason, setDiscountReason] = useState('Manager goodwill');

  // Void for revision modal
  const [voidBill, setVoidBill] = useState<Bill | null>(null);

  const fetchBills = async () => {
    setIsLoading(true);
    try {
      const data = await ordersBillsApi.listBills({
        status: statusFilter === 'ALL' ? undefined : statusFilter,
      });
      setBills(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to load bills');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchBills();
  }, [statusFilter]);

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
      await ordersBillsApi.voidBillForRevision(
        voidBill.id,
        reason || 'Voided for order item revision'
      );
      alert('Bill marked as VOIDED_FOR_REVISION. Orders can now be adjusted.');
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
    return (
      b.bill_number.toLowerCase().includes(q) ||
      (b.table_number && String(b.table_number).includes(q))
    );
  });

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-white">Billing & Payment Settlements</h1>
          <p className="text-sm text-slate-400 mt-1">
            Unpaid issued bills, tax breakdowns (GST), payments, and audited manager discounts
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {['ISSUED', 'PAID', 'ALL', 'VOIDED_FOR_REVISION'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold transition ${
                statusFilter === st
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              {st === 'ISSUED' ? 'Unpaid Bills' : st === 'PAID' ? 'Settled Receipts' : st}
            </button>
          ))}
        </div>

        <div className="relative w-64">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search bill # or table..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Bills Table */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Loading bills...</div>
      ) : filteredBills.length === 0 ? (
        <div className="p-12 text-center rounded-3xl bg-slate-900/40 border border-slate-800 text-slate-400">
          No bills found for this status.
        </div>
      ) : (
        <div className="rounded-3xl border border-slate-800 bg-slate-900/60 overflow-hidden shadow-2xl">
          <table className="w-full text-left text-sm text-slate-300">
            <thead className="bg-slate-950/70 text-xs uppercase tracking-wider text-slate-400 border-b border-slate-800">
              <tr>
                <th className="px-6 py-4 font-semibold">Invoice #</th>
                <th className="px-6 py-4 font-semibold">Table</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold">Generated (IST)</th>
                <th className="px-6 py-4 font-semibold text-right">Subtotal</th>
                <th className="px-6 py-4 font-semibold text-right">Discount</th>
                <th className="px-6 py-4 font-semibold text-right">Grand Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {filteredBills.map((b) => (
                <tr
                  key={b.id}
                  onClick={() => setSelectedBill(b)}
                  className="hover:bg-slate-800/40 transition cursor-pointer"
                >
                  <td className="px-6 py-4 font-mono font-bold text-white flex items-center gap-2">
                    <Receipt className="w-4 h-4 text-indigo-400" />
                    <span>{b.bill_number}</span>
                  </td>
                  <td className="px-6 py-4 font-semibold text-slate-200">Table {b.table_number || '—'}</td>
                  <td className="px-6 py-4">
                    <StatusBadge status={b.status} size="sm" />
                  </td>
                  <td className="px-6 py-4 text-xs text-slate-400 font-mono">
                    {formatDateTimeIst(b.generated_at)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-slate-300">{formatInr(b.subtotal_amount)}</td>
                  <td className="px-6 py-4 text-right font-mono text-amber-400">
                    {parseFloat(b.discount_amount) > 0 ? `-${formatInr(b.discount_amount)}` : '₹0.00'}
                  </td>
                  <td className="px-6 py-4 text-right font-mono font-black text-white">
                    {formatInr(b.grand_total)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Bill Detail & Action Modal */}
      {selectedBill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-3xl bg-slate-900 border border-slate-800 p-6 shadow-2xl relative">
            <div className="flex items-start justify-between pb-4 border-b border-slate-800">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-xl font-black text-white">{selectedBill.bill_number}</h3>
                  <StatusBadge status={selectedBill.status} size="sm" />
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  Table #{selectedBill.table_number || '—'} • Generated {formatDateTimeIst(selectedBill.generated_at)}
                </p>
              </div>
              <button onClick={() => setSelectedBill(null)} className="text-slate-400 hover:text-white p-1">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Financial breakdown */}
            <div className="mt-6 space-y-3 p-4 rounded-2xl bg-slate-950 border border-slate-800 text-xs font-mono">
              <div className="flex justify-between text-slate-400">
                <span>Subtotal (Items)</span>
                <span>{formatInr(selectedBill.subtotal_amount)}</span>
              </div>
              {parseFloat(selectedBill.discount_amount) > 0 && (
                <div className="flex justify-between text-amber-400">
                  <span>Discount ({selectedBill.discount_reason || 'Admin'})</span>
                  <span>-{formatInr(selectedBill.discount_amount)}</span>
                </div>
              )}
              <div className="flex justify-between text-slate-400">
                <span>Taxable Amount</span>
                <span>{formatInr(selectedBill.taxable_amount)}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>CGST ({selectedBill.cgst_percentage}%)</span>
                <span>{formatInr(selectedBill.cgst_amount)}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>SGST ({selectedBill.sgst_percentage}%)</span>
                <span>{formatInr(selectedBill.sgst_amount)}</span>
              </div>
              <div className="pt-2 border-t border-slate-800 flex justify-between text-base font-black text-white">
                <span className="font-sans">Grand Total</span>
                <span>{formatInr(selectedBill.grand_total)}</span>
              </div>
            </div>

            {/* Payment record if paid */}
            {selectedBill.payments && selectedBill.payments.length > 0 && (
              <div className="mt-4 p-3.5 rounded-2xl bg-emerald-950/30 border border-emerald-800/40 text-xs">
                <div className="flex items-center gap-2 text-emerald-400 font-bold mb-1">
                  <CreditCard className="w-4 h-4" />
                  <span>Settled via {selectedBill.payments[0].payment_method}</span>
                </div>
                <p className="text-slate-400">
                  Ref: {selectedBill.payments[0].reference_number || 'N/A'} • Completed {formatDateTimeIst(selectedBill.payments[0].completed_at)}
                </p>
              </div>
            )}

            {/* Admin Override Actions for ISSUED bills */}
            {selectedBill.status === 'ISSUED' && (
              <div className="mt-6 pt-4 border-t border-slate-800 flex items-center gap-3">
                <button
                  onClick={() => setDiscountBill(selectedBill)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl text-xs font-semibold bg-indigo-950 hover:bg-indigo-900 text-indigo-300 border border-indigo-800/50 transition cursor-pointer"
                >
                  <Percent className="w-4 h-4" />
                  <span>Apply Manager Discount</span>
                </button>
                <button
                  onClick={() => setVoidBill(selectedBill)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl text-xs font-semibold bg-rose-950 hover:bg-rose-900 text-rose-300 border border-rose-800/50 transition cursor-pointer"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Void for Revision</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Apply Discount Modal */}
      {discountBill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
          <div className="w-full max-w-sm rounded-3xl bg-slate-900 border border-slate-800 p-6 shadow-2xl">
            <h3 className="text-base font-bold text-white">Apply Manager Discount</h3>
            <p className="text-xs text-slate-400 mt-1">Invoice: {discountBill.bill_number}</p>
            <div className="mt-4 space-y-3">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Discount Amount (₹)</label>
                <input
                  type="number"
                  step="0.01"
                  value={discountAmount}
                  onChange={(e) => setDiscountAmount(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm font-mono text-white"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Mandatory Reason</label>
                <input
                  type="text"
                  value={discountReason}
                  onChange={(e) => setDiscountReason(e.target.value)}
                  placeholder="Manager goodwill, long wait complaint..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setDiscountBill(null)}
                className="px-4 py-2 rounded-xl text-xs text-slate-300 hover:bg-slate-800"
              >
                Cancel
              </button>
              <button
                onClick={handleApplyDiscount}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                Apply Discount
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Void for Revision Confirmation */}
      <ConfirmModal
        isOpen={!!voidBill}
        title={`Void Invoice ${voidBill?.bill_number} for Revision`}
        description="Marking this bill as VOIDED_FOR_REVISION unlocks the table session so staff can add or adjust items, then generate a revised bill. The void action is immutably audit-logged."
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
