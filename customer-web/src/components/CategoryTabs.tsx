import React, { useEffect, useRef, useState } from 'react';
import type { MenuCategory } from '../types';
import { Leaf, Drumstick, Egg, SlidersHorizontal, ChevronDown, LayoutGrid, ChevronUp } from 'lucide-react';
import { DishImage } from './DishImage';
import { categoryCoverItem } from '../utils/dishImages';

export type DietaryFilter = 'ALL' | 'VEG' | 'NON_VEG' | 'EGG';
export type SpiceFilter = 'ANY' | 'MILD' | 'MEDIUM' | 'HOT';
export type SortMode = 'MENU' | 'PRICE_ASC' | 'PRICE_DESC';

interface CategoryBrowserProps {
  categories: MenuCategory[];
  selectedCategoryId: string | null;
  onSelectCategory: (id: string | null) => void;
  dietaryFilter: DietaryFilter;
  onSelectDietaryFilter: (f: DietaryFilter) => void;
  spiceFilter: SpiceFilter;
  onSelectSpiceFilter: (f: SpiceFilter) => void;
  sortMode: SortMode;
  onSelectSortMode: (m: SortMode) => void;
  onReset: () => void;
  canReset: boolean;
}

// Display-only shortening of the real category name. Never merges categories.
export function shortCategoryName(name: string): string {
  const [head, tail] = name.split(' — ');
  const short = !tail
    ? name.trim()
    : ['Dinner', 'Lunch', 'Beverages'].includes(head.trim()) ? tail.trim() : `${head.trim()} ${tail.trim()}`;
  return short.replace('Milkshakes', 'Shakes');
}

const FIRST_ROW = 6;
const SECOND_ROW_COLLAPSED = 4; // + the "All Categories" tile = 5 cells, like the design

const CategoryTile: React.FC<{ category: MenuCategory; selected: boolean; onClick: () => void }> = ({
  category, selected, onClick,
}) => {
  const cover = categoryCoverItem(category);
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className="flex flex-col items-stretch rounded-2xl overflow-hidden transition active:scale-95 cursor-pointer"
      style={
        selected
          ? { background: 'var(--primary)', border: '1px solid var(--primary)', boxShadow: '0 4px 12px rgba(217,93,43,.3)' }
          : { background: 'var(--white)', border: '1px solid var(--border)' }
      }
    >
      <div className="p-1 pb-0">
        <div className="aspect-[4/3] w-full rounded-xl overflow-hidden" style={{ background: 'var(--bg-subtle)' }}>
          {cover ? <DishImage item={cover} className="w-full h-full" iconSize={20} /> : null}
        </div>
      </div>
      <span
        className="px-0.5 py-1.5 text-[10.5px] font-semibold leading-tight text-center line-clamp-3 min-h-[2.4em] flex items-center justify-center"
        style={{ color: selected ? '#fff' : 'var(--text-primary)' }}
      >
        {shortCategoryName(category.name)}
      </span>
    </button>
  );
};

const ToggleTile: React.FC<{ expanded: boolean; onClick: () => void }> = ({ expanded, onClick }) => (
  <button
    type="button"
    onClick={onClick}
    aria-expanded={expanded}
    className="flex flex-col items-center justify-center gap-1 rounded-2xl px-1 py-2 text-[11px] font-semibold text-center leading-tight cursor-pointer transition active:scale-95"
    style={{ background: 'var(--white)', border: '1px solid var(--border)', color: 'var(--text-primary)', minHeight: 78 }}
  >
    {expanded ? <ChevronUp size={22} aria-hidden /> : <LayoutGrid size={24} aria-hidden style={{ color: 'var(--text-secondary)' }} />}
    <span>{expanded ? 'Show less' : 'All Categories'}</span>
  </button>
);

const DIETARY: { key: DietaryFilter; label: string; Icon?: React.ElementType; color: string }[] = [
  { key: 'ALL', label: 'All', color: 'var(--primary)' },
  { key: 'VEG', label: 'Veg', Icon: Leaf, color: 'var(--green)' },
  { key: 'NON_VEG', label: 'Non-Veg', Icon: Drumstick, color: '#B91C1C' },
  { key: 'EGG', label: 'Egg', Icon: Egg, color: '#B45309' },
];

const SPICE_OPTIONS: { key: SpiceFilter; label: string }[] = [
  { key: 'ANY', label: 'Any' }, { key: 'MILD', label: 'Mild' }, { key: 'MEDIUM', label: 'Medium' }, { key: 'HOT', label: 'Hot' },
];
const SORT_OPTIONS: { key: SortMode; label: string }[] = [
  { key: 'MENU', label: 'Menu order' }, { key: 'PRICE_ASC', label: 'Price: low to high' }, { key: 'PRICE_DESC', label: 'Price: high to low' },
];

