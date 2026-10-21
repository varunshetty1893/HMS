import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import type { CartItem } from '../types';

interface CartContextType {
  items: CartItem[];
  addItem: (item: CartItem) => void;
  updateQuantity: (variantId: string, quantity: number, itemNotes?: string) => void;
  removeItem: (variantId: string, itemNotes?: string) => void;
  /** Replace every cart line of one dish (all its portions) in one go. */
  setItemLines: (menuItemId: string, lines: CartItem[]) => void;
  clearCart: () => void;
  totalItemsCount: number;
  totalEstimatedAmount: number;
}

const CartContext = createContext<CartContextType | null>(null);

const CART_STORAGE_KEY = 'hms_customer_cart';

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [items, setItems] = useState<CartItem[]>(() => {
    try {
      const saved = sessionStorage.getItem(CART_STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      sessionStorage.setItem(CART_STORAGE_KEY, JSON.stringify(items));
    } catch {
      // ignore
    }
  }, [items]);

  const addItem = useCallback((newItem: CartItem) => {
    setItems((prev) => {
      const idx = prev.findIndex(
        (it) => it.variantId === newItem.variantId && (it.itemNotes || '') === (newItem.itemNotes || '')
      );
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = {
          ...next[idx],
          quantity: next[idx].quantity + newItem.quantity,
        };
        return next;
      }
      return [...prev, newItem];
    });
  }, []);

  const updateQuantity = useCallback((variantId: string, quantity: number, itemNotes?: string) => {
    setItems((prev) => {
      if (quantity <= 0) {
        return prev.filter(
          (it) => it.variantId !== variantId || (it.itemNotes || '') !== (itemNotes || '')
        );
      }
      return prev.map((it) =>
        it.variantId === variantId && (it.itemNotes || '') === (itemNotes || '')
          ? { ...it, quantity }
          : it
      );
    });
  }, []);

  const removeItem = useCallback((variantId: string, itemNotes?: string) => {
    setItems((prev) =>
      prev.filter(
        (it) => it.variantId !== variantId || (it.itemNotes || '') !== (itemNotes || '')
      )
    );
  }, []);

  const setItemLines = useCallback((menuItemId: string, lines: CartItem[]) => {
    setItems((prev) => {
      const firstIdx = prev.findIndex((it) => it.menuItemId === menuItemId);
      const rest = prev.filter((it) => it.menuItemId !== menuItemId);
      const cleaned = lines.filter((l) => l.quantity > 0);
      if (firstIdx < 0) return [...rest, ...cleaned];
      // keep the dish at its original position in the cart
      const insertAt = Math.min(firstIdx, rest.length);
      return [...rest.slice(0, insertAt), ...cleaned, ...rest.slice(insertAt)];
    });
  }, []);

  const clearCart = useCallback(() => {
    setItems([]);
    sessionStorage.removeItem(CART_STORAGE_KEY);
  }, []);

  const totalItemsCount = useMemo(() => {
    return items.reduce((sum, it) => sum + it.quantity, 0);
  }, [items]);

  const totalEstimatedAmount = useMemo(() => {
    return items.reduce((sum, it) => sum + it.price * it.quantity, 0);
  }, [items]);

  return (
    <CartContext.Provider
      value={{
        items,
        addItem,
        updateQuantity,
        removeItem,
        setItemLines,
        clearCart,
        totalItemsCount,
        totalEstimatedAmount,
      }}
    >
      {children}
    </CartContext.Provider>
  );
};

export const useCart = (): CartContextType => {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used within CartProvider');
  return ctx;
};
