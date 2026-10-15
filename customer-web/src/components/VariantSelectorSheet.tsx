import React, { useMemo, useState } from 'react';
import type { CartItem, MenuItem, MenuPriceVariant } from '../types';
import { formatInr } from '../utils/currency';
import { useCart } from '../context/CartContext';
import { Plus, Minus } from 'lucide-react';
import { resolveMediaUrl } from '../utils/env';

interface VariantSelectorSheetProps {
  item: MenuItem | null;
  onClose: () => void;
}

const DietaryBadge: React.FC<{ type: string | null }> = ({ type }) => {
  if (!type) return null;
  const cfg: Record<string, { label: string; fg: string; bg: string; border: string }> = {
    VEG:     { label: '🥗 Vegetarian', fg: 'var(--green)',   bg: 'var(--green-light)',   border: 'var(--green)' },
    NON_VEG: { label: '🍗 Non-Veg',    fg: '#B91C1C',        bg: '#FEF2F2',              border: '#B91C1C' },
    EGG:     { label: '🥚 Egg',        fg: 'var(--amber)',   bg: 'var(--amber-light)',   border: 'var(--amber)' },
  };
  const c = cfg[type];
  if (!c) return null;
  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full"
      style={{ color: c.fg, background: c.bg, border: `1px solid ${c.border}` }}
    >
      {c.label}
    </span>
  );
};

const UNIT_SHORT: Record<string, string> = {
  PIECE: 'pcs',
  ML: 'ml',
  L: 'L',
  GRAM: 'g',
  KG: 'kg',
};

/** "6 pcs" / "250 ml"; nothing for plain portions (Half / Full already say it). */
function portionDetail(v: MenuPriceVariant): string {
  const short = UNIT_SHORT[String(v.unit).toUpperCase()];
  const qty = parseFloat(String(v.quantity_value));
  if (!short || isNaN(qty)) return '';
  if (v.variant_name.toLowerCase().includes(String(qty))) return '';
  return `${qty} ${short}`;
}

const MAX_PER_PORTION = 20;

export const VariantSelectorSheet: React.FC<VariantSelectorSheetProps> = ({ item, onClose }) => {
  if (!item) return null;
  // key = remount with fresh state whenever a different dish is opened
  return <SheetBody key={item.id} item={item} onClose={onClose} />;
};

