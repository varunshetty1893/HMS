import React, { useState } from 'react';
import { useCart } from '../context/CartContext';
import { useSession } from '../context/SessionContext';
import { placeOrder, HmsApiError } from '../api';
import { generateIdempotencyKey } from '../utils/idempotency';
import { formatInr } from '../utils/currency';
import { LimitExceededBanner } from './LimitExceededBanner';
import { X, Plus, Minus, Trash2, ShoppingBag, ArrowRight, Loader2, ShoppingCart } from 'lucide-react';
import type { OrderCreate } from '../types';

interface CartDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onOrderSuccess: () => void;
}

export const CartDrawer: React.FC<CartDrawerProps> = ({ isOpen, onClose, onOrderSuccess }) => {
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
      special_instructions: specialInstructions.trim() || null,
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
              'Unpaid table limit (₹5,000.00) reached. Please ask your waiter to settle.'
          );
        } else {
          setGeneralError(err.message || 'Failed to place order. Please try again.');
        }
      } else {
        setGeneralError('Network error. Please check your connection.');
      }
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end animate-fade-in"
      style={{ background: 'rgba(40,40,32,0.5)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md flex flex-col h-full shadow-2xl animate-slide-in-right"
        style={{ background: 'var(--white)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between px-5 py-4"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          <div className="flex items-center gap-2.5">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'var(--primary-bg)', color: 'var(--primary)' }}
            >
              <ShoppingCart size={18} />
            </div>
            <div>
              <h2 className="font-bold text-base" style={{ color: 'var(--text-primary)' }}>
                Your Cart
              </h2>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {totalItemsCount} {totalItemsCount === 1 ? 'item' : 'items'}
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
            style={{ background: 'var(--bg-subtle)', color: 'var(--text-secondary)' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Error banners */}
        {limitError && (
          <div style={{ borderBottom: '1px solid var(--border)' }} className="px-4 py-3">
            <LimitExceededBanner message={limitError} onDismiss={() => setLimitError(null)} />
          </div>
        )}
        {generalError && (
          <div
            className="flex items-center justify-between gap-2 px-4 py-3 text-xs"
            style={{
              background: '#FEF2F2',
              borderBottom: '1px solid #FCA5A5',
              color: '#B91C1C',
            }}
          >
            <span>{generalError}</span>
            <button onClick={() => setGeneralError(null)}><X size={13} /></button>
          </div>
        )}

        {/* Cart item list */}
        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
          {items.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center gap-3 py-12 text-center">
              <ShoppingBag size={52} strokeWidth={1} style={{ color: 'var(--border)' }} />
              <div>
                <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                  Your cart is empty
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Browse the menu to add delicious items
                </p>
              </div>
            </div>
          ) : (
            items.map((it) => (
              <div
                key={`${it.variantId}-${it.itemNotes ?? ''}`}
                className="flex items-start gap-3 p-3.5 rounded-2xl"
                style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border)' }}
              >
                {/* Emoji placeholder */}
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center text-lg flex-shrink-0"
                  style={{ background: 'var(--white)' }}
                >
                  🍽
                </div>

                <div className="flex-1 min-w-0">
                  <h4 className="font-semibold text-sm leading-snug" style={{ color: 'var(--text-primary)' }}>
                    {it.itemName}
                  </h4>
                  <span className="text-xs font-medium" style={{ color: 'var(--primary)' }}>
                    {it.variantName}
                  </span>
                  {it.itemNotes && (
                    <p className="text-[11px] italic mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      "{it.itemNotes}"
                    </p>
                  )}

                  <div className="flex items-center justify-between mt-2">
                    <span className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                      {formatInr(it.price * it.quantity)}
                    </span>

                    <div className="flex items-center gap-1">
                      {/* Delete */}
                      <button
                        onClick={() => removeItem(it.variantId)}
                        className="w-7 h-7 rounded-lg flex items-center justify-center transition-colors"
                        style={{ background: '#FEF2F2', color: '#B91C1C' }}
                        title="Remove"
                      >
                        <Trash2 size={12} />
                      </button>

                      {/* Qty controls */}
                      <div
                        className="flex items-center gap-0.5 rounded-lg overflow-hidden"
                        style={{ border: '1px solid var(--border)', background: 'var(--white)' }}
                      >
                        <button
                          onClick={() => updateQuantity(it.variantId, it.quantity - 1)}
                          className="w-7 h-7 flex items-center justify-center transition-colors"
                          style={{ color: 'var(--text-secondary)' }}
                        >
                          <Minus size={12} />
                        </button>
                        <span className="w-6 text-center text-xs font-bold" style={{ color: 'var(--text-primary)' }}>
                          {it.quantity}
                        </span>
                        <button
                          onClick={() => updateQuantity(it.variantId, it.quantity + 1)}
                          className="w-7 h-7 flex items-center justify-center transition-colors"
                          style={{ background: 'var(--primary)', color: '#fff' }}
                        >
                          <Plus size={12} />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div
            className="px-5 pb-6 pt-4 space-y-3"
            style={{ borderTop: '1px solid var(--border)', background: 'var(--white)' }}
          >
            {/* Special instructions */}
            <div>
              <label
                className="block text-xs font-semibold uppercase tracking-wide mb-1"
                style={{ color: 'var(--text-muted)' }}
              >
                Order Notes (Optional)
              </label>
              <input
                type="text"
                value={specialInstructions}
                onChange={(e) => setSpecialInstructions(e.target.value)}
                placeholder="e.g. Please bring water first"
                maxLength={200}
                className="w-full rounded-xl px-3 py-2 text-sm focus:outline-none transition"
                style={{
                  background: 'var(--bg-subtle)',
                  border: '1px solid var(--border)',
                  color: 'var(--text-primary)',
                }}
                onFocus={e => e.currentTarget.style.borderColor = 'var(--primary)'}
                onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
              />
            </div>

            {/* Total */}
            <div className="flex items-center justify-between">
              <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Estimated Total
              </span>
              <span className="font-bold text-lg" style={{ color: 'var(--text-primary)' }}>
                {formatInr(totalEstimatedAmount)}
              </span>
            </div>
            <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              Authoritative prices, taxes, and final total are calculated by the server.
            </p>

            {/* Place Order */}
            <button
              type="button"
              disabled={isSubmitting}
              onClick={handleSubmitOrder}
              className="btn-primary w-full"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Sending to Kitchen…</span>
                </>
              ) : (
                <>
                  <span>Place Order</span>
                  <ArrowRight size={16} className="ml-auto" />
                </>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
