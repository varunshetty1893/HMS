import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { getMenu } from '../api';
import type { CustomerMenuResponse, MenuItem, MenuCategory } from '../types';
import { CategoryTabs } from '../components/CategoryTabs';
import { MenuItemCard } from '../components/MenuItemCard';
import { VariantSelectorSheet } from '../components/VariantSelectorSheet';
import { CartDrawer } from '../components/CartDrawer';
import { CallWaiterSheet } from '../components/CallWaiterSheet';
import { useCart } from '../context/CartContext';
import { useSession } from '../context/SessionContext';
import { formatInr } from '../utils/currency';
import {
  Search, ShoppingBag, ArrowRight, RefreshCw, AlertCircle, X, Star, Hand,
} from 'lucide-react';

interface MenuPageProps {
  onOrderSuccess: () => void;
}

export const MenuPage: React.FC<MenuPageProps> = ({ onOrderSuccess }) => {
  const { totalItemsCount, totalEstimatedAmount } = useCart();
  const { tableDisplayName } = useSession();

  const [menuData, setMenuData] = useState<CustomerMenuResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [dietaryFilter, setDietaryFilter] = useState<'ALL' | 'VEG' | 'NON_VEG' | 'EGG'>('ALL');

  const [selectedItemForSheet, setSelectedItemForSheet] = useState<MenuItem | null>(null);
  const [isCartDrawerOpen, setIsCartDrawerOpen] = useState<boolean>(false);
  const [isCallWaiterOpen, setIsCallWaiterOpen] = useState<boolean>(false);

  // Refs to each category section for jump-to
  const categoryRefs = useRef<Map<string, HTMLElement>>(new Map());

  const loadMenu = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getMenu({ available_only: false });
      setMenuData(data);
    } catch {
      setError('Could not load the menu. Please check your connection.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => { loadMenu(); }, [loadMenu]);

  const visibleCategories = useMemo(
    () => menuData?.categories.filter((category) => category.items.length > 0) ?? [],
    [menuData]
  );

  // Jump to category section when tab selected (only when no search active)
  const handleSelectCategory = useCallback((id: string | null) => {
    setSelectedCategoryId(id);
    if (!id || searchQuery) return;
    setTimeout(() => {
      const el = categoryRefs.current.get(id);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 50);
  }, [searchQuery]);

  // Filtered menu logic
  const filteredCategories = useMemo<MenuCategory[]>(() => {
    if (!menuData) return [];
    return menuData.categories
      .map((cat) => {
        const filteredItems = cat.items.filter((item) => {
          // Dietary filter
          if (dietaryFilter !== 'ALL' && item.dietary_type !== dietaryFilter) {
            return false;
          }
          // Search query filter
          if (searchQuery.trim()) {
            const q = searchQuery.toLowerCase().trim();
            const aliases: Record<string, string[]> = {
              biryani: ['biriyani'], biriyani: ['biryani'], pulao: ['pulav'], pulav: ['pulao'],
            };
            const queries = [q, ...(aliases[q] ?? [])];
            const includesQuery = (text: string | null | undefined) =>
              !!text && queries.some((term) => text.toLowerCase().includes(term));
            const nameMatch = includesQuery(item.name);
            const descMatch = includesQuery(item.description);
            const codeMatch = includesQuery(item.item_code);
            const categoryMatch = includesQuery(cat.name);
            const variantMatch = item.variants.some((v) =>
              includesQuery(v.variant_name)
            );
            return nameMatch || descMatch || codeMatch || categoryMatch || variantMatch;
          }
          return true;
        });
        return { ...cat, items: filteredItems };
      })
      .filter((cat) => {
        if (selectedCategoryId && !searchQuery) {
          return cat.id === selectedCategoryId;
        }
        return cat.items.length > 0;
      });
  }, [menuData, searchQuery, selectedCategoryId, dietaryFilter]);

  // Popular dishes = most ordered (server-ranked, max 6). Hidden until orders exist.
  const popularIds = useMemo<Set<string>>(
    () => new Set(menuData?.popular_item_ids ?? []),
    [menuData]
  );

  const featuredItems = useMemo<MenuItem[]>(() => {
    if (!menuData || searchQuery) return [];
    const ids = menuData.popular_item_ids ?? [];
    const byId = new Map<string, MenuItem>();
    menuData.categories.forEach((c) => c.items.forEach((i) => byId.set(i.id, i)));
    return ids
      .map((id) => byId.get(id))
      .filter((i): i is MenuItem => !!i && i.is_available)
      .slice(0, 6);
  }, [menuData, searchQuery]);

  const skeletonCards = [1, 2, 3, 4, 5, 6];

  return (
    <div className="min-h-screen pb-32" style={{ background: 'var(--cream, #FFF8ED)' }}>
      {/* ── Hero greeting + Search bar ── */}
      <div
        className="px-4 pt-4 pb-3"
        style={{ background: 'var(--white)', borderBottom: '1px solid var(--border)' }}
      >
        <div className="max-w-5xl mx-auto space-y-3">
          {/* Greeting + Waiter Quick Action */}
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                {tableDisplayName ? `${tableDisplayName} • Welcome to` : 'Welcome to'}
              </p>
              <h2 className="text-lg md:text-xl font-bold leading-tight flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                <span>SpiceHub Family Restaurant</span>
                <span className="text-base">🌶</span>
              </h2>
            </div>

            {/* Quick Call Waiter button directly in header banner */}
            <button
              onClick={() => setIsCallWaiterOpen(true)}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all shadow-sm cursor-pointer hover:scale-105 active:scale-95"
              style={{
                background: 'var(--primary-bg)',
                color: 'var(--primary)',
                border: '1.5px solid rgba(217, 93, 43, 0.3)',
              }}
              title="Call waiter to table"
            >
              <Hand size={14} />
              <span>Call Waiter</span>
            </button>
          </div>

          {/* Search */}
          <div className="relative">
            <Search
              size={16}
              className="absolute left-3.5 top-1/2 -translate-y-1/2"
              style={{ color: 'var(--text-muted)' }}
            />
            <input
              type="search"
              id="menu-search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by dish name, biryani, starters, kebab…"
              className="w-full pl-10 pr-10 py-2.5 rounded-2xl text-sm focus:outline-none transition"
              style={{
                background: 'var(--bg-subtle)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
              }}
              onFocus={e => e.currentTarget.style.borderColor = 'var(--primary)'}
              onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 rounded-full flex items-center justify-center cursor-pointer"
                style={{ background: 'var(--border)', color: 'var(--text-secondary)' }}
              >
                <X size={11} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── Category tabs (sticky) ── */}
      {menuData && (
        <CategoryTabs
          categories={visibleCategories}
          selectedCategoryId={selectedCategoryId}
          onSelectCategory={handleSelectCategory}
          dietaryFilter={dietaryFilter}
          onSelectDietaryFilter={setDietaryFilter}
        />
      )}

      {/* ── Main content ── */}
      <div className="max-w-5xl mx-auto px-4 pt-5 space-y-8">
        {/* Loading skeletons */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {skeletonCards.map((i) => (
              <div key={i} className="rounded-3xl p-4 flex items-start gap-3 bg-white border border-stone-200">
                <div className="skeleton w-28 h-28 rounded-2xl flex-shrink-0" />
                <div className="flex-1 space-y-2 pt-1">
                  <div className="skeleton h-4 w-2/3 rounded" />
                  <div className="skeleton h-3 w-1/2 rounded" />
                  <div className="skeleton h-3 w-4/5 rounded mt-2" />
                  <div className="skeleton h-4 w-1/3 rounded mt-3" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error state */}
        {!isLoading && error && (
          <div
            className="rounded-3xl p-8 text-center space-y-4 max-w-md mx-auto shadow-sm"
            style={{ background: 'var(--white)', border: '1px solid var(--border)' }}
          >
            <AlertCircle size={36} style={{ color: '#B91C1C', margin: '0 auto' }} />
            <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>{error}</p>
            <button onClick={loadMenu} className="btn-primary">
              <RefreshCw size={14} />
              <span>Retry Menu</span>
            </button>
          </div>
        )}

        {/* Featured / Popular section */}
        {!isLoading && !error && featuredItems.length > 0 && !searchQuery && !selectedCategoryId && (
          <section>
            <div className="flex items-center gap-2 mb-3 px-1">
              <Star size={16} style={{ color: 'var(--primary)' }} fill="var(--primary)" />
              <h2 className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                Most Ordered
              </h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {featuredItems.map((item) => (
                <MenuItemCard
                  key={item.id}
                  item={item}
                  isPopular={popularIds.has(item.id)}
                  onSelect={setSelectedItemForSheet}
                />
              ))}
            </div>
          </section>
        )}

        {/* Empty search result */}
        {!isLoading && !error && filteredCategories.length === 0 && !isLoading && (
          <div className="text-center py-16 space-y-3">
            <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
              No dishes found
            </p>
            <p className="text-sm max-w-sm mx-auto" style={{ color: 'var(--text-muted)' }}>
              Try searching for &apos;Biryani&apos;, &apos;Tikka&apos;, &apos;Naan&apos; or reset your filters.
            </p>
            <button
              onClick={() => { setSearchQuery(''); setDietaryFilter('ALL'); }}
              className="mt-3 px-5 py-2.5 rounded-xl font-bold text-xs uppercase cursor-pointer"
              style={{
                background: 'var(--primary)',
                color: '#fff',
              }}
            >
              Clear Filters
            </button>
          </div>
        )}

        {/* Category sections */}
        {!isLoading && !error && filteredCategories.map((category) => (
          <section
            key={category.id}
            ref={(el) => { if (el) categoryRefs.current.set(category.id, el); }}
          >
            {/* Category header */}
            <div
              className="flex items-center justify-between mb-3 pb-2 px-1"
              style={{ borderBottom: '1.5px solid var(--border)' }}
            >
              <h2 className="text-base font-bold tracking-wide" style={{ color: 'var(--text-primary)' }}>
                {category.name}
              </h2>
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: 'var(--bg-subtle)', color: 'var(--text-muted)' }}>
                {category.items.length} {category.items.length === 1 ? 'item' : 'items'}
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {category.items.map((item) => (
                <MenuItemCard
                  key={item.id}
                  item={item}
                  isPopular={popularIds.has(item.id)}
                  onSelect={setSelectedItemForSheet}
                />
              ))}
            </div>
          </section>
        ))}

        {/* Bottom padding for cart bar */}
        <div className="h-6" />
      </div>

      {/* ── Persistent bottom cart bar ── */}
      {totalItemsCount > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 px-4 pb-4 pointer-events-none">
          <div className="max-w-lg mx-auto pointer-events-auto">
            <button
              id="view-cart-btn"
              onClick={() => setIsCartDrawerOpen(true)}
              className="w-full flex items-center justify-between px-5 py-3.5 rounded-2xl font-bold text-sm shadow-xl transition-all animate-slide-up cursor-pointer hover:opacity-95"
              style={{
                background: 'var(--primary)',
                color: '#fff',
                boxShadow: '0 8px 24px rgba(217, 93, 43, 0.35)',
              }}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-8 h-8 rounded-xl flex items-center justify-center font-mono font-bold"
                  style={{ background: 'rgba(255,255,255,0.25)' }}
                >
                  <ShoppingBag size={16} />
                </div>
                <div className="text-left leading-tight">
                  <span className="block text-xs font-bold">
                    {totalItemsCount} {totalItemsCount === 1 ? 'item' : 'items'} added
                  </span>
                  <span className="text-xs opacity-90 font-mono">
                    {formatInr(totalEstimatedAmount)} (Total)
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider">
                <span>View Order</span>
                <ArrowRight size={16} />
              </div>
            </button>
          </div>
        </div>
      )}

      {/* ── Variant selector bottom sheet ── */}
      <VariantSelectorSheet
        item={selectedItemForSheet}
        onClose={() => setSelectedItemForSheet(null)}
      />

      {/* ── Cart drawer ── */}
      <CartDrawer
        isOpen={isCartDrawerOpen}
        onClose={() => setIsCartDrawerOpen(false)}
        onOrderSuccess={onOrderSuccess}
      />

      {/* ── Call Waiter bottom sheet (accessible directly anytime) ── */}
      <CallWaiterSheet
        isOpen={isCallWaiterOpen}
        onClose={() => setIsCallWaiterOpen(false)}
      />
    </div>
  );
};
