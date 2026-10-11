import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { getMenu } from '../api';
import type { CustomerMenuResponse, MenuItem } from '../types';
import { CategoryTabs } from '../components/CategoryTabs';
import { MenuItemCard } from '../components/MenuItemCard';
import { VariantSelectorSheet } from '../components/VariantSelectorSheet';
import { CartDrawer } from '../components/CartDrawer';
import { useCart } from '../context/CartContext';
import { formatInr } from '../utils/currency';
import { Search, ShoppingBag, ArrowRight, RefreshCw, AlertCircle } from 'lucide-react';

interface MenuPageProps {
  onOrderSuccess: () => void;
}

export const MenuPage: React.FC<MenuPageProps> = ({ onOrderSuccess }) => {
  const { totalItemsCount, totalEstimatedAmount } = useCart();

  const [menuData, setMenuData] = useState<CustomerMenuResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [dietaryFilter, setDietaryFilter] = useState<'ALL' | 'VEG' | 'NON_VEG' | 'EGG'>('ALL');

  const [selectedItemForSheet, setSelectedItemForSheet] = useState<MenuItem | null>(null);
  const [isCartDrawerOpen, setIsCartDrawerOpen] = useState<boolean>(false);

  const loadMenu = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getMenu({ available_only: true });
      setMenuData(data);
      setIsLoading(false);
    } catch {
      setError('Could not load dining menu. Please check your connection.');
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadMenu();
  }, [loadMenu]);

  // Filtered categories & items
  const filteredCategories = useMemo(() => {
    if (!menuData) return [];

    const query = searchQuery.trim().toLowerCase();

    return menuData.categories
      .filter((cat) => selectedCategoryId === null || cat.id === selectedCategoryId)
      .map((cat) => {
        const items = cat.items.filter((item) => {
          // Dietary match
          if (dietaryFilter !== 'ALL' && item.dietary_type !== dietaryFilter) {
            return false;
          }
          // Search query match (item name, code, or description)
          if (query) {
            const matchesName = item.name.toLowerCase().includes(query);
            const matchesCode = item.item_code.toLowerCase().includes(query);
            const matchesDesc = item.description?.toLowerCase().includes(query);
            return matchesName || matchesCode || matchesDesc;
          }
          return true;
        });

        return {
          ...cat,
          items,
        };
      })
      .filter((cat) => cat.items.length > 0);
  }, [menuData, selectedCategoryId, dietaryFilter, searchQuery]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 pb-28">
      {/* Search Input Bar */}
      <div className="max-w-md mx-auto px-4 pt-3 pb-1">
        <div className="relative">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search dishes or codes (e.g. Biryani, CB-H)..."
            className="w-full bg-slate-900 border border-slate-800 rounded-2xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-orange-500 transition shadow-inner"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-white"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Categories & Dietary Filters */}
      {menuData && (
        <div className="max-w-md mx-auto">
          <CategoryTabs
            categories={menuData.categories}
            selectedCategoryId={selectedCategoryId}
            onSelectCategory={setSelectedCategoryId}
            dietaryFilter={dietaryFilter}
            onSelectDietaryFilter={setDietaryFilter}
          />
        </div>
      )}

      {/* Main Menu List Area */}
      <div className="max-w-md mx-auto px-4 pt-4 space-y-6">
        {isLoading ? (
          <div className="space-y-4 pt-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="bg-slate-900/50 border border-slate-800/80 rounded-2xl p-4 animate-pulse space-y-3"
              >
                <div className="h-4 bg-slate-800 rounded w-1/3"></div>
                <div className="h-3 bg-slate-800/60 rounded w-2/3"></div>
                <div className="h-8 bg-slate-800/40 rounded"></div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-center space-y-4 my-8">
            <AlertCircle size={32} className="text-rose-400 mx-auto" />
            <p className="text-xs text-slate-300">{error}</p>
            <button
              onClick={loadMenu}
              className="bg-orange-500 hover:bg-orange-600 text-white font-semibold py-2 px-4 rounded-xl text-xs inline-flex items-center space-x-2 transition"
            >
              <RefreshCw size={14} />
              <span>Retry</span>
            </button>
          </div>
        ) : filteredCategories.length === 0 ? (
          <div className="text-center py-16 text-slate-500 space-y-2">
            <p className="text-sm font-medium text-slate-300">No items match your criteria</p>
            <p className="text-xs text-slate-500">Try adjusting your filters or search keywords</p>
          </div>
        ) : (
          filteredCategories.map((category) => (
            <div key={category.id} className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                  {category.name}
                </h2>
                <span className="text-xs text-slate-500 font-mono">
                  {category.items.length} {category.items.length === 1 ? 'item' : 'items'}
                </span>
              </div>

              <div className="grid grid-cols-1 gap-3">
                {category.items.map((item) => (
                  <MenuItemCard
                    key={item.id}
                    item={item}
                    onSelect={(selected) => setSelectedItemForSheet(selected)}
                  />
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Floating View Cart Sticky Button */}
      {totalItemsCount > 0 && (
        <div className="fixed bottom-4 left-0 right-0 z-40 px-4">
          <div className="max-w-md mx-auto">
            <button
              onClick={() => setIsCartDrawerOpen(true)}
              className="w-full bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white font-bold py-3.5 px-5 rounded-2xl flex items-center justify-between shadow-2xl shadow-orange-500/30 transition transform active:scale-[0.99] border border-orange-400/30"
            >
              <div className="flex items-center space-x-2.5">
                <div className="w-7 h-7 rounded-lg bg-white/20 flex items-center justify-center">
                  <ShoppingBag size={16} />
                </div>
                <div className="text-left leading-tight">
                  <span className="text-xs font-semibold block">
                    {totalItemsCount} {totalItemsCount === 1 ? 'item' : 'items'} in cart
                  </span>
                  <span className="text-[11px] font-normal text-orange-100">
                    Est. {formatInr(totalEstimatedAmount)}
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-1.5 text-xs font-bold tracking-wide">
                <span>View Cart</span>
                <ArrowRight size={16} />
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Variant Selector Bottom Sheet */}
      <VariantSelectorSheet
        item={selectedItemForSheet}
        onClose={() => setSelectedItemForSheet(null)}
      />

      {/* Cart Drawer */}
      <CartDrawer
        isOpen={isCartDrawerOpen}
        onClose={() => setIsCartDrawerOpen(false)}
        onOrderSuccess={onOrderSuccess}
      />
    </div>
  );
};
