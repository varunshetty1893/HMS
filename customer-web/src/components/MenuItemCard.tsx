import React from 'react';
import type { MenuItem } from '../types';
import { formatInr } from '../utils/currency';
import { Plus, Flame } from 'lucide-react';

interface MenuItemCardProps {
  item: MenuItem;
  onSelect: (item: MenuItem) => void;
}

export const MenuItemCard: React.FC<MenuItemCardProps> = ({ item, onSelect }) => {
  // Sort variants by price ascending to find starting price
  const availableVariants = item.variants.filter((v) => v.is_available);
  const minPrice = availableVariants.length > 0
    ? Math.min(...availableVariants.map((v) => parseFloat(v.price) || 0))
    : 0;

  const hasMultipleVariants = availableVariants.length > 1;

  return (
    <div
      onClick={() => item.is_available && onSelect(item)}
      className={`group relative bg-slate-800/70 hover:bg-slate-800 border border-slate-700/60 hover:border-slate-600 rounded-2xl p-4 transition-all duration-200 cursor-pointer shadow-sm flex flex-col justify-between ${
        !item.is_available ? 'opacity-50 grayscale pointer-events-none' : ''
      }`}
    >
      <div>
        {/* Header row: dietary badge & spice */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            {/* Dietary Badge */}
            {item.dietary_type === 'VEG' && (
              <span className="flex items-center justify-center w-4 h-4 border border-emerald-500 rounded-sm p-0.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              </span>
            )}
            {item.dietary_type === 'NON_VEG' && (
              <span className="flex items-center justify-center w-4 h-4 border border-rose-500 rounded-sm p-0.5">
                <span className="w-2 h-2 rounded-full bg-rose-500"></span>
              </span>
            )}
            {item.dietary_type === 'EGG' && (
              <span className="flex items-center justify-center w-4 h-4 border border-amber-500 rounded-sm p-0.5">
                <span className="w-2 h-2 rounded-full bg-amber-400"></span>
              </span>
            )}

            {/* Item code */}
            <span className="text-[11px] font-mono font-medium text-slate-400">
              {item.item_code}
            </span>
          </div>

          {/* Spice Level */}
          {item.spice_level && (
            <div className="flex items-center space-x-0.5 text-xs">
              {item.spice_level === 'MILD' && <Flame size={12} className="text-amber-400" />}
              {item.spice_level === 'MEDIUM' && (
                <>
                  <Flame size={12} className="text-orange-400" />
                  <Flame size={12} className="text-orange-400" />
                </>
              )}
              {item.spice_level === 'HOT' && (
                <>
                  <Flame size={12} className="text-rose-500" />
                  <Flame size={12} className="text-rose-500" />
                  <Flame size={12} className="text-rose-500" />
                </>
              )}
            </div>
          )}
        </div>

        {/* Item Name */}
        <h3 className="font-semibold text-slate-100 text-sm md:text-base leading-snug group-hover:text-orange-400 transition-colors">
          {item.name}
        </h3>

        {/* Description */}
        {item.description && (
          <p className="text-xs text-slate-400 line-clamp-2 mt-1 leading-relaxed">
            {item.description}
          </p>
        )}
      </div>

      {/* Footer row: Price & Add Button */}
      <div className="mt-3 pt-3 border-t border-slate-700/50 flex items-center justify-between">
        <div>
          <span className="text-xs text-slate-400 block leading-tight">
            {hasMultipleVariants ? 'From' : 'Price'}
          </span>
          <span className="font-bold text-slate-100 text-sm">
            {formatInr(minPrice)}
          </span>
        </div>

        <button
          type="button"
          disabled={!item.is_available || availableVariants.length === 0}
          className="flex items-center space-x-1 bg-orange-600/20 hover:bg-orange-500 text-orange-400 hover:text-white border border-orange-500/40 hover:border-orange-500 px-3 py-1.5 rounded-xl text-xs font-semibold tracking-wide transition-all duration-150 shadow-sm"
        >
          <Plus size={14} />
          <span>{hasMultipleVariants ? 'Options' : 'Add'}</span>
        </button>
      </div>
    </div>
  );
};
