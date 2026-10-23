import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Banknote,
  CheckCircle2,
  CreditCard,
  Loader2,
  Minus,
  Plus,
  QrCode,
  RotateCcw,
  Search,
  Trash2,
} from 'lucide-react';
import { Bill, Payment, TableBillCheck } from '@/types/api';
import { PaperWidth, printReceipt, receiptPrefs } from '@/utils/receipt';
import {
  MenuSearchItem,
  TableOrderSummary,
  ordersBillsApi,
} from '@/api/ordersBillsApi';

export interface PanelTheme {
  L: boolean;
  heading: string;
  sub: string;
  muted: string;
  border: string;
  card: React.CSSProperties;
  input: React.CSSProperties;
}

interface Props {
  checks: TableBillCheck[];
  theme: PanelTheme;
  onRefresh: () => Promise<void>;
  /** Bill created and fully paid. */
  onPaid: (message: string) => void;
  /** Bill created but not (fully) settled - parent opens the bill. */
  onBillCreated: (bill: Bill, message?: string) => void;
}

type Method = 'CASH' | 'UPI' | 'CARD';
interface Edit {
  qty: number;
  price: string;
}
interface ExtraLine {
  key: string;
  name: string;
  qty: number;
  price: string;
}

const r2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;
const inr = (n: number) =>
  `₹${n.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const num = (v: string | number | null | undefined) => {
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
};

const BillAndCollectPanel: React.FC<Props> = ({ checks, theme, onRefresh, onPaid, onBillCreated }) => {
  const { L, heading, sub, muted, border, card, input } = theme;

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [edits, setEdits] = useState<Record<string, Edit>>({});
  const [extras, setExtras] = useState<ExtraLine[]>([]);
  const [changeReason, setChangeReason] = useState('Adjusted at billing');
  const [discountMode, setDiscountMode] = useState<'AMOUNT' | 'PERCENT'>('AMOUNT');
  const [discountValue, setDiscountValue] = useState('');
  const [discountReason, setDiscountReason] = useState('');
  const [method, setMethod] = useState<Method>('CASH');
  const [tendered, setTendered] = useState('');
  const [reference, setReference] = useState('');
  const [notes, setNotes] = useState('');
  const [autoPrint, setAutoPrint] = useState<boolean>(receiptPrefs.getAutoPrint());
  const [paper, setPaper] = useState<PaperWidth>(receiptPrefs.getPaper());

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<MenuSearchItem[]>([]);
  const [searching, setSearching] = useState(false);
  const [customName, setCustomName] = useState('');
  const [customPrice, setCustomPrice] = useState('');

  const [orders, setOrders] = useState<TableOrderSummary[]>([]);
  const [servingId, setServingId] = useState<string | null>(null);
  const [busy, setBusy] = useState<'pay' | 'bill' | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Keep a valid selection as tables appear / get billed.
  useEffect(() => {
    if (checks.length === 0) {
      setSelectedId(null);
    } else if (!selectedId || !checks.some((c) => c.table_id === selectedId)) {
      setSelectedId(checks[0].table_id);
    }
  }, [checks, selectedId]);

  const check = checks.find((c) => c.table_id === selectedId) ?? null;

  // Reset the working draft when switching tables.
  useEffect(() => {
    setEdits({});
    setExtras([]);
    setDiscountValue('');
    setDiscountReason('');
    setTendered('');
    setReference('');
    setNotes('');
    setQuery('');
    setResults([]);
    setError(null);
  }, [selectedId]);

  // Order statuses for the selected table (refreshed whenever the live check changes).
  const checkSignature = check
    ? `${check.preview_grand_total}-${check.preview_line_items.length}-${check.has_unserved_orders}-${check.has_unaccepted_placed_orders}`
    : '';
  useEffect(() => {
    if (!check) {
      setOrders([]);
      return;
    }
    let cancelled = false;
    ordersBillsApi
      .getTableOrders(check.table_id)
      .then((o) => !cancelled && setOrders(o))
      .catch(() => !cancelled && setOrders([]));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [check?.table_id, checkSignature]);

  // Debounced menu search.
  const searchSeq = useRef(0);
  useEffect(() => {
    const q = query.trim();
    if (q.length < 1) {
      setResults([]);
      return;
    }
    const seq = ++searchSeq.current;
    setSearching(true);
    const t = setTimeout(() => {
      ordersBillsApi
        .searchMenu(q)
        .then((r) => seq === searchSeq.current && setResults(r.slice(0, 8)))
        .catch(() => seq === searchSeq.current && setResults([]))
        .finally(() => seq === searchSeq.current && setSearching(false));
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  // ── Working bill ──────────────────────────────────────────────────────────
  const lines = useMemo(
    () =>
      (check?.preview_line_items ?? []).map((item) => {
        const id = item.id as string;
        const edit = edits[id];
        const origQty = item.quantity_billed;
        const origPrice = num(item.unit_price_snapshot);
        const qty = edit ? edit.qty : origQty;
        const price = edit ? edit.price : origPrice.toFixed(2);
        const changed = qty !== origQty || r2(num(price)) !== r2(origPrice);
        return { item, id, origQty, origPrice, qty, price, changed };
      }),
    [check, edits]
  );

  const extrasSubtotal = extras.reduce((s, e) => s + r2(num(e.price) * e.qty), 0);
  const subtotal = r2(lines.reduce((s, l) => s + r2(num(l.price) * l.qty), 0) + extrasSubtotal);
  const rawDiscount = num(discountValue);
  const discount = Math.min(
    subtotal,
    discountMode === 'PERCENT' ? r2((subtotal * Math.min(rawDiscount, 100)) / 100) : r2(rawDiscount)
  );
  const taxable = r2(subtotal - discount);
  const baseTaxable = num(check?.preview_taxable);
  const cgstRate = baseTaxable > 0 ? (num(check?.preview_cgst) / baseTaxable) * 100 : 2.5;
  const sgstRate = baseTaxable > 0 ? (num(check?.preview_sgst) / baseTaxable) * 100 : 2.5;
  const cgst = r2((taxable * cgstRate) / 100);
  const sgst = r2((taxable * sgstRate) / 100);
  const total = r2(taxable + cgst + sgst);

  const tenderedNum = tendered.trim() ? num(tendered) : total;
  const change = method === 'CASH' ? Math.max(0, r2(tenderedNum - total)) : 0;
  const waiting = !!check && (check.has_unaccepted_placed_orders || check.has_unserved_orders);

  const setLineQty = (id: string, origPrice: number, current: Edit | undefined, qty: number) => {
    const next = Math.max(0, Math.min(999, qty));
    setEdits((prev) => ({
      ...prev,
      [id]: { qty: next, price: current ? current.price : origPrice.toFixed(2) },
    }));
  };
  const setLinePrice = (id: string, origQty: number, current: Edit | undefined, price: string) => {
    setEdits((prev) => ({
      ...prev,
      [id]: { qty: current ? current.qty : origQty, price },
    }));
  };

  const addExtra = (key: string, name: string, price: number) => {
    setExtras((prev) => {
      const existing = prev.find((e) => e.key === key);
      if (existing) return prev.map((e) => (e.key === key ? { ...e, qty: Math.min(999, e.qty + 1) } : e));
      return [...prev, { key, name, qty: 1, price: price.toFixed(2) }];
    });
  };

  const addCustom = () => {
    const price = num(customPrice);
    if (!customName.trim() || price <= 0) {
      setError('Enter a name and a price greater than zero for the custom item.');
      return;
    }
    setError(null);
    addExtra(`custom-${crypto.randomUUID()}`, customName.trim(), price);
    setCustomName('');
    setCustomPrice('');
  };

  const handleServe = async (o: TableOrderSummary) => {
    setServingId(o.id);
    try {
      await ordersBillsApi.serveOrder(o.id, o.version);
      await onRefresh();
    } catch (e: any) {
      setError(e?.message || 'Could not mark the order as served.');
    } finally {
      setServingId(null);
    }
  };

  // ── Submit ────────────────────────────────────────────────────────────────
  const buildPayload = () => {
    const reason = changeReason.trim().length >= 3 ? changeReason.trim() : 'Adjusted at billing';
    return {
      discount_amount: discount.toFixed(2),
      discount_reason: discount > 0 ? discountReason.trim() || 'Admin discount' : null,
      price_overrides: lines
        .filter((l) => l.changed)
        .map((l) => ({
          order_item_id: l.id,
          unit_price: r2(num(l.price)).toFixed(2),
          quantity_billed: l.qty,
          reason,
        })),
      custom_line_items: extras
        .filter((e) => e.qty >= 1 && num(e.price) >= 0.01)
        .map((e) => ({
          item_name: e.name,
          quantity: e.qty,
          unit_price: r2(num(e.price)).toFixed(2),
          reason: 'Added at billing',
        })),
    };
  };

  const validate = (): string | null => {
    if (!check) return 'Select a table first.';
    if (waiting) return 'All orders must be served before the bill can be generated.';
    if (total <= 0) return 'The bill total must be greater than zero.';
    if (lines.some((l) => num(l.price) < 0)) return 'Prices cannot be negative.';
    if (extras.some((e) => num(e.price) < 0.01)) return 'Every added item needs a price.';
    return null;
  };

  const submit = async (collect: boolean) => {
    const problem = validate();
    if (problem || !check) {
      setError(problem);
      return;
    }
    if (collect && method === 'CASH' && tenderedNum < total) {
      setError(`Cash received must be at least ${inr(total)}.`);
      return;
    }
    setError(null);
    setBusy(collect ? 'pay' : 'bill');
    let bill: Bill;
    try {
      bill = await ordersBillsApi.generateBill(check.table_number, buildPayload());
    } catch (e: any) {
      setError(e?.message || 'Could not generate the bill.');
      setBusy(null);
      return;
    }
    if (!collect) {
      setBusy(null);
      if (autoPrint) void printReceipt(bill, paper);
      onBillCreated(bill);
      return;
    }
    try {
      const amount = num(bill.grand_total);
      const received = method === 'CASH' ? Math.max(tenderedNum, amount) : amount;
      await ordersBillsApi.recordPayment(bill.id, {
        payment_method: method,
        amount_paid: amount.toFixed(2),
        amount_tendered: method === 'CASH' ? received.toFixed(2) : null,
        reference_number: reference.trim() || null,
        notes: notes.trim() || null,
      });
      if (autoPrint) {
        const settled: Payment = {
          id: 'local',
          bill_id: bill.id,
          payment_method: method,
          amount_paid: amount.toFixed(2),
          amount_tendered: method === 'CASH' ? received.toFixed(2) : null,
          change_returned: method === 'CASH' ? r2(Math.max(0, received - amount)).toFixed(2) : '0.00',
          status: 'COMPLETED',
          reference_number: reference.trim() || null,
          completed_at: new Date().toISOString(),
        };
        void printReceipt({ ...bill, status: 'PAID', payments: [settled] }, paper);
      }
      const changeMsg =
        method === 'CASH' && received > amount ? ` Return ${inr(r2(received - amount))} change.` : '';
      onPaid(`Table ${check.table_number} settled · ${bill.bill_number} · ${inr(amount)}.${changeMsg}`);
    } catch (e: any) {
      onBillCreated(
        bill,
        `Bill ${bill.bill_number} was created, but the payment was not saved: ${e?.message || 'unknown error'}. Record it here.`
      );
    } finally {
      setBusy(null);
    }
  };

  const chip = (status: string): React.CSSProperties => {
    if (status === 'SERVED') return { backgroundColor: '#dcfce7', color: '#166534' };
    if (status === 'READY') return { backgroundColor: '#dbeafe', color: '#1e40af' };
    return { backgroundColor: '#fef3c7', color: '#92400e' };
  };

  const methodBtn = (m: Method, label: string, icon: React.ReactNode) => (
    <button
      key={m}
      onClick={() => setMethod(m)}
      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs font-bold cursor-pointer"
      style={
        method === m
          ? { backgroundColor: '#ea580c', color: '#fff', border: '1px solid #ea580c' }
          : { color: heading, border: `1px solid ${border}` }
      }
    >
      {icon}
      {label}
    </button>
  );

  if (checks.length === 0) {
    return (
      <div className="rounded-3xl p-12 text-center" style={card}>
        <CheckCircle2 className="w-10 h-10 mx-auto text-emerald-500" />
        <h3 className="mt-3 text-lg font-black" style={{ color: heading }}>All tables are settled</h3>
        <p className="text-sm mt-1" style={{ color: sub }}>
          Tables that have ordered will appear here, ready to bill and collect.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[220px_minmax(0,1fr)] gap-4 items-start">
      {/* Table list */}
      <div className="space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wider" style={{ color: sub }}>
          Tables ordering · {checks.length}
        </h2>
        {checks.map((c) => {
          const w = c.has_unaccepted_placed_orders || c.has_unserved_orders;
          const active = c.table_id === selectedId;
          return (
            <button
              key={c.table_id}
              onClick={() => setSelectedId(c.table_id)}
              className="w-full text-left rounded-xl p-3 border-l-4 cursor-pointer transition"
              style={{
                ...card,
                borderLeftColor: w ? '#f59e0b' : '#10b981',
                outline: active ? '2px solid #ea580c' : 'none',
              }}
            >
              <div className="flex items-center justify-between">
                <span className="text-base font-black" style={{ color: heading }}>Table {c.table_number}</span>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold" style={w ? chip('PLACED') : chip('SERVED')}>
                  {c.has_unaccepted_placed_orders ? 'Awaiting kitchen' : c.has_unserved_orders ? 'Being served' : 'Ready'}
                </span>
              </div>
              <div className="text-[11px] mt-1 truncate" style={{ color: muted }}>
                {c.preview_line_items.map((i) => `${i.quantity_billed}× ${i.item_name}`).join(' · ')}
              </div>
              <div className="mt-1 text-base font-black font-mono" style={{ color: heading }}>
                {inr(num(c.preview_grand_total))}
              </div>
            </button>
          );
        })}
      </div>

      {/* Editor */}
      {check && (
        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_340px] gap-3 items-start min-w-0">
        <div className="space-y-3 min-w-0">
          <div className="rounded-2xl px-4 py-3" style={card}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-black" style={{ color: heading }}>
                  Table {check.table_number} · Bill &amp; Collect
                </h2>
                <p className="text-xs" style={{ color: sub }}>
                  Change quantities or prices, add items, apply a discount, then collect payment.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {orders.map((o) => (
                  <span key={o.id} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold" style={chip(o.status)}>
                    {o.order_number} · {o.status}
                    {o.status === 'READY' && (
                      <button
                        disabled={servingId === o.id}
                        onClick={() => handleServe(o)}
                        className="ml-1 underline cursor-pointer disabled:opacity-50"
                      >
                        {servingId === o.id ? '…' : 'Mark served'}
                      </button>
                    )}
                  </span>
                ))}
              </div>
            </div>
            {waiting && (
              <p className="mt-3 text-xs font-semibold" style={{ color: '#b45309' }}>
                Some orders are not served yet. Mark READY orders as served above; orders still in the kitchen are handled from Live Orders.
              </p>
            )}
          </div>

          {/* Lines */}
          <div className="rounded-2xl overflow-hidden" style={card}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead style={{ backgroundColor: L ? '#f1f5f9' : '#1e293b', color: muted }}>
                  <tr className="text-[11px] uppercase">
                    <th className="py-2 px-3">Item</th>
                    <th className="py-2 px-2 text-center">Qty</th>
                    <th className="py-2 px-2 text-right">Rate (₹)</th>
                    <th className="py-2 px-3 text-right">Total</th>
                    <th className="py-2 px-2" />
                  </tr>
                </thead>
                <tbody>
                  {lines.map((l) => {
                    const removed = l.qty === 0;
                    return (
                      <tr key={l.id} className="border-t" style={{ borderColor: border, opacity: removed ? 0.5 : 1 }}>
                        <td className="py-2 px-3">
                          <div className={`font-bold ${removed ? 'line-through' : ''}`} style={{ color: heading }}>
                            {l.item.item_name}
                            {l.item.variant_name && l.item.variant_name.toUpperCase() !== 'STANDARD' && (
                              <span className="font-normal" style={{ color: muted }}> ({l.item.variant_name})</span>
                            )}
                          </div>
                          <div className="text-[11px]" style={{ color: muted }}>
                            {l.item.order_number}
                            {l.changed && <span className="ml-2 font-bold text-amber-600">edited · was {l.origQty} × {inr(l.origPrice)}</span>}
                          </div>
                        </td>
                        <td className="py-2 px-2">
                          <div className="flex items-center justify-center gap-1.5">
                            <button onClick={() => setLineQty(l.id, l.origPrice, edits[l.id], l.qty - 1)} className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer" style={{ border: `1px solid ${border}`, color: heading }}><Minus className="w-3.5 h-3.5" /></button>
                            <span className="w-8 text-center font-mono font-bold" style={{ color: heading }}>{l.qty}</span>
                            <button onClick={() => setLineQty(l.id, l.origPrice, edits[l.id], l.qty + 1)} className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer" style={{ border: `1px solid ${border}`, color: heading }}><Plus className="w-3.5 h-3.5" /></button>
                          </div>
                        </td>
                        <td className="py-2 px-2 text-right">
                          <input
                            type="number"
                            min="0"
                            step="0.01"
                            value={l.price}
                            onChange={(e) => setLinePrice(l.id, l.origQty, edits[l.id], e.target.value)}
                            className="w-24 px-2 py-1.5 rounded-lg text-right font-mono text-sm"
                            style={input}
                          />
                        </td>
                        <td className="py-2 px-3 text-right font-mono font-bold" style={{ color: heading }}>{inr(r2(num(l.price) * l.qty))}</td>
                        <td className="py-2 px-2">
                          {removed || l.changed ? (
                            <button title="Restore original" onClick={() => setEdits((p) => { const n = { ...p }; delete n[l.id]; return n; })} className="cursor-pointer" style={{ color: muted }}><RotateCcw className="w-4 h-4" /></button>
                          ) : (
                            <button title="Remove from bill" onClick={() => setLineQty(l.id, l.origPrice, edits[l.id], 0)} className="cursor-pointer text-rose-500"><Trash2 className="w-4 h-4" /></button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                  {extras.map((e) => (
                    <tr key={e.key} className="border-t" style={{ borderColor: border, backgroundColor: L ? '#fffbeb' : 'rgba(120,53,15,0.12)' }}>
                      <td className="py-2 px-3">
                        <div className="font-bold" style={{ color: heading }}>{e.name}</div>
                        <div className="text-[11px] font-bold text-amber-600">Added at billing</div>
                      </td>
                      <td className="py-2 px-2">
                        <div className="flex items-center justify-center gap-1.5">
                          <button onClick={() => setExtras((p) => p.flatMap((x) => (x.key === e.key ? (x.qty <= 1 ? [] : [{ ...x, qty: x.qty - 1 }]) : [x])))} className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer" style={{ border: `1px solid ${border}`, color: heading }}><Minus className="w-3.5 h-3.5" /></button>
                          <span className="w-8 text-center font-mono font-bold" style={{ color: heading }}>{e.qty}</span>
                          <button onClick={() => setExtras((p) => p.map((x) => (x.key === e.key ? { ...x, qty: Math.min(999, x.qty + 1) } : x)))} className="w-7 h-7 rounded-lg flex items-center justify-center cursor-pointer" style={{ border: `1px solid ${border}`, color: heading }}><Plus className="w-3.5 h-3.5" /></button>
                        </div>
                      </td>
                      <td className="py-2 px-2 text-right">
                        <input type="number" min="0" step="0.01" value={e.price} onChange={(ev) => setExtras((p) => p.map((x) => (x.key === e.key ? { ...x, price: ev.target.value } : x)))} className="w-24 px-2 py-1.5 rounded-lg text-right font-mono text-sm" style={input} />
                      </td>
                      <td className="py-2 px-3 text-right font-mono font-bold" style={{ color: heading }}>{inr(r2(num(e.price) * e.qty))}</td>
                      <td className="py-2 px-2"><button onClick={() => setExtras((p) => p.filter((x) => x.key !== e.key))} className="cursor-pointer text-rose-500"><Trash2 className="w-4 h-4" /></button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {lines.some((l) => l.changed) && (
              <div className="px-4 py-3 border-t flex items-center gap-3" style={{ borderColor: border }}>
                <label className="text-[11px] font-bold uppercase" style={{ color: muted }}>Reason for changes</label>
                <input value={changeReason} onChange={(e) => setChangeReason(e.target.value)} className="flex-1 px-3 py-1.5 rounded-lg text-sm" style={input} />
              </div>
            )}
          </div>

          {/* Add items */}
          <div className="rounded-2xl px-4 py-3 space-y-2" style={card}>
            <h3 className="text-sm font-black" style={{ color: heading }}>Add items</h3>
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2" style={{ color: muted }} />
              <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search menu by name or code (e.g. biryani, CB)…" className="w-full pl-9 pr-3 py-2.5 rounded-xl text-sm" style={input} />
              {searching && <Loader2 className="w-4 h-4 animate-spin absolute right-3 top-1/2 -translate-y-1/2" style={{ color: muted }} />}
            </div>
            {results.length > 0 && (
              <div className="rounded-2xl border divide-y overflow-hidden" style={{ borderColor: border }}>
                {results.map((item) => (
                  <div key={item.item_id} className="px-4 py-2.5 flex flex-wrap items-center gap-2" style={{ borderColor: border }}>
                    <div className="mr-auto min-w-0">
                      <div className="text-sm font-bold" style={{ color: heading }}>{item.name}</div>
                      <div className="text-[11px]" style={{ color: muted }}>{item.category_name}{!item.is_available && ' · unavailable'}</div>
                    </div>
                    {item.variants.filter((v) => v.price !== null).map((v) => (
                      <button
                        key={v.variant_id}
                        onClick={() => addExtra(v.variant_id, v.variant_name && v.variant_name.toUpperCase() !== 'STANDARD' ? `${item.name} (${v.variant_name})` : item.name, num(v.price))}
                        className="px-3 py-1.5 rounded-lg text-xs font-bold cursor-pointer"
                        style={{ border: `1px solid ${border}`, color: heading }}
                      >
                        + {v.variant_name} · {inr(num(v.price))}
                      </button>
                    ))}
                  </div>
                ))}
              </div>
            )}
            <div className="flex flex-wrap gap-2 pt-1">
              <input value={customName} onChange={(e) => setCustomName(e.target.value)} placeholder="Custom item (e.g. Water bottle)" className="flex-1 min-w-[180px] px-3 py-2 rounded-xl text-sm" style={input} />
              <input type="number" min="0" step="0.01" value={customPrice} onChange={(e) => setCustomPrice(e.target.value)} placeholder="Price ₹" className="w-28 px-3 py-2 rounded-xl text-sm" style={input} />
              <button onClick={addCustom} className="px-4 py-2 rounded-xl text-xs font-bold cursor-pointer" style={{ border: `1px solid ${border}`, color: heading }}>Add custom</button>
            </div>
            <p className="text-[11px]" style={{ color: muted }}>
              Items added here are billed directly. They are not sent to the kitchen and are shown as separate lines on the bill.
            </p>
          </div>

        </div>

        {/* Checkout column */}
        <div className="rounded-2xl p-4 space-y-3 lg:sticky lg:top-3" style={card}>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-black" style={{ color: heading }}>Checkout</h3>
            <span className="text-[11px]" style={{ color: muted }}>Table {check.table_number}</span>
          </div>

          {/* Discount */}
          <div className="flex gap-2">
            <div className="flex rounded-xl overflow-hidden shrink-0" style={{ border: `1px solid ${border}` }}>
              {(['AMOUNT', 'PERCENT'] as const).map((m) => (
                <button key={m} onClick={() => setDiscountMode(m)} className="px-3 py-1.5 text-xs font-bold cursor-pointer" style={discountMode === m ? { backgroundColor: '#ea580c', color: '#fff' } : { color: heading }}>
                  {m === 'AMOUNT' ? '₹' : '%'}
                </button>
              ))}
            </div>
            <input type="number" min="0" step="0.01" value={discountValue} onChange={(e) => setDiscountValue(e.target.value)} placeholder={discountMode === 'AMOUNT' ? 'Discount ₹' : 'Discount %'} className="flex-1 min-w-0 px-3 py-1.5 rounded-xl text-sm" style={input} />
          </div>
          {discount > 0 && (
            <input value={discountReason} onChange={(e) => setDiscountReason(e.target.value)} placeholder="Reason (optional)" className="w-full px-3 py-1.5 rounded-xl text-sm" style={input} />
          )}

          {/* Totals */}
          <div className="rounded-xl border px-3 py-2 text-xs space-y-1" style={{ borderColor: border, color: sub }}>
            <div className="flex justify-between"><span>Subtotal</span><span className="font-mono">{inr(subtotal)}</span></div>
            {discount > 0 && <div className="flex justify-between text-emerald-600"><span>Discount</span><span className="font-mono">−{inr(discount)}</span></div>}
            <div className="flex justify-between"><span>CGST ({cgstRate.toFixed(2)}%)</span><span className="font-mono">{inr(cgst)}</span></div>
            <div className="flex justify-between"><span>SGST ({sgstRate.toFixed(2)}%)</span><span className="font-mono">{inr(sgst)}</span></div>
            <div className="flex justify-between pt-1.5 border-t text-base font-black" style={{ borderColor: border, color: heading }}><span>Total</span><span className="font-mono">{inr(total)}</span></div>
          </div>

          {/* Payment */}
          <div className="flex gap-2">
            {methodBtn('CASH', 'Cash', <Banknote className="w-4 h-4" />)}
            {methodBtn('UPI', 'UPI', <QrCode className="w-4 h-4" />)}
            {methodBtn('CARD', 'Card', <CreditCard className="w-4 h-4" />)}
          </div>
          {method === 'CASH' ? (
            <div className="space-y-2">
              <input type="number" min="0" step="0.01" value={tendered} onChange={(e) => setTendered(e.target.value)} placeholder={`Cash received (default ${inr(total)})`} className="w-full px-3 py-1.5 rounded-xl text-sm font-mono" style={input} />
              <div className="flex gap-1.5 flex-wrap">
                {[total, Math.ceil(total / 10) * 10, Math.ceil(total / 100) * 100, Math.ceil(total / 500) * 500].filter((v, i, a) => v >= total && a.indexOf(v) === i).map((v) => (
                  <button key={v} onClick={() => setTendered(String(v))} className="px-2 py-0.5 rounded-lg text-[11px] font-bold cursor-pointer" style={{ border: `1px solid ${border}`, color: heading }}>{inr(v)}</button>
                ))}
              </div>
              <div className="flex justify-between rounded-xl px-3 py-1.5 text-sm font-bold" style={{ backgroundColor: L ? '#fff7ed' : 'rgba(194,65,12,0.15)', color: '#c2410c' }}>
                <span>Return change</span><span className="font-mono">{inr(change)}</span>
              </div>
            </div>
          ) : (
            <input value={reference} onChange={(e) => setReference(e.target.value)} placeholder={method === 'UPI' ? 'UPI reference (optional)' : 'Card slip no. (optional)'} className="w-full px-3 py-1.5 rounded-xl text-sm" style={input} />
          )}
          <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Notes (optional)" className="w-full px-3 py-1.5 rounded-xl text-sm" style={input} />

          {/* Receipt options */}
          <div className="flex items-center justify-between gap-2 text-xs" style={{ color: sub }}>
            <label className="inline-flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={autoPrint} onChange={(e) => { setAutoPrint(e.target.checked); receiptPrefs.setAutoPrint(e.target.checked); }} />
              Print receipt
            </label>
            <select value={paper} onChange={(e) => { const w = e.target.value as PaperWidth; setPaper(w); receiptPrefs.setPaper(w); }} className="px-2 py-1 rounded-lg text-xs" style={input}>
              <option value="80">80 mm</option>
              <option value="58">58 mm</option>
            </select>
          </div>

          {error && (
            <div className="rounded-xl px-3 py-2 text-xs font-semibold bg-rose-100 text-rose-700">{error}</div>
          )}

          <button
            disabled={busy !== null || waiting}
            onClick={() => submit(true)}
            className="w-full px-4 py-3 rounded-xl text-sm font-black text-white bg-emerald-600 hover:bg-emerald-700 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed inline-flex items-center justify-center gap-2"
          >
            {busy === 'pay' && <Loader2 className="w-4 h-4 animate-spin" />}
            Bill &amp; collect {inr(total)}
          </button>
          <button
            disabled={busy !== null || waiting}
            onClick={() => submit(false)}
            className="w-full px-4 py-2 rounded-xl text-xs font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ border: `1px solid ${border}`, color: heading }}
          >
            {busy === 'bill' ? 'Generating…' : 'Generate bill only (collect later)'}
          </button>
        </div>
        </div>
      )}
    </div>
  );
};

export default BillAndCollectPanel;
