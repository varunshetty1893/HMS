import React, { useState } from 'react';
import type { MenuItem, MenuPriceVariant } from '../types';
import { formatInr } from '../utils/currency';
import { useCart } from '../context/CartContext';
import { Plus, Minus, Check } from 'lucide-react';

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

export const VariantSelectorSheet: React.FC<VariantSelectorSheetProps> = ({ item, onClose }) => {
  const { addItem } = useCart();

  if (!item) return null;

  const availableVariants = item.variants.filter((v) => v.is_available);
  const defaultVariant =
    availableVariants.find((v) => v.is_default) || availableVariants[0] || item.variants[0];

  const [selectedVariant, setSelectedVariant] = useState<MenuPriceVariant>(defaultVariant);
  const [quantity, setQuantity] = useState<number>(1);
  const [itemNotes, setItemNotes] = useState<string>('');

  const variantPrice = parseFloat(String(selectedVariant?.price ?? '0')) || 0;
  const totalPrice = variantPrice * quantity;

  const handleAddToCart = () => {
    if (!selectedVariant) return;
    addItem({
      variantId: selectedVariant.id,
      menuItemId: item.id,
      itemName: item.name,
      variantName: selectedVariant.variant_name,
      price: variantPrice,
      quantity,
      itemNotes: itemNotes.trim() ? itemNotes.trim() : undefined,
    });
    onClose();
  };

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
        {/* Handle (mobile only) */}
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
          {/* Dish image thumbnail */}
          <div
            className="w-16 h-16 rounded-xl overflow-hidden flex-shrink-0 flex items-center justify-center text-2xl"
            style={{ background: 'var(--bg-subtle)' }}
          >
            {item.image_url ? (
              <img src={item.image_url} alt={item.name} className="w-full h-full object-cover"
                onError={e => { e.currentTarget.style.display='none'; e.currentTarget.nextElementSibling!.removeAttribute('hidden'); }}
              />
            ) : null}
            <span hidden={!!item.image_url}>
              {item.dietary_type === 'VEG' ? '🥗' : item.dietary_type === 'NON_VEG' ? '🍗' : '🍳'}
            </span>
          </div>
        </div>

        {/* Scrollable content */}
        <div className="overflow-y-auto flex-1 px-5 py-4 space-y-5">
          {/* Variant selection */}
          {availableVariants.length > 0 && (
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wide mb-2.5"
                style={{ color: 'var(--text-muted)' }}>
                Choose Portion
              </label>
              <div className="space-y-2">
                {availableVariants.map((variant) => {
                  const isSelected = selectedVariant?.id === variant.id;
                  return (
                    <button
                      key={variant.id}
                      type="button"
                      onClick={() => setSelectedVariant(variant)}
                      className="w-full flex items-center justify-between p-3.5 rounded-2xl border text-left transition-all"
                      style={
                        isSelected
                          ? { background: 'var(--primary-bg)', border: '1.5px solid var(--primary)' }
                          : { background: 'var(--bg-subtle)', border: '1px solid var(--border)' }
                      }
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className="w-4 h-4 rounded-full border-2 flex items-center justify-center flex-shrink-0"
                          style={
                            isSelected
                              ? { borderColor: 'var(--primary)', background: 'var(--primary)' }
                              : { borderColor: 'var(--border)', background: 'transparent' }
                          }
                        >
                          {isSelected && <Check size={9} strokeWidth={3} color="#fff" />}
                        </div>
                        <div>
                          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            {variant.variant_name}
                          </span>
                          <span className="text-xs ml-1.5" style={{ color: 'var(--text-muted)' }}>
                            ({variant.quantity_value} {variant.unit})
                          </span>
                        </div>
                      </div>
                      <span className="font-bold text-sm" style={{ color: isSelected ? 'var(--primary)' : 'var(--text-primary)' }}>
                        {formatInr(variant.price)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Quantity */}
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
              Quantity
            </span>
            <div
              className="flex items-center gap-1 p-1 rounded-xl"
              style={{ border: '1.5px solid var(--border)', background: 'var(--bg-subtle)' }}
            >
              <button
                type="button"
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                style={{ background: 'var(--white)', color: 'var(--text-primary)' }}
              >
                <Minus size={14} />
              </button>
              <span className="w-7 text-center font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                {quantity}
              </span>
              <button
                type="button"
                onClick={() => setQuantity((q) => Math.min(20, q + 1))}
                className="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                style={{ background: 'var(--primary)', color: '#fff' }}
              >
                <Plus size={14} />
              </button>
            </div>
          </div>

          {/* Item notes */}
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wide mb-1.5"
              style={{ color: 'var(--text-muted)' }}>
              Special Instructions <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(Optional)</span>
            </label>
            <input
              type="text"
              value={itemNotes}
              onChange={(e) => setItemNotes(e.target.value)}
              placeholder="Less spicy, no onions, extra crispy…"
              maxLength={100}
              className="w-full rounded-xl px-3.5 py-2.5 text-sm focus:outline-none transition"
              style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
              onFocus={e => e.currentTarget.style.borderColor = 'var(--primary)'}
              onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
            />
          </div>
        </div>

        {/* Footer CTA */}
        <div className="px-5 pb-6 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
          <button
            type="button"
            onClick={handleAddToCart}
            className="btn-primary w-full"
          >
            <span>Add to Cart</span>
            <span className="ml-auto font-bold">{formatInr(totalPrice)}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
