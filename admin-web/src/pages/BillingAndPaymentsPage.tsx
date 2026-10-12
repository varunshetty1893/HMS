import React, { useEffect, useState } from 'react';
import { ordersBillsApi } from '@/api/ordersBillsApi';
import { formatInr } from '@/utils/currency';
import { formatDateTimeIst } from '@/utils/dateIst';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ConfirmModal } from '@/components/common/ConfirmModal';
import { usePageTheme } from '@/hooks/usePageTheme';
import {
  AlertCircle,
  CheckCircle2,
  CreditCard,
  Percent,
  Receipt,
  RotateCcw,
  Search,
  X,
} from 'lucide-react';
import { Bill } from '@/types/api';

const BILL_TABS: { label: string; value: string }[] = [
  { label: 'Unpaid Bills', value: 'ISSUED' },
  { label: 'Paid Bills', value: 'PAID' },
  { label: 'All Bills', value: 'ALL' },
  { label: 'Cancelled for Revision', value: 'VOIDED_FOR_REVISION' },
];

export const BillingAndPaymentsPage: React.FC = () => {
  const { L, heading, sub, muted, border, card, tableWrap, thead, tbodyRowHover, input, select, tabActive, tabInactive, modalInner } = usePageTheme();

  const [bills, setBills] = useState<Bill[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('ISSUED');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  const [selectedBill, setSelectedBill] = useState<Bill | null>(null);
  const [discountBill, setDiscountBill] = useState<Bill | null>(null);
  const [discountAmount, setDiscountAmount] = useState('50.00');
  const [discountReason, setDiscountReason] = useState('Manager goodwill');
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
      setError(err?.message || 'Failed to load restaurant bills');
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
      const amount = parseFloat(discountAmount);
      if (isNaN(amount) || amount <= 0) {
        alert('Please enter a valid discount amount');
        return;
      }
      await ordersBillsApi.applyDiscount(
        discountBill.id,
        amount.toFixed(2),
        discountReason || 'Manager courtesy discount'
      );
      setSuccessBanner(`Discount of ₹${amount.toFixed(2)} applied to bill #${discountBill.bill_number}.`);
      setDiscountBill(null);
      fetchBills();
      setTimeout(() => setSuccessBanner(null), 5000);
    } catch (err: any) {
      alert(err?.message || 'Failed to apply discount');
    }
  };

  const handleConfirmCancelBill = async (reason?: string) => {
    if (!voidBill) return;
    try {
      await ordersBillsApi.voidBillForRevision(
        voidBill.id,
        reason || 'Void for correction'
      );
      setSuccessBanner(`Bill #${voidBill.bill_number} marked as cancelled for correction.`);
      setVoidBill(null);
      fetchBills();
      setTimeout(() => setSuccessBanner(null), 5000);
    } catch (err: any) {
      alert(err?.message || 'Failed to cancel bill');
    }
  };

  const filteredBills = bills.filter((b) => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    return (
      b.bill_number.toLowerCase().includes(q) ||
      String(b.table_number || '').includes(q)
    );
  });

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight flex items-center gap-2.5" style={{ color: heading }}>
            <Receipt className="w-6 h-6 text-brand-500" />
            <span>Billing & Payments</span>
          </h1>
          <p className="text-sm mt-1" style={{ color: sub }}>
            Cashier settlement desk, table checks, GST tax calculation, and discounts
          </p>
        </div>
      </div>

      {/* Success Banner */}
      {successBanner && (
        <div
          className="p-4 rounded-2xl text-xs flex items-center justify-between animate-in fade-in"
          style={{
            backgroundColor: L ? '#dcfce7' : 'rgba(5,46,22,0.6)',
            borderColor: L ? '#bbf7d0' : '#166534',
            borderWidth: 1,
            borderStyle: 'solid',
            color: L ? '#15803d' : '#86efac',
          }}
        >
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{successBanner}</span>
          </div>
          <button onClick={() => setSuccessBanner(null)} className="cursor-pointer opacity-80 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Error Alert */}
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
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="cursor-pointer opacity-80 hover:opacity-100">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter Tabs & Search */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
          {BILL_TABS.map((tab) => {
            const isActive = statusFilter === tab.value;
            return (
              <button
                key={tab.value}
                onClick={() => setStatusFilter(tab.value)}
                className="px-3.5 py-1.5 rounded-xl text-xs font-semibold shrink-0 transition cursor-pointer"
                style={isActive ? tabActive : tabInactive}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: muted }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search bill # or table..."
            className="w-full pl-10 pr-4 py-2 rounded-xl text-xs focus:outline-none"
            style={input}
          />
        </div>
      </div>

      {/* Bills Table */}
      {isLoading ? (
        <div
          className="p-16 text-center rounded-2xl"
          style={{ ...card, color: muted }}
        >
          <div className="inline-block w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin" />
          <p className="mt-3 text-sm">Loading bills...</p>
        </div>
      ) : filteredBills.length === 0 ? (
        <div
          className="p-16 text-center rounded-2xl"
          style={{ ...card, color: sub }}
        >
          <Receipt className="w-8 h-8 mx-auto mb-2" style={{ color: muted }} />
          <p className="font-semibold" style={{ color: heading }}>No bills found</p>
          <p className="text-xs mt-1" style={{ color: muted }}>There are no bills under this category right now.</p>
        </div>
      ) : (
        <div className="rounded-2xl overflow-hidden shadow-xl" style={tableWrap}>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm" style={{ color: heading }}>
              <thead className="text-xs uppercase tracking-wider border-b" style={{ ...thead, borderBottomColor: border }}>
                <tr>
                  <th className="px-6 py-4 font-semibold">Bill #</th>
                  <th className="px-6 py-4 font-semibold">Table</th>
                  <th className="px-6 py-4 font-semibold">Status</th>
                  <th className="px-6 py-4 font-semibold">Generated Time</th>
                  <th className="px-6 py-4 font-semibold text-right">Items Subtotal</th>
                  <th className="px-6 py-4 font-semibold text-right">Discount</th>
                  <th className="px-6 py-4 font-semibold text-right">Grand Total</th>
                </tr>
              </thead>
              <tbody>
                {filteredBills.map((b) => (
                  <tr
                    key={b.id}
                    onClick={() => setSelectedBill(b)}
                    className="transition cursor-pointer border-b"
                    style={{ borderBottomColor: border }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.backgroundColor = tbodyRowHover.backgroundColor as string;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }}
                  >
                    <td className="px-6 py-4 font-mono font-bold flex items-center gap-2" style={{ color: heading }}>
                      <Receipt className="w-4 h-4 text-brand-500 shrink-0" />
                      <span>{b.bill_number}</span>
                    </td>
                    <td className="px-6 py-4 font-semibold" style={{ color: heading }}>
                      Table {b.table_number || '—'}
                    </td>
                    <td className="px-6 py-4">
                      <StatusBadge status={b.status} size="sm" />
                    </td>
                    <td className="px-6 py-4 text-xs font-mono" style={{ color: muted }}>
                      {formatDateTimeIst(b.generated_at)}
                    </td>
                    <td className="px-6 py-4 text-right font-mono" style={{ color: sub }}>
                      {formatInr(b.subtotal_amount)}
                    </td>
                    <td className="px-6 py-4 text-right font-mono font-semibold" style={{ color: '#d97706' }}>
                      {parseFloat(b.discount_amount) > 0 ? `-${formatInr(b.discount_amount)}` : '₹0.00'}
                    </td>
                    <td className="px-6 py-4 text-right font-mono font-black" style={{ color: heading }}>
                      {formatInr(b.grand_total)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Bill Detail Modal */}
      {selectedBill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-2xl p-6 shadow-2xl relative" style={modalInner}>
            <div className="flex items-start justify-between pb-4 border-b" style={{ borderBottomColor: border }}>
              <div>
                <div className="flex items-center gap-2.5">
                  <h3 className="text-xl font-black" style={{ color: heading }}>{selectedBill.bill_number}</h3>
                  <StatusBadge status={selectedBill.status} size="sm" />
                </div>
                <p className="text-xs mt-1" style={{ color: sub }}>
                  Table #{selectedBill.table_number || '—'} • Generated {formatDateTimeIst(selectedBill.generated_at)}
                </p>
              </div>
              <button
                onClick={() => setSelectedBill(null)}
                className="p-1 rounded-lg cursor-pointer opacity-70 hover:opacity-100"
                style={{ color: muted }}
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Bill Summary */}
            <div className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between py-1 border-b" style={{ borderBottomColor: border, color: sub }}>
                <span>Subtotal (Items)</span>
                <span className="font-mono font-medium" style={{ color: heading }}>{formatInr(selectedBill.subtotal_amount)}</span>
              </div>
              {parseFloat(selectedBill.discount_amount) > 0 && (
                <div className="flex justify-between py-1 border-b text-amber-500" style={{ borderBottomColor: border }}>
                  <span>Discount ({selectedBill.discount_reason || 'Special'})</span>
                  <span className="font-mono font-semibold">-{formatInr(selectedBill.discount_amount)}</span>
                </div>
              )}
              <div className="flex justify-between py-1 border-b" style={{ borderBottomColor: border, color: sub }}>
                <span>CGST (2.5%)</span>
                <span className="font-mono" style={{ color: heading }}>{formatInr(selectedBill.cgst_amount)}</span>
              </div>
              <div className="flex justify-between py-1 border-b" style={{ borderBottomColor: border, color: sub }}>
                <span>SGST (2.5%)</span>
                <span className="font-mono" style={{ color: heading }}>{formatInr(selectedBill.sgst_amount)}</span>
              </div>
              <div className="flex justify-between py-2 text-base font-bold" style={{ color: heading }}>
                <span>Grand Total</span>
                <span className="font-mono font-black text-lg text-brand-600">{formatInr(selectedBill.grand_total)}</span>
              </div>
            </div>

            {/* Modal Actions */}
            <div className="mt-6 pt-4 border-t flex items-center justify-end gap-3" style={{ borderTopColor: border }}>
              {selectedBill.status === 'ISSUED' && (
                <>
                  <button
                    onClick={() => {
                      setDiscountBill(selectedBill);
                      setSelectedBill(null);
                    }}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold cursor-pointer"
                    style={{
                      backgroundColor: L ? '#fef3c7' : 'rgba(120,53,15,0.4)',
                      color: L ? '#b45309' : '#fcd34d',
                      border: `1px solid ${L ? '#fde68a' : 'rgba(245,158,11,0.3)'}`,
                    }}
                  >
                    <Percent className="w-3.5 h-3.5" />
                    <span>Apply Discount</span>
                  </button>
                  <button
                    onClick={() => {
                      setVoidBill(selectedBill);
                      setSelectedBill(null);
                    }}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold cursor-pointer"
                    style={{
                      backgroundColor: L ? '#fee2e2' : 'rgba(127,29,29,0.4)',
                      color: L ? '#b91c1c' : '#fca5a5',
                      border: `1px solid ${L ? '#fecaca' : 'rgba(239,68,68,0.3)'}`,
                    }}
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    <span>Cancel for Correction</span>
                  </button>
                </>
              )}
              <button
                onClick={() => setSelectedBill(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer"
                style={{
                  backgroundColor: L ? '#f5f0e8' : '#1e293b',
                  color: heading,
                  border: `1px solid ${border}`,
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Discount Modal */}
      {discountBill && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
          <div className="w-full max-w-sm rounded-2xl p-6 shadow-2xl space-y-4" style={modalInner}>
            <div className="flex items-center justify-between pb-3 border-b" style={{ borderBottomColor: border }}>
              <h3 className="font-bold text-base" style={{ color: heading }}>Apply Discount</h3>
              <button onClick={() => setDiscountBill(null)} className="opacity-70 hover:opacity-100" style={{ color: muted }}>
                <X className="w-4 h-4" />
              </button>
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Discount Amount (₹)</label>
              <input
                type="number"
                step="0.01"
                value={discountAmount}
                onChange={(e) => setDiscountAmount(e.target.value)}
                className="w-full px-3 py-2 rounded-xl text-sm font-mono focus:outline-none"
                style={input}
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Reason</label>
              <input
                type="text"
                value={discountReason}
                onChange={(e) => setDiscountReason(e.target.value)}
                placeholder="Manager goodwill / VIP discount"
                className="w-full px-3 py-2 rounded-xl text-sm focus:outline-none"
                style={input}
              />
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => setDiscountBill(null)}
                className="px-3.5 py-2 rounded-xl text-xs font-semibold cursor-pointer"
                style={{
                  backgroundColor: L ? '#f5f0e8' : '#1e293b',
                  color: heading,
                  border: `1px solid ${border}`,
                }}
              >
                Cancel
              </button>
              <button
                onClick={handleApplyDiscount}
                className="px-4 py-2 rounded-xl text-xs font-semibold bg-brand-600 text-white cursor-pointer hover:bg-brand-500 shadow-md"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Cancel Bill Modal */}
      <ConfirmModal
        isOpen={!!voidBill}
        title={`Cancel Bill #${voidBill?.bill_number} for Correction`}
        description="This cancels the current bill so kitchen or items can be updated, and a new corrected bill generated. This action is permanently recorded in the audit logs."
        confirmLabel="Yes, Cancel Bill"
        cancelLabel="Keep Bill"
        requireReason={true}
        reasonPlaceholder="e.g. Table swapped / Applied wrong combo discount"
        variant="danger"
        onConfirm={handleConfirmCancelBill}
        onCancel={() => setVoidBill(null)}
      />
    </div>
  );
};
