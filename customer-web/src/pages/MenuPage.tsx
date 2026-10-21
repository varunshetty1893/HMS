import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { getMenu } from '../api';
import type { CustomerMenuResponse, MenuItem, MenuCategory } from '../types';
import { CategoryBrowser, type DietaryFilter, type SpiceFilter, type SortMode } from '../components/CategoryTabs';
import { categoryCoverItem } from '../utils/dishImages';
import { DishImage } from '../components/DishImage';
import { MenuItemCard } from '../components/MenuItemCard';
import { VariantSelectorSheet } from '../components/VariantSelectorSheet';
import { CartDrawer } from '../components/CartDrawer';
import { useCart } from '../context/CartContext';
import { formatInrShort } from '../utils/currency';
import {
  Search, ShoppingCart, ChevronRight, RefreshCw, AlertCircle, X, Star,
} from 'lucide-react';

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
  const [dietaryFilter, setDietaryFilter] = useState<DietaryFilter>('ALL');
  const [spiceFilter, setSpiceFilter] = useState<SpiceFilter>('ANY');
  const [sortMode, setSortMode] = useState<SortMode>('MENU');
  const [showAllPopular, setShowAllPopular] = useState(false);

  const [selectedItemForSheet, setSelectedItemForSheet] = useState<MenuItem | null>(null);
  const [isCartDrawerOpen, setIsCartDrawerOpen] = useState<boolean>(false);

  const contentTopRef = useRef<HTMLDivElement>(null);

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

  const aliases: Record<string, string[]> = {
    biryani: ['biriyani'], biriyani: ['biryani'], pulao: ['pulav'], pulav: ['pulao'],
  };

  const matchesFilters = useCallback((item: MenuItem, catName: string): boolean => {
    if (dietaryFilter !== 'ALL' && item.dietary_type !== dietaryFilter) return false;
    if (spiceFilter !== 'ANY' && item.spice_level !== spiceFilter) return false;
    const q = searchQuery.toLowerCase().trim();
    if (!q) return true;
    const queries = [q, ...(aliases[q] ?? [])];
    const includesQuery = (text: string | null | undefined) =>
      !!text && queries.some((term) => text.toLowerCase().includes(term));
    return (
      includesQuery(item.name) || includesQuery(item.description) || includesQuery(item.item_code) ||
      includesQuery(catName) || item.variants.some((v) => includesQuery(v.variant_name))
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dietaryFilter, spiceFilter, searchQuery]);

  // Selecting a category shows that category; bring its first dish into view
  // just below the sticky header (offset comes from the measured --header-h).
  const handleSelectCategory = useCallback((id: string | null) => {
    setSelectedCategoryId(id);
    requestAnimationFrame(() => {
      contentTopRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }, []);

  const resetAll = useCallback(() => {
    setSearchQuery(''); setDietaryFilter('ALL'); setSelectedCategoryId(null); setSpiceFilter('ANY'); setSortMode('MENU');
  }, []);

  // Filtered menu logic
  const minPriceOf = (item: MenuItem): number => {
    const prices = item.variants
      .filter((v) => v.is_available && v.price !== null)
      .map((v) => parseFloat(v.price!) || 0)
      .filter((p) => p > 0);
    return prices.length ? Math.min(...prices) : Number.POSITIVE_INFINITY;
  };

  const filteredCategories = useMemo<MenuCategory[]>(() => {
    if (!menuData) return [];
    return menuData.categories
      .map((cat) => {
        const items = cat.items.filter((item) => matchesFilters(item, cat.name));
        if (sortMode === 'MENU') return { ...cat, items };
        const sign = sortMode === 'PRICE_ASC' ? 1 : -1;
        return { ...cat, items: [...items].sort((x, y) => {
          const px = minPriceOf(x), py = minPriceOf(y);
          if (px === py) return 0;
          if (!isFinite(px)) return 1; // seasonal / unpriced always last
          if (!isFinite(py)) return -1;
          return (px - py) * sign;
        }) };
      })
      .filter((cat) => (selectedCategoryId ? cat.id === selectedCategoryId : cat.items.length > 0));
  }, [menuData, selectedCategoryId, matchesFilters, sortMode]);

  // Popular dishes = most ordered (server-ranked, max 6). Hidden until orders exist.
  const popularIds = useMemo<Set<string>>(
    () => new Set(menuData?.popular_item_ids ?? []),
    [menuData]
  );

  // Curated picks shown only until real order history exists (then the heading says so).
  const FALLBACK_POPULAR_CODES = ['BD-TEA', 'CB', 'BF-IDL', 'BF-MD', 'NC-BC', 'BR-BN'];
  const hasOrderRanking = (menuData?.popular_item_ids?.length ?? 0) > 0;

  const featuredItems = useMemo<MenuItem[]>(() => {
    if (!menuData || searchQuery || dietaryFilter !== 'ALL' || spiceFilter !== 'ANY') return [];
    const byId = new Map<string, MenuItem>();
    const byCode = new Map<string, MenuItem>();
    menuData.categories.forEach((c) => c.items.forEach((i) => { byId.set(i.id, i); byCode.set(i.item_code.toUpperCase(), i); }));
    const ranked = (menuData.popular_item_ids ?? []).map((id) => byId.get(id));
    const picks = ranked.length > 0 ? ranked : FALLBACK_POPULAR_CODES.map((code) => byCode.get(code));
    return picks.filter((i): i is MenuItem => !!i && i.is_available).slice(0, 6);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [menuData, searchQuery, dietaryFilter, spiceFilter]);

  const skeletonCards = [1, 2, 3, 4, 5, 6];

  return (
    <div className={`min-h-screen ${totalItemsCount > 0 ? 'pb-28' : 'pb-6'}`} style={{ background: 'var(--cream, #FFF8ED)' }}>
      {/* ── Search + categories + dietary filters (normal flow, NOT sticky) ── */}
      <div className="px-3 pt-3 pb-3">
        <div className="max-w-5xl mx-auto space-y-3">
          <div className="relative">
            <Search size={18} className="absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
            <input
              type="search"
              id="menu-search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for biryani, idli, tea, starters…"
              aria-label="Search menu"
              className="w-full pl-10 pr-10 py-3 rounded-2xl text-sm focus:outline-none transition"
              style={{ background: 'var(--white)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
              onFocus={e => e.currentTarget.style.borderColor = 'var(--primary)'}
              onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                aria-label="Clear search"
                className="absolute right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full flex items-center justify-center cursor-pointer"
                style={{ background: 'var(--border)', color: 'var(--text-secondary)' }}
              >
                <X size={12} />
              </button>
            )}
          </div>

          {menuData && (
            <CategoryBrowser
              categories={visibleCategories}
              selectedCategoryId={selectedCategoryId}
              onSelectCategory={handleSelectCategory}
              dietaryFilter={dietaryFilter}
              onSelectDietaryFilter={setDietaryFilter}
              spiceFilter={spiceFilter}
              onSelectSpiceFilter={setSpiceFilter}
              sortMode={sortMode}
              onSelectSortMode={setSortMode}
              onReset={resetAll}
              canReset={!!searchQuery || !!selectedCategoryId || dietaryFilter !== 'ALL' || spiceFilter !== 'ANY' || sortMode !== 'MENU'}
            />
          )}
        </div>
      </div>

      {/* ── Main content ── */}
      <div className="max-w-5xl mx-auto px-3 space-y-6">
        <div ref={contentTopRef} style={{ scrollMarginTop: 'calc(var(--header-h, 0px) + 8px)' }} />
        {/* Loading skeletons */}
        {isLoading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
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

        {/* Most Ordered */}
        {!isLoading && !error && featuredItems.length > 0 && !searchQuery && !selectedCategoryId && (
          <section className="rounded-3xl p-3" style={{ background: 'var(--primary-bg)' }}>
            <div className="flex items-center justify-between mb-2.5 px-1">
              <div className="flex items-center gap-2">
                <Star size={22} style={{ color: 'var(--primary)' }} fill="var(--primary)" />
                <h2 className="text-xl font-extrabold" style={{ color: 'var(--text-primary)' }}>
                  {hasOrderRanking ? 'Most Ordered' : 'Popular Picks'}
                </h2>
              </div>
              <button
                type="button"
                onClick={() => setShowAllPopular((v) => !v)}
                className="flex items-center gap-0.5 text-sm font-semibold cursor-pointer"
                style={{ color: 'var(--primary)' }}
              >
                {showAllPopular ? 'Show less' : 'See All'}
                <ChevronRight size={16} className={showAllPopular ? 'rotate-90' : ''} />
              </button>
            </div>
            <div
              className={showAllPopular
                ? 'grid grid-cols-2 gap-2.5'
                : 'flex gap-2.5 overflow-x-auto no-scrollbar snap-x pb-1 -mx-1 px-1'}
            >
              {featuredItems.map((item) => (
                <MenuItemCard
                  key={item.id}
                  item={item}
                  compact
                  isPopular
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
              onClick={resetAll}
              className="mt-3 px-5 py-2.5 rounded-xl font-bold text-xs uppercase cursor-pointer"
              style={{
                background: 'var(--primary)',
                color: '#fff',
              }}
            >
              Reset filters
            </button>
          </div>
        )}

        {/* Category sections */}
        {!isLoading && !error && filteredCategories.map((category) => (
          <section key={category.id} style={{ scrollMarginTop: 'calc(var(--header-h, 0px) + 8px)' }}>
            {/* Category header */}
            <div className="flex items-center justify-between mb-2.5 px-1">
              <div className="flex items-center gap-2.5 min-w-0">
                {(() => {
                  const cover = categoryCoverItem(category);
                  return cover ? (
                    <div className="w-9 h-9 rounded-lg overflow-hidden shrink-0" style={{ background: 'var(--bg-subtle)' }}>
                      <DishImage item={cover} className="w-full h-full" iconSize={16} />
                    </div>
                  ) : null;
                })()}
                <h2 className="text-lg font-extrabold leading-tight" style={{ color: 'var(--text-primary)' }}>
                  {category.name}
                </h2>
              </div>
              <span className="flex items-center gap-0.5 text-sm shrink-0" style={{ color: 'var(--text-secondary)' }}>
                {category.items.length} {category.items.length === 1 ? 'item' : 'items'}
                <ChevronRight size={16} />
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
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

      </div>

      {/* ── Persistent bottom cart bar ── */}
      {totalItemsCount > 0 && (
        <div className="fixed bottom-0 left-0 right-0 z-40 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pointer-events-none">
          <div className="max-w-xl mx-auto pointer-events-auto">
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
                <div className="relative w-9 h-9 flex items-center justify-center">
                  <ShoppingCart size={26} />
                  <span
                    className="absolute -top-1 -right-1.5 min-w-[20px] h-5 px-1 rounded-full text-[11px] font-bold flex items-center justify-center"
                    style={{ background: '#fff', color: 'var(--primary)' }}
                  >
                    {totalItemsCount}
                  </span>
                </div>
                <div className="w-px h-9 bg-white/40" />
                <div className="text-left leading-tight">
                  <span className="block text-base font-bold">View Cart</span>
                  <span className="text-sm opacity-95">
                    {totalItemsCount} {totalItemsCount === 1 ? 'item' : 'items'} • {formatInrShort(totalEstimatedAmount)}
                  </span>
                </div>
              </div>
              <ChevronRight size={20} />
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

    </div>
  );
};
