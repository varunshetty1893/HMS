import React, { useState } from 'react';
import type { MenuItem, MenuPriceVariant } from '../types';
import { formatInr } from '../utils/currency';
import { useCart } from '../context/CartContext';
import { X, Plus, Minus, Check } from 'lucide-react';

interface VariantSelectorSheetProps {
  item: MenuItem | null;
  onClose: () => void;
}

export const VariantSelectorSheet: React.FC<VariantSelectorSheetProps> = ({
  item,
  onClose,
}) => {
  const { addItem } = useCart();

  if (!item) return null;

  const availableVariants = item.variants.filter((v) => v.is_available);
  const defaultVariant =
    availableVariants.find((v) => v.is_default) || availableVariants[0] || item.variants[0];

  const [selectedVariant, setSelectedVariant] = useState<MenuPriceVariant>(defaultVariant);
  const [quantity, setQuantity] = useState<number>(1);
  const [itemNotes, setItemNotes] = useState<string>('');

  const variantPrice = parseFloat(selectedVariant?.price || '0') || 0;
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
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-t-3xl sm:rounded-3xl p-5 shadow-2xl text-slate-100 flex flex-col max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between pb-3 border-b border-slate-800">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              {item.dietary_type === 'VEG' && (
                <span className="flex items-center justify-center w-3.5 h-3.5 border border-emerald-500 rounded-sm p-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                </span>
              )}
              {item.dietary_type === 'NON_VEG' && (
                <span className="flex items-center justify-center w-3.5 h-3.5 border border-rose-500 rounded-sm p-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                </span>
              )}
              {item.dietary_type === 'EGG' && (
                <span className="flex items-center justify-center w-3.5 h-3.5 border border-amber-500 rounded-sm p-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
                </span>
              )}
              <span className="text-xs font-mono text-slate-400">{item.item_code}</span>
            </div>
            <h2 className="text-lg font-bold text-white">{item.name}</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content scroll area */}
        <div className="overflow-y-auto py-4 space-y-5 flex-1 pr-1">
          {item.description && (
            <p className="text-xs text-slate-400 leading-relaxed">{item.description}</p>
          )}

          {/* Variants Selection */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2.5">
              Select Portion / Variant
            </label>
            <div className="space-y-2">
              {availableVariants.map((variant) => {
                const isSelected = selectedVariant?.id === variant.id;
                return (
                  <button
                    key={variant.id}
                    type="button"
                    onClick={() => setSelectedVariant(variant)}
                    className={`w-full flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                      isSelected
                        ? 'bg-orange-500/10 border-orange-500 text-white'
                        : 'bg-slate-800/50 border-slate-700/70 text-slate-300 hover:border-slate-600'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <div
                        className={`w-4 h-4 rounded-full border flex items-center justify-center ${
                          isSelected
                            ? 'border-orange-500 bg-orange-500 text-white'
                            : 'border-slate-600 bg-transparent'
                        }`}
                      >
                        {isSelected && <Check size={10} strokeWidth={3} />}
                      </div>
                      <div>
                        <span className="text-sm font-medium">{variant.variant_name}</span>
                        {variant.quantity_value && (
                          <span className="text-xs text-slate-400 ml-2">
                            ({variant.quantity_value} {variant.unit})
                          </span>
                        )}
                      </div>
                    </div>
                    <span className="font-semibold text-sm text-slate-100">
                      {formatInr(variant.price)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Quantity Selector */}
          <div className="flex items-center justify-between pt-1">
            <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
              Quantity
            </span>
            <div className="flex items-center space-x-3 bg-slate-800 rounded-xl p-1 border border-slate-700">
              <button
                type="button"
                onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                className="w-8 h-8 rounded-lg bg-slate-700 text-slate-200 flex items-center justify-center hover:bg-slate-600 transition"
              >
                <Minus size={14} />
              </button>
              <span className="w-6 text-center font-bold text-sm text-white">{quantity}</span>
              <button
                type="button"
                onClick={() => setQuantity((q) => Math.min(20, q + 1))}
                className="w-8 h-8 rounded-lg bg-orange-500 text-white flex items-center justify-center hover:bg-orange-600 transition"
              >
                <Plus size={14} />
              </button>
            </div>
          </div>

          {/* Item Special Notes */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
              Item Instructions (Optional)
            </label>
            <input
              type="text"
              value={itemNotes}
              onChange={(e) => setItemNotes(e.target.value)}
              placeholder="e.g. Less spicy, no onions, extra crispy"
              maxLength={100}
              className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 transition"
            />
          </div>
        </div>

        {/* Footer Add Button */}
        <div className="pt-3 border-t border-slate-800">
          <button
            type="button"
            onClick={handleAddToCart}
            className="w-full bg-orange-500 hover:bg-orange-600 text-white font-semibold py-3 px-4 rounded-xl flex items-center justify-between shadow-lg shadow-orange-500/25 transition active:scale-[0.99]"
          >
            <span>Add to Cart</span>
            <span>{formatInr(totalPrice)}</span>
          </button>
        </div>
      </div>
    </div>
  );
};
