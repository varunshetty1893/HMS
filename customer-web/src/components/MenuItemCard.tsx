import React from 'react';
import type { MenuItem } from '../types';
import { formatInr } from '../utils/currency';
import { Plus, Minus, Flame, Sparkles } from 'lucide-react';
import { useCart } from '../context/CartContext';

interface MenuItemCardProps {
  item: MenuItem;
  onSelect: (item: MenuItem) => void;
}

// Fallback high-resolution culinary photography
const CULINARY_FALLBACKS: Record<string, string> = {
  biryani: 'https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=600&q=80',
  tikka: 'https://images.unsplash.com/photo-1567188040759-fb8a883dc6d8?auto=format&fit=crop&w=600&q=80',
  kebab: 'https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?auto=format&fit=crop&w=600&q=80',
  chicken: 'https://images.unsplash.com/photo-1603894584373-5ac82b2ae398?auto=format&fit=crop&w=600&q=80',
  paneer: 'https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=600&q=80',
  dal: 'https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=600&q=80',
  naan: 'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80',
  roti: 'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=600&q=80',
  lassi: 'https://images.unsplash.com/photo-1553530666-ba11a7da3888?auto=format&fit=crop&w=600&q=80',
  lime: 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80',
  soda: 'https://images.unsplash.com/photo-1513558161293-cdaf765ed2fd?auto=format&fit=crop&w=600&q=80',
  jamun: 'https://images.unsplash.com/photo-1605197154247-a870d02ea29b?auto=format&fit=crop&w=600&q=80',
  veg: 'https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80',
  nonveg: 'https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=600&q=80',
};

function getDishImage(item: MenuItem): string {
  if (item.image_url && item.image_url.trim().length > 0) {
    return item.image_url;
  }
  const lower = item.name.toLowerCase();
  for (const [kw, url] of Object.entries(CULINARY_FALLBACKS)) {
    if (lower.includes(kw)) return url;
  }
  return item.dietary_type === 'NON_VEG'
    ? CULINARY_FALLBACKS.nonveg
    : CULINARY_FALLBACKS.veg;
}

const DietaryBadge: React.FC<{ type: string | null }> = ({ type }) => {
  if (!type) return null;
  const isVeg = type === 'VEG';
  const isEgg = type === 'EGG';

  const borderColor = isVeg ? '#315B42' : isEgg ? '#D97706' : '#B91C1C';
  const dotColor = isVeg ? '#315B42' : isEgg ? '#D97706' : '#B91C1C';

  return (
    <div
      title={isVeg ? 'Vegetarian' : isEgg ? 'Contains Egg' : 'Non-Vegetarian'}
      className="w-4 h-4 rounded-sm border flex items-center justify-center shrink-0"
      style={{ borderColor, borderWidth: '1.5px' }}
    >
      <div
        className="w-2 h-2 rounded-full"
        style={{ background: dotColor }}
      />
    </div>
  );
};

const SpiceBadge: React.FC<{ level: string | null }> = ({ level }) => {
  if (!level) return null;
  const count = level === 'MILD' ? 1 : level === 'MEDIUM' ? 2 : 3;
  return (
    <div className="flex items-center gap-0.5 text-[10px]" title={`${level} spice`}>
      {Array.from({ length: count }).map((_, i) => (
        <Flame
          key={i}
          size={11}
          style={{ color: level === 'HOT' ? '#B91C1C' : '#D95D2B' }}
        />
      ))}
    </div>
  );
};

