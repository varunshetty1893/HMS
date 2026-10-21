import React from 'react';
import type { MenuItem } from '../types';
import { formatInrShort } from '../utils/currency';
import { Plus, Minus, Flame } from 'lucide-react';
import { useCart } from '../context/CartContext';
import { DishImage } from './DishImage';

interface MenuItemCardProps {
  item: MenuItem;
  onSelect: (item: MenuItem) => void;
  /** True when this dish is among the most ordered. */
  isPopular?: boolean;
  /** Vertical card used in the horizontally scrolling Most Ordered strip. */
  compact?: boolean;
}

export const DietaryBadge: React.FC<{ type: string | null; size?: number }> = ({ type, size = 18 }) => {
  if (!type) return null;
  const isVeg = type === 'VEG';
  const isEgg = type === 'EGG';
  const color = isVeg ? '#1E9E5A' : isEgg ? '#D97706' : '#B91C1C';
  return (
    <div
      title={isVeg ? 'Vegetarian' : isEgg ? 'Contains Egg' : 'Non-Vegetarian'}
      className="rounded-md flex items-center justify-center shrink-0 bg-white"
      style={{ width: size, height: size, border: `1.8px solid ${color}` }}
    >
      <div className="rounded-full" style={{ width: size * 0.5, height: size * 0.5, background: color }} />
    </div>
  );
};

const SpiceBadge: React.FC<{ level: string | null }> = ({ level }) => {
  if (!level) return null;
  const count = level === 'MILD' ? 1 : level === 'MEDIUM' ? 2 : 3;
  return (
    <div className="flex items-center gap-0.5" title={`${level} spice`}>
      {Array.from({ length: count }).map((_, i) => (
        <Flame key={i} size={11} style={{ color: level === 'HOT' ? '#B91C1C' : '#D95D2B' }} />
      ))}
    </div>
  );
};

