import React, { useMemo, useState } from 'react';
import type { CustomerItemChange, MenuItem, OrderResponse } from '../types';
import { formatInr } from '../utils/currency';
import { AlertTriangle, ChefHat, Loader2, Lock, Minus, Plus } from 'lucide-react';

const MAX_LINE_QTY = 20;

interface OrderEditPanelProps {
  order: OrderResponse;
  /** menu_item_id -> menu item (used to find cheaper portions, e.g. Full -> Half) */
  menuItems: Record<string, MenuItem>;
  onSave: (orderId: string, expectedVersion: number, changes: CustomerItemChange[]) => Promise<void>;
  onClose: () => void;
}

interface SwitchDraft {
  variantId: string;
  qty: number;
}

/**
 * Customer self-service edit of an order. Mirrors the backend rules (backend is the authority):
 *   PLACED / ACCEPTED : + / - / remove / switch to a cheaper portion
 *   PREPARING         : only +  (and Full -> Half correction); - and remove are locked
 */
export const OrderEditPanel: React.FC<OrderEditPanelProps> = ({
  order,
  menuItems,
  onSave,
  onClose,
}) => {
  const preCooking =
    order.status === 'PLACED' || order.status === 'SUBMITTED' || order.status === 'ACCEPTED';

  const liveItems = order.items.filter((i) => i.active_quantity > 0 && i.item_status !== 'CANCELLED');

  const [qty, setQty] = useState<Record<string, number>>(
    () => Object.fromEntries(liveItems.map((i) => [i.id, i.active_quantity])),
  );
  const [switches, setSwitches] = useState<Record<string, SwitchDraft | null>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const cheaperVariants = (menuItemId: string, currentVariantId: string, currentPrice: number) => {
    const mi = menuItems[menuItemId];
    if (!mi) return [];
    return mi.variants.filter(
      (v) =>
        v.id !== currentVariantId &&
        v.is_available &&
        v.price !== null &&
        parseFloat(v.price) < currentPrice,
    );
  };

  const { changes, delta, removesEverything } = useMemo(() => {
    const out: CustomerItemChange[] = [];
    let d = 0;
    let remaining = 0;
    for (const item of liveItems) {
      const unit = parseFloat(item.unit_price_snapshot);
      const sw = switches[item.id];
      if (sw) {
        const target = menuItems[item.menu_item_id]?.variants.find((v) => v.id === sw.variantId);
        if (target) {
          out.push({
            order_item_id: item.id,
            switch_to_variant_id: sw.variantId,
            switch_quantity: sw.qty,
          });
          d += sw.qty * (parseFloat(target.price || '0') - unit);
        }
        remaining += item.active_quantity;
        continue;
      }
      const q = qty[item.id] ?? item.active_quantity;
      remaining += q;
      if (q !== item.active_quantity) {
        out.push({ order_item_id: item.id, new_quantity: q });
        d += (q - item.active_quantity) * unit;
      }
    }
    return { changes: out, delta: d, removesEverything: remaining === 0 };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [qty, switches, order]);

  const handleSave = async () => {
    if (changes.length === 0) return;
    setSaving(true);
    setError(null);
    try {
      await onSave(order.id, order.version, changes);
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Could not update the order.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3 pt-1">
      {!preCooking && (
        <div className="flex items-start gap-2 p-2.5 rounded-xl text-[11px] bg-amber-50/80 border border-amber-200/80 text-amber-900">
          <ChefHat size={15} className="text-amber-700 shrink-0 mt-0.5" />
          <span className="font-medium">
            Cooking has started. You can add more or switch to a smaller portion, but items
            can&apos;t be reduced or removed. For anything else, please ask your waiter.
          </span>
        </div>
      )}

      {liveItems.map((item) => {
        const unit = parseFloat(item.unit_price_snapshot);
        const current = qty[item.id] ?? item.active_quantity;
        const sw = switches[item.id] ?? null;
        const minQty = preCooking ? 0 : item.active_quantity;
        const options = cheaperVariants(item.menu_item_id, item.menu_price_variant_id, unit);
        const qtyChanged = current !== item.active_quantity;
        const canMinus = !sw && current > minQty;
        const canPlus = !sw && current < MAX_LINE_QTY;

        return (
          <div
            key={item.id}
            className="rounded-2xl p-3 space-y-2"
            style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border)' }}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="text-xs font-bold truncate" style={{ color: 'var(--text-primary)' }}>
                  {item.item_name_snapshot}
                </p>
                <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                  {item.variant_name_snapshot} · {formatInr(unit)} each
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  type="button"
                  disabled={!canMinus}
                  onClick={() => setQty((p) => ({ ...p, [item.id]: current - 1 }))}
                  className="w-8 h-8 rounded-full flex items-center justify-center border transition disabled:opacity-35"
                  style={{ borderColor: 'var(--border)', background: 'var(--white)' }}
                  aria-label={`Decrease ${item.item_name_snapshot}`}
                  title={!preCooking && current <= minQty ? 'Cooking started - cannot reduce' : ''}
                >
                  {!preCooking && current <= minQty ? <Lock size={12} /> : <Minus size={14} />}
                </button>
                <span
                  className="w-6 text-center text-sm font-bold font-mono"
                  style={{ color: current === 0 ? '#DC2626' : 'var(--text-primary)' }}
                >
                  {current}
                </span>
                <button
                  type="button"
                  disabled={!canPlus}
                  onClick={() => setQty((p) => ({ ...p, [item.id]: current + 1 }))}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-white transition disabled:opacity-35"
                  style={{ background: 'var(--primary)' }}
                  aria-label={`Increase ${item.item_name_snapshot}`}
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>

            {current === 0 && (
              <p className="text-[11px] font-semibold text-red-600">This dish will be removed.</p>
            )}

            {/* Portion switch (e.g. Full -> Half) — never to a bigger portion */}
            {options.length > 0 && !qtyChanged && (
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <span className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                  Ordered by mistake? Switch to
                </span>
                <select
                  value={sw?.variantId ?? ''}
                  onChange={(e) => {
                    const v = e.target.value;
                    setSwitches((p) => ({
                      ...p,
                      [item.id]: v ? { variantId: v, qty: sw?.qty ?? 1 } : null,
                    }));
                  }}
                  className="text-[11px] rounded-lg px-2 py-1 border"
                  style={{ borderColor: 'var(--border)', background: 'var(--white)' }}
                >
                  <option value="">Keep {item.variant_name_snapshot}</option>
                  {options.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.variant_name} ({formatInr(parseFloat(v.price || '0'))})
                    </option>
                  ))}
                </select>
                {sw && item.active_quantity > 1 && (
                  <label className="text-[11px] flex items-center gap-1" style={{ color: 'var(--text-secondary)' }}>
                    how many
                    <select
                      value={sw.qty}
                      onChange={(e) =>
                        setSwitches((p) => ({
                          ...p,
                          [item.id]: { variantId: sw.variantId, qty: parseInt(e.target.value, 10) },
                        }))
                      }
                      className="rounded-lg px-1.5 py-1 border"
                      style={{ borderColor: 'var(--border)', background: 'var(--white)' }}
                    >
                      {Array.from({ length: item.active_quantity }, (_, i) => i + 1).map((n) => (
                        <option key={n} value={n}>
                          {n}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>
            )}
          </div>
        );
      })}

      {removesEverything && preCooking && changes.length > 0 && (
        <div className="flex items-start gap-2 p-2.5 rounded-xl text-[11px] bg-red-50 border border-red-200 text-red-800">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <span>Removing every dish will cancel this whole order.</span>
        </div>
      )}

      {error && <p className="text-[11px] font-semibold text-red-600">{error}</p>}

      <div className="flex items-center justify-between pt-1">
        <span className="text-xs font-mono font-bold" style={{ color: 'var(--text-secondary)' }}>
          {changes.length === 0
            ? 'No changes yet'
            : `${delta >= 0 ? '+' : '-'}${formatInr(Math.abs(delta))}`}
        </span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="px-3.5 py-2 rounded-xl text-xs font-semibold bg-white border border-stone-300 text-stone-700 hover:bg-stone-50 transition"
          >
            Close
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving || changes.length === 0}
            className="px-4 py-2 rounded-xl text-xs font-bold text-white shadow-sm transition flex items-center gap-1.5 disabled:opacity-50"
            style={{ background: 'var(--primary)' }}
          >
            {saving && <Loader2 size={13} className="animate-spin" />}
            <span>Save changes</span>
          </button>
        </div>
      </div>
    </div>
  );
};