export const MenuItemCard: React.FC<MenuItemCardProps> = ({ item, onSelect }) => {
  const { items: cartItems, updateQuantity } = useCart();

  const availableVariants = item.variants.filter((v) => v.is_available);
  const minPrice = availableVariants.length > 0
    ? Math.min(...availableVariants.map((v) => parseFloat(v.price) || 0))
    : 0;
  const hasMultipleVariants = availableVariants.length > 1;

  // Cart quantity for this item across all variants
  const cartQty = cartItems
    .filter((c) => c.menuItemId === item.id)
    .reduce((sum, c) => sum + c.quantity, 0);

  const singleVariant = !hasMultipleVariants && availableVariants[0];
  const singleCartItem = singleVariant
    ? cartItems.find((c) => c.variantId === singleVariant.id)
    : null;

  const handleAddClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!item.is_available) return;
    onSelect(item);
  };

  const handleDecrement = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (singleCartItem) {
      updateQuantity(singleCartItem.variantId, singleCartItem.quantity - 1);
    } else {
      onSelect(item);
    }
  };

  const handleIncrement = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (singleVariant && singleCartItem) {
      updateQuantity(singleCartItem.variantId, singleCartItem.quantity + 1);
    } else {
      onSelect(item);
    }
  };

  const imageUrl = getDishImage(item);
  const isSpecial = item.name.toLowerCase().includes('biryani') || item.name.toLowerCase().includes('butter chicken') || item.name.toLowerCase().includes('tikka');

  return (
    <div
      onClick={() => item.is_available && onSelect(item)}
      className={`group rounded-3xl p-4 transition-all flex items-start justify-between gap-3.5 relative overflow-hidden ${
        !item.is_available ? 'opacity-50 grayscale pointer-events-none' : 'cursor-pointer'
      }`}
      style={{
        background: 'var(--white)',
        border: '1px solid var(--border)',
        boxShadow: '0 2px 10px rgba(40, 40, 32, 0.04)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.boxShadow = '0 8px 24px rgba(40, 40, 32, 0.08)';
        e.currentTarget.style.borderColor = 'rgba(217, 93, 43, 0.3)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.boxShadow = '0 2px 10px rgba(40, 40, 32, 0.04)';
        e.currentTarget.style.borderColor = 'var(--border)';
      }}
    >
      {/* Left Column: Details */}
      <div className="flex-1 min-w-0 flex flex-col justify-between self-stretch pr-1">
        <div>
          {/* Header Badges */}
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <DietaryBadge type={item.dietary_type} />
            <SpiceBadge level={item.spice_level} />
            {isSpecial && (
              <span
                className="text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1"
                style={{
                  background: 'var(--primary-bg)',
                  color: 'var(--primary)',
                }}
              >
                <Sparkles size={10} />
                <span>Bestseller</span>
              </span>
            )}
            {!item.is_available && (
              <span
                className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                style={{ background: '#FEF2F2', color: '#B91C1C' }}
              >
                Sold Out
              </span>
            )}
          </div>

          {/* Dish Title */}
          <h3
            className="font-bold text-base leading-snug group-hover:text-orange-600 transition-colors"
            style={{ color: 'var(--text-primary)' }}
          >
            {item.name}
          </h3>

          {/* Price */}
          <div className="flex items-baseline gap-1.5 mt-1">
            <span
              className="font-bold text-base font-mono"
              style={{ color: 'var(--text-primary)' }}
            >
              {formatInr(minPrice)}
            </span>
            {hasMultipleVariants && (
              <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
                • Options Available
              </span>
            )}
          </div>

          {/* Description */}
          {item.description && (
            <p
              className="text-xs line-clamp-2 mt-1.5 leading-relaxed"
              style={{ color: 'var(--text-secondary)' }}
            >
              {item.description}
            </p>
          )}
        </div>

        {/* Portion indicators if variants exist */}
        {hasMultipleVariants && (
          <div className="flex items-center gap-1.5 mt-2.5">
            {availableVariants.map((v) => (
              <span
                key={v.id}
                className="text-[10px] font-medium px-2 py-0.5 rounded-md"
                style={{
                  background: 'var(--bg-subtle)',
                  color: 'var(--text-muted)',
                  border: '1px solid var(--border)',
                }}
              >
                {v.variant_name}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Right Column: Dish Photo with Floating ADD button */}
      <div className="relative shrink-0 flex flex-col items-center">
        <div
          className="w-28 h-28 rounded-2xl overflow-hidden relative shadow-sm"
          style={{
            background: 'var(--bg-subtle)',
            border: '1px solid var(--border)',
          }}
        >
          <img
            src={imageUrl}
            alt={item.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.src = CULINARY_FALLBACKS.veg;
            }}
          />
        </div>

        {/* Action Button positioned beneath/overlapping photo */}
        <div className="mt-2" onClick={(e) => e.stopPropagation()}>
          {cartQty > 0 ? (
            <div
              className="flex items-center rounded-xl overflow-hidden shadow-md"
              style={{
                background: 'var(--white)',
                border: '1.5px solid var(--primary)',
              }}
            >
              <button
                onClick={handleDecrement}
                className="w-8 h-8 flex items-center justify-center transition-colors cursor-pointer"
                style={{ color: 'var(--primary)' }}
                title="Decrease"
              >
                <Minus size={14} strokeWidth={2.5} />
              </button>
              <span
                className="w-6 text-center text-xs font-bold font-mono"
                style={{ color: 'var(--primary)' }}
              >
                {cartQty}
              </span>
              <button
                onClick={handleIncrement}
                className="w-8 h-8 flex items-center justify-center transition-colors cursor-pointer"
                style={{ color: 'var(--primary)' }}
                title="Increase"
              >
                <Plus size={14} strokeWidth={2.5} />
              </button>
            </div>
          ) : (
            <button
              onClick={handleAddClick}
              disabled={!item.is_available || availableVariants.length === 0}
              className="px-5 py-1.5 rounded-xl font-bold text-xs uppercase tracking-wider flex items-center gap-1 shadow-md transition-all cursor-pointer transform active:scale-95"
              style={{
                background: 'var(--white)',
                color: 'var(--primary)',
                border: '1.5px solid var(--primary)',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--primary)';
                e.currentTarget.style.color = '#FFFFFF';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--white)';
                e.currentTarget.style.color = 'var(--primary)';
              }}
            >
              <Plus size={13} strokeWidth={3} />
              <span>ADD</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