const SheetBody: React.FC<{ item: MenuItem; onClose: () => void }> = ({ item, onClose }) => {
  const { items: cartItems, setItemLines } = useCart();

  const availableVariants = useMemo(() => item.variants.filter((v) => v.is_available), [item]);
  const defaultVariant =
    availableVariants.find((v) => v.is_default) || availableVariants[0] || item.variants[0];

  const existingLines = cartItems.filter((c) => c.menuItemId === item.id);
  const isEditing = existingLines.length > 0;

  // Quantity per portion. Opens with what is already in the cart, else 1 of the default portion.
  const [quantities, setQuantities] = useState<Record<string, number>>(() => {
    const q: Record<string, number> = {};
    if (existingLines.length > 0) {
      existingLines.forEach((l) => {
        q[l.variantId] = (q[l.variantId] || 0) + l.quantity;
      });
    } else if (defaultVariant) {
      q[defaultVariant.id] = 1;
    }
    return q;
  });
  const [itemNotes, setItemNotes] = useState<string>(existingLines[0]?.itemNotes ?? '');

  const setQty = (variantId: string, next: number) =>
    setQuantities((prev) => ({
      ...prev,
      [variantId]: Math.max(0, Math.min(MAX_PER_PORTION, next)),
    }));

  const selected = availableVariants
    .map((v) => ({ variant: v, qty: quantities[v.id] || 0 }))
    .filter((r) => r.qty > 0);
  const totalQty = selected.reduce((n, r) => n + r.qty, 0);
  const totalPrice = selected.reduce((sum, r) => sum + (parseFloat(String(r.variant.price)) || 0) * r.qty, 0);
  const summary = selected.map((r) => `${r.qty} × ${r.variant.variant_name}`).join(' + ');

  const handleConfirm = () => {
    const notes = itemNotes.trim() ? itemNotes.trim() : undefined;
    const lines: CartItem[] = selected.map((r) => ({
      variantId: r.variant.id,
      menuItemId: item.id,
      itemName: item.name,
      variantName: r.variant.variant_name,
      price: parseFloat(String(r.variant.price)) || 0,
      quantity: r.qty,
      itemNotes: notes,
    }));
    setItemLines(item.id, lines);
    onClose();
  };

  const imageUrl = resolveMediaUrl(item.image_url);

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 animate-fade-in"
      style={{ background: 'rgba(40,40,32,0.5)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-[var(--bg-card)] rounded-t-3xl sm:rounded-3xl shadow-2xl border border-[var(--border)] flex flex-col animate-slide-up sm:animate-scale-in max-h-[85dvh] sm:max-h-[85vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-center pt-3 sm:hidden">
          <div className="w-10 h-1 rounded-full" style={{ background: 'var(--border)' }} />
        </div>

        {/* Header */}
        <div className="flex items-start justify-between px-5 pt-3 pb-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex-1 min-w-0 pr-3">
            <div className="flex items-center gap-2 mb-1.5 flex-wrap">
              <DietaryBadge type={item.dietary_type} />
              <span className="text-[11px] font-mono" style={{ color: 'var(--text-muted)' }}>
                {item.item_code}
              </span>
            </div>
            <h2 className="text-lg font-bold leading-tight" style={{ color: 'var(--text-primary)' }}>
              {item.name}
            </h2>
            {item.description && (
              <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
                {item.description}
              </p>
            )}
          </div>
          <DishThumb url={imageUrl} name={item.name} dietary={item.dietary_type} />
        </div>

        {/* Portions, each with its own quantity */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-5">
          {availableVariants.length > 0 && (
            <div>
              <label
                className="block text-xs font-semibold uppercase tracking-wide mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                {availableVariants.length > 1 ? 'Choose portions & quantity' : 'Quantity'}
              </label>
              {availableVariants.length > 1 && (
                <p className="text-[11px] mb-2.5" style={{ color: 'var(--text-muted)' }}>
                  You can mix portions, e.g. 1 Full + 2 Half.
                </p>
              )}
              <div className="space-y-2">
                {availableVariants.map((variant) => {
                  const qty = quantities[variant.id] || 0;
                  const detail = portionDetail(variant);
                  const active = qty > 0;
                  return (
                    <div
                      key={variant.id}
                      className="w-full flex items-center justify-between gap-3 p-3 rounded-2xl border transition-all"
                      style={
                        active
                          ? { background: 'var(--primary-bg)', border: '1.5px solid var(--primary)' }
                          : { background: 'var(--bg-subtle)', border: '1px solid var(--border)' }
                      }
                    >
                      <div className="min-w-0">
                        <div className="text-sm font-semibold leading-tight" style={{ color: 'var(--text-primary)' }}>
                          {variant.variant_name}
                          {detail && (
                            <span className="text-xs font-normal ml-1.5" style={{ color: 'var(--text-muted)' }}>
                              ({detail})
                            </span>
                          )}
                        </div>
                        <div
                          className="text-sm font-bold font-mono mt-0.5"
                          style={{ color: active ? 'var(--primary)' : 'var(--text-secondary)' }}
                        >
                          {formatInr(variant.price)}
                        </div>
                      </div>

                      {active ? (
                        <div
                          className="flex items-center gap-1 p-1 rounded-xl shrink-0"
                          style={{ border: '1.5px solid var(--primary)', background: 'var(--white)' }}
                        >
                          <button
                            type="button"
                            onClick={() => setQty(variant.id, qty - 1)}
                            className="w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer"
                            style={{ color: 'var(--primary)' }}
                            aria-label={`Decrease ${variant.variant_name}`}
                          >
                            <Minus size={14} strokeWidth={2.5} />
                          </button>
                          <span className="w-6 text-center font-bold text-sm font-mono" style={{ color: 'var(--primary)' }}>
                            {qty}
                          </span>
                          <button
                            type="button"
                            onClick={() => setQty(variant.id, qty + 1)}
                            className="w-8 h-8 rounded-lg flex items-center justify-center cursor-pointer"
                            style={{ background: 'var(--primary)', color: '#fff' }}
                            aria-label={`Increase ${variant.variant_name}`}
                          >
                            <Plus size={14} strokeWidth={2.5} />
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setQty(variant.id, 1)}
                          className="px-4 py-1.5 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center gap-1 cursor-pointer shrink-0"
                          style={{ background: 'var(--white)', color: 'var(--primary)', border: '1.5px solid var(--primary)' }}
                        >
                          <Plus size={13} strokeWidth={3} />
                          <span>Add</span>
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Item notes */}
          <div>
            <label
              className="block text-xs font-semibold uppercase tracking-wide mb-1.5"
              style={{ color: 'var(--text-muted)' }}
            >
              Special Instructions <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Optional)</span>
            </label>
            <input
              type="text"
              value={itemNotes}
              onChange={(e) => setItemNotes(e.target.value)}
              placeholder="Less spicy, no onions, extra crispy…"
              maxLength={100}
              className="w-full rounded-xl px-3.5 py-2.5 text-sm focus:outline-none transition"
              style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
              onFocus={(e) => (e.currentTarget.style.borderColor = 'var(--primary)')}
              onBlur={(e) => (e.currentTarget.style.borderColor = 'var(--border)')}
            />
          </div>
        </div>

        {/* Footer CTA */}
        <div className="px-5 pb-6 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
          {summary && (
            <p className="text-[11px] mb-2 text-center" style={{ color: 'var(--text-muted)' }}>
              {summary}
            </p>
          )}
          {totalQty === 0 && isEditing ? (
            <button
              type="button"
              onClick={handleConfirm}
              className="w-full px-4 py-3 rounded-2xl font-bold text-sm cursor-pointer"
              style={{ background: '#FEF2F2', color: '#B91C1C', border: '1.5px solid #B91C1C' }}
            >
              Remove from cart
            </button>
          ) : (
            <button
              type="button"
              onClick={handleConfirm}
              disabled={totalQty === 0}
              className="btn-primary w-full disabled:opacity-50"
            >
              <span>{totalQty === 0 ? 'Select a portion' : isEditing ? 'Update cart' : 'Add to Cart'}</span>
              {totalQty > 0 && <span className="ml-auto font-bold">{formatInr(totalPrice)}</span>}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

const DishThumb: React.FC<{ url: string | null; name: string; dietary: string | null }> = ({ url, name, dietary }) => {
  const [failed, setFailed] = useState(false);
  return (
    <div
      className="w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 flex items-center justify-center text-2xl"
      style={{ background: 'var(--bg-subtle)' }}
    >
      {url && !failed ? (
        <img src={url} alt={name} className="w-full h-full object-cover" onError={() => setFailed(true)} />
      ) : (
        <span>{dietary === 'VEG' ? '🥗' : dietary === 'EGG' ? '🍳' : '🍛'}</span>
      )}
    </div>
  );
};
