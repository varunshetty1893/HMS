import React, { useState } from 'react';
import { useCart } from '../context/CartContext';
import { useSession } from '../context/SessionContext';
import { placeOrder, HmsApiError } from '../api';
import { generateIdempotencyKey } from '../utils/idempotency';
import { formatInr } from '../utils/currency';
import { LimitExceededBanner } from './LimitExceededBanner';
import { X, Plus, Minus, Trash2, ShoppingBag, ArrowRight, Loader2 } from 'lucide-react';
import type { OrderCreate } from '../types';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onOrderSuccess: () => void;
}

export const CartDrawer: React.FC<CartDrawerProps> = ({
  isOpen,
  onClose,
  onOrderSuccess,
}) => {
  const { items, updateQuantity, removeItem, clearCart, totalItemsCount, totalEstimatedAmount } =
    useCart();
  const { updateOutstanding, refreshSession } = useSession();

  const [specialInstructions, setSpecialInstructions] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [limitError, setLimitError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmitOrder = async () => {
    if (items.length === 0 || isSubmitting) return;

    setIsSubmitting(true);
    setLimitError(null);
    setGeneralError(null);

    const idempotencyKey = generateIdempotencyKey();

    const orderPayload: OrderCreate = {
      items: items.map((it) => ({
        variant_id: it.variantId,
        quantity: it.quantity,
        item_notes: it.itemNotes || null,
      })),
      special_instructions: specialInstructions.trim() ? specialInstructions.trim() : null,
    };

    try {
      const res = await placeOrder(orderPayload, idempotencyKey);
      if (res.data.table_session) {
        updateOutstanding(res.data.table_session.current_outstanding_amount);
      }
      await refreshSession();
      clearCart();
      setIsSubmitting(false);
      onClose();
      onOrderSuccess();
    } catch (err: unknown) {
      setIsSubmitting(false);
      if (err instanceof HmsApiError) {
        if (err.code === 'TABLE_SPEND_LIMIT_EXCEEDED') {
          setLimitError(
            err.message ||
              'Unpaid table limit (₹5,000.00) reached. Please ask your waiter to settle or verify orders.'
          );
        } else {
          setGeneralError(err.message || 'Failed to place order. Please try again.');
        }
      } else {
        setGeneralError('Network error submitting order. Please check connection.');
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-md bg-slate-900 border-l border-slate-800 text-slate-100 flex flex-col h-full shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="p-2 bg-orange-500/20 text-orange-400 rounded-xl">
              <ShoppingBag size={18} />
            </div>
            <div>
              <h2 className="font-bold text-base text-white">Your Cart</h2>
              <span className="text-xs text-slate-400">
                {totalItemsCount} {totalItemsCount === 1 ? 'item' : 'items'}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full bg-slate-800 text-slate-400 hover:text-white hover:bg-slate-700 transition"
          >
            <X size={18} />
          </button>
        </div>

        {/* Limit Warning if any */}
        {limitError && (
          <div className="p-4 border-b border-slate-800">
            <LimitExceededBanner
              message={limitError}
              onDismiss={() => setLimitError(null)}
            />
          </div>
        )}

        {/* General Error Banner */}
        {generalError && (
          <div className="p-4 bg-rose-950/60 border-b border-rose-800 text-rose-300 text-xs flex justify-between items-center">
            <span>{generalError}</span>
            <button onClick={() => setGeneralError(null)} className="text-rose-400 hover:text-white">✕</button>
          </div>
        )}

        {/* Cart Items List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {items.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 py-12">
              <ShoppingBag size={48} className="stroke-[1.5] mb-3 text-slate-600" />
              <p className="text-sm font-medium text-slate-300">Your cart is empty</p>
              <p className="text-xs text-slate-500 mt-1">Browse the menu to add delicious items</p>
            </div>
          ) : (
            items.map((it) => (
              <div
                key={`${it.variantId}-${it.itemNotes || ''}`}
                className="bg-slate-800/60 border border-slate-700/60 rounded-xl p-3 flex flex-col justify-between"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-semibold text-sm text-slate-100">{it.itemName}</h4>
                    <span className="text-xs text-orange-400">{it.variantName}</span>
                    {it.itemNotes && (
                      <p className="text-[11px] text-slate-400 italic mt-0.5">
                        Note: &ldquo;{it.itemNotes}&rdquo;
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => removeItem(it.variantId)}
                    className="text-slate-500 hover:text-rose-400 transition p-1"
                    title="Remove item"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>

                <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-700/40">
                  <span className="font-semibold text-sm text-slate-200">
                    {formatInr(it.price * it.quantity)}
                  </span>

                  <div className="flex items-center space-x-2 bg-slate-900 rounded-lg p-0.5 border border-slate-700">
                    <button
                      type="button"
                      onClick={() => updateQuantity(it.variantId, it.quantity - 1)}
                      className="w-6 h-6 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 flex items-center justify-center transition"
                    >
                      <Minus size={12} />
                    </button>
                    <span className="w-5 text-center text-xs font-bold text-white">
                      {it.quantity}
                    </span>
                    <button
                      type="button"
                      onClick={() => updateQuantity(it.variantId, it.quantity + 1)}
                      className="w-6 h-6 rounded bg-orange-500 text-white hover:bg-orange-600 flex items-center justify-center transition"
                    >
                      <Plus size={12} />
                    </button>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer / Order submission */}
        {items.length > 0 && (
          <div className="p-4 border-t border-slate-800 bg-slate-900/90 space-y-3">
            {/* Special Instructions for Order */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Order Notes (Optional)
              </label>
              <input
                type="text"
                value={specialInstructions}
                onChange={(e) => setSpecialInstructions(e.target.value)}
                placeholder="e.g. Please bring water first"
                maxLength={200}
                className="w-full bg-slate-800/80 border border-slate-700 rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-orange-500"
              />
            </div>

            {/* Subtotal summary */}
            <div className="flex items-center justify-between text-sm pt-1">
              <span className="text-slate-400">Estimated Total:</span>
              <span className="font-bold text-base text-white">
                {formatInr(totalEstimatedAmount)}
              </span>
            </div>
            <p className="text-[10px] text-slate-500">
              Authoritative prices, taxes, and total are calculated by server.
            </p>

            {/* Place Order CTA */}
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleSubmitOrder}
              className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-slate-700 text-white font-semibold py-3 px-4 rounded-xl flex items-center justify-center space-x-2 shadow-lg shadow-orange-500/20 transition active:scale-[0.99]"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Submitting to Kitchen...</span>
                </>
              ) : (
                <>
                  <span>Send Order to Kitchen</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