const Chip: React.FC<{ active: boolean; onClick: () => void; children: React.ReactNode }> = ({ active, onClick, children }) => (
  <button
    type="button"
    onClick={onClick}
    aria-pressed={active}
    className="px-3 py-1.5 rounded-full text-xs font-semibold cursor-pointer transition"
    style={active
      ? { background: 'var(--primary)', color: '#fff', border: '1px solid var(--primary)' }
      : { background: 'var(--white)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
  >
    {children}
  </button>
);

export const CategoryBrowser: React.FC<CategoryBrowserProps> = ({
  categories, selectedCategoryId, onSelectCategory,
  dietaryFilter, onSelectDietaryFilter, spiceFilter, onSelectSpiceFilter, sortMode, onSelectSortMode,
  onReset, canReset,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const filtersRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!filtersOpen) return;
    const close = (e: MouseEvent) => {
      if (filtersRef.current && !filtersRef.current.contains(e.target as Node)) setFiltersOpen(false);
    };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, [filtersOpen]);

  const needsToggle = categories.length > FIRST_ROW + SECOND_ROW_COLLAPSED;
  const firstRow = categories.slice(0, FIRST_ROW);
  let secondRow = !needsToggle
    ? categories.slice(FIRST_ROW)
    : expanded
      ? []
      : categories.slice(FIRST_ROW, FIRST_ROW + SECOND_ROW_COLLAPSED);
  if (needsToggle && !expanded) {
    // keep the active category visible even if it lives in the hidden part
    const sel = categories.find((c) => c.id === selectedCategoryId);
    const visible = [...firstRow, ...secondRow];
    if (sel && !visible.some((c) => c.id === sel.id)) secondRow = [...secondRow.slice(0, -1), sel];
  }
  const rest = needsToggle && expanded ? categories.slice(FIRST_ROW) : [];

  const pick = (id: string) => onSelectCategory(id === selectedCategoryId ? null : id);
  const activeExtras = (spiceFilter !== 'ANY' ? 1 : 0) + (sortMode !== 'MENU' ? 1 : 0);

  return (
    <section aria-label="Menu categories and filters" className="space-y-3">
      <div className="grid grid-cols-6 gap-1.5">
        {firstRow.map((c) => (
          <CategoryTile key={c.id} category={c} selected={c.id === selectedCategoryId} onClick={() => pick(c.id)} />
        ))}
      </div>

      {(secondRow.length > 0 || (needsToggle && !expanded)) && (
        <div className={`grid gap-1.5 ${needsToggle ? 'grid-cols-5' : 'grid-cols-6'}`}>
          {secondRow.map((c) => (
            <CategoryTile key={c.id} category={c} selected={c.id === selectedCategoryId} onClick={() => pick(c.id)} />
          ))}
          {needsToggle && !expanded && <ToggleTile expanded={false} onClick={() => setExpanded(true)} />}
        </div>
      )}

      {rest.length > 0 && (
        <div className="grid grid-cols-6 gap-1.5">
          {rest.map((c) => (
            <CategoryTile key={c.id} category={c} selected={c.id === selectedCategoryId} onClick={() => pick(c.id)} />
          ))}
          <ToggleTile expanded onClick={() => setExpanded(false)} />
        </div>
      )}

      <div className="flex items-center gap-1.5" role="group" aria-label="Dietary filters">
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar min-w-0 flex-1">
          {DIETARY.map(({ key, label, Icon, color }) => {
            const active = dietaryFilter === key;
            return (
              <button
                key={key}
                type="button"
                aria-pressed={active}
                onClick={() => onSelectDietaryFilter(key)}
                className="shrink-0 flex items-center gap-1 px-2.5 py-2 rounded-full text-xs font-semibold transition cursor-pointer"
                style={active
                  ? { background: color, color: '#fff', border: `1px solid ${color}` }
                  : { background: 'var(--white)', color: 'var(--text-primary)', border: '1px solid var(--border)' }}
              >
                {Icon && <Icon size={14} style={{ color: active ? '#fff' : color }} aria-hidden />}
                {label}
              </button>
            );
          })}
        </div>

        <div className="relative shrink-0" ref={filtersRef}>
          <button
            type="button"
            onClick={() => setFiltersOpen((v) => !v)}
            aria-expanded={filtersOpen}
            className="flex items-center gap-1 px-2.5 py-2 rounded-full text-xs font-semibold cursor-pointer"
            style={{ background: 'var(--white)', color: 'var(--text-primary)', border: `1px solid ${activeExtras ? 'var(--primary)' : 'var(--border)'}` }}
          >
            <SlidersHorizontal size={15} aria-hidden />
            Filters
            {activeExtras > 0 && (
              <span className="w-4 h-4 rounded-full text-[10px] font-bold flex items-center justify-center text-white" style={{ background: 'var(--primary)' }}>
                {activeExtras}
              </span>
            )}
            <ChevronDown size={14} aria-hidden />
          </button>

          {filtersOpen && (
            <div
              className="absolute right-0 top-full mt-2 w-64 rounded-2xl p-3 space-y-3 z-30 animate-scale-in"
              style={{ background: 'var(--white)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)' }}
            >
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wide mb-1.5" style={{ color: 'var(--text-muted)' }}>Spice level</p>
                <div className="flex flex-wrap gap-1.5">
                  {SPICE_OPTIONS.map((o) => (
                    <Chip key={o.key} active={spiceFilter === o.key} onClick={() => onSelectSpiceFilter(o.key)}>{o.label}</Chip>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wide mb-1.5" style={{ color: 'var(--text-muted)' }}>Sort by</p>
                <div className="flex flex-wrap gap-1.5">
                  {SORT_OPTIONS.map((o) => (
                    <Chip key={o.key} active={sortMode === o.key} onClick={() => onSelectSortMode(o.key)}>{o.label}</Chip>
                  ))}
                </div>
              </div>
              {canReset && (
                <button
                  type="button"
                  onClick={() => { onReset(); setFiltersOpen(false); }}
                  className="w-full text-xs font-bold py-2 rounded-xl cursor-pointer"
                  style={{ color: 'var(--primary)', background: 'var(--primary-bg)' }}
                >
                  Reset all
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  );
};