export const MenuItemCard: React.FC<MenuItemCardProps> = ({ item, onSelect, compact = false }) => {
  const { items: cartItems, updateQuantity } = useCart();

  const availableVariants = item.variants.filter((v) => v.is_available);
  const isSeasonal =
    item.pricing_type === 'SEASONAL' ||
    availableVariants.some((v) => v.pricing_status === 'SEASONAL_UNPRICED' || v.price === null);
  const pricedVariants = availableVariants.filter((v) => v.price !== null && parseFloat(v.price) > 0);
  const minPrice = pricedVariants.length > 0 ? Math.min(...pricedVariants.map((v) => parseFloat(v.price!) || 0)) : 0;
  const isPriceUnavailable = isSeasonal && pricedVariants.length === 0;
  const hasMultipleVariants = availableVariants.length > 1;

  const cartQty = cartItems.filter((c) => c.menuItemId === item.id).reduce((sum, c) => sum + c.quantity, 0);
  const singleVariant = !hasMultipleVariants && availableVariants[0];
  const singleCartItem = singleVariant ? cartItems.find((c) => c.variantId === singleVariant.id) : null;

  const handleAdd = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!item.is_available || isPriceUnavailable) return;
    onSelect(item);
  };
  const handleDecrement = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (singleCartItem) updateQuantity(singleCartItem.variantId, singleCartItem.quantity - 1);
    else onSelect(item);
  };
  const handleIncrement = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (isPriceUnavailable) return;
    if (singleVariant && singleCartItem) updateQuantity(singleCartItem.variantId, singleCartItem.quantity + 1);
    else onSelect(item);
  };

  const soldOut = !item.is_available;

  const priceNode = isPriceUnavailable ? (
    <span className="inline-block text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-md px-1.5 py-0.5">
      Seasonal price
    </span>
  ) : (
    <div className="flex items-baseline gap-1">
      <span className="font-bold text-[17px]" style={{ color: 'var(--text-primary)' }}>{formatInrShort(minPrice)}</span>
      {hasMultipleVariants && <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>onwards</span>}
    </div>
  );

  const stepper = (
    <div
      className="flex items-center rounded-xl overflow-hidden"
      style={{ border: '1.5px solid var(--primary)', background: 'var(--white)' }}
    >
      <button onClick={handleDecrement} className="w-9 h-9 flex items-center justify-center cursor-pointer" style={{ color: 'var(--primary)', background: 'var(--primary-bg)' }} aria-label={`Decrease ${item.name}`}>
        <Minus size={16} strokeWidth={2.5} />
      </button>
      <span className="w-9 text-center text-sm font-bold" style={{ color: 'var(--text-primary)' }}>{cartQty}</span>
      <button onClick={handleIncrement} className="w-9 h-9 flex items-center justify-center cursor-pointer text-white" style={{ background: 'var(--primary)' }} aria-label={`Increase ${item.name}`}>
        <Plus size={16} strokeWidth={2.5} />
      </button>
    </div>
  );

  const addButton = isPriceUnavailable ? (
    <span className="inline-flex items-center justify-center px-3 py-2 text-[11px] font-semibold text-blue-700 bg-blue-50 border border-blue-200 rounded-xl">
      Ask waiter
    </span>
  ) : (
    <button
      onClick={handleAdd}
      disabled={soldOut || availableVariants.length === 0}
      className="w-full h-10 px-4 rounded-xl font-semibold text-sm flex items-center justify-center gap-1.5 cursor-pointer active:scale-95 transition disabled:opacity-50"
      style={{ background: 'var(--white)', color: 'var(--primary)', border: '1.5px solid var(--primary)' }}
      aria-label={`Add ${item.name}`}
    >
      <Plus size={16} strokeWidth={2.5} />
      <span>Add</span>
    </button>
  );

  const actionNode = <div onClick={(e) => e.stopPropagation()}>{cartQty > 0 && !isPriceUnavailable ? stepper : addButton}</div>;

  /* ── Compact vertical card (Most Ordered strip) ── */
  if (compact) {
    return (
      <div
        onClick={() => !soldOut && onSelect(item)}
        className={`snap-start shrink-0 w-[46%] min-w-[170px] max-w-[210px] rounded-2xl p-2 flex flex-col ${soldOut ? 'opacity-50 grayscale pointer-events-none' : 'cursor-pointer'}`}
        style={{ background: 'var(--white)', border: '1px solid var(--border)', boxShadow: '0 2px 10px rgba(40,40,32,0.05)' }}
      >
        <div className="relative w-full aspect-[4/3] rounded-xl overflow-hidden" style={{ background: 'var(--bg-subtle)' }}>
          <DishImage item={item} className="w-full h-full" />
          <div className="absolute top-1.5 left-1.5"><DietaryBadge type={item.dietary_type} /></div>
        </div>
        <h3 className="mt-2 font-bold text-[15px] leading-snug line-clamp-2" style={{ color: 'var(--text-primary)' }}>{item.name}</h3>
        <div className="mt-0.5">{priceNode}</div>
        {item.description && (
          <p className="mt-1 text-xs leading-snug line-clamp-3 min-h-[3.1em]" style={{ color: 'var(--text-secondary)' }}>{item.description}</p>
        )}
        <div className="mt-1.5 flex flex-wrap gap-1 min-h-[22px]">
          {hasMultipleVariants && availableVariants.slice(0, 3).map((v) => (
            <span key={v.id} className="text-[11px] px-2 py-0.5 rounded-md" style={{ background: 'var(--bg-subtle)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
              {v.variant_name}
            </span>
          ))}
        </div>
        <div className="mt-auto pt-2">{actionNode}</div>
      </div>
    );
  }

  /* ── List row ── */
  return (
    <div
      onClick={() => !soldOut && onSelect(item)}
      className={`rounded-2xl p-2.5 flex items-center gap-3 transition-shadow ${soldOut ? 'opacity-50 grayscale pointer-events-none' : 'cursor-pointer hover:shadow-md'}`}
      style={{ background: 'var(--white)', border: '1px solid var(--border)', boxShadow: '0 2px 10px rgba(40,40,32,0.04)' }}
    >
      <div className="w-[92px] h-[92px] sm:w-28 sm:h-28 rounded-xl overflow-hidden shrink-0" style={{ background: 'var(--bg-subtle)' }}>
        <DishImage item={item} className="w-full h-full" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-start gap-2">
          <div className="mt-0.5"><DietaryBadge type={item.dietary_type} size={20} /></div>
          <h3 className="font-bold text-base leading-snug" style={{ color: 'var(--text-primary)' }}>{item.name}</h3>
        </div>
        <div className="mt-0.5 flex items-center gap-2 flex-wrap">
          {priceNode}
          <SpiceBadge level={item.spice_level} />
          {soldOut && (
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full" style={{ background: '#FEF2F2', color: '#B91C1C' }}>Sold out</span>
          )}
        </div>
        {item.description && (
          <p className="mt-0.5 text-[13px] leading-snug line-clamp-2" style={{ color: 'var(--text-secondary)' }}>{item.description}</p>
        )}
        {hasMultipleVariants && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {availableVariants.map((v) => (
              <span key={v.id} className="text-[11px] px-2 py-0.5 rounded-md" style={{ background: 'var(--bg-subtle)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
                {v.variant_name}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="shrink-0 w-[98px]">{actionNode}</div>
    </div>
  );
};
