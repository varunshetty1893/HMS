import React, { useMemo, useState } from 'react';
import type { MenuCategory } from '../types';
import {
  Grid2X2, ChevronDown, ChevronUp, UtensilsCrossed, Coffee, Soup, Cookie, IceCreamCone,
  Salad, Egg, Beef, Drumstick, Wheat, Sandwich,
} from 'lucide-react';

export type DietaryFilter = 'ALL' | 'VEG' | 'NON_VEG' | 'EGG';

interface CategoryBrowserProps {
  categories: MenuCategory[];
  selectedCategoryId: string | null;
  onSelectCategory: (id: string | null) => void;
  /** Item count per category id after search + dietary filters are applied. */
  counts: Record<string, number>;
  dietaryFilter: DietaryFilter;
  onSelectDietaryFilter: (f: DietaryFilter) => void;
  onReset: () => void;
  canReset: boolean;
}

const DIETARY_OPTIONS: { key: DietaryFilter; label: string }[] = [
  { key: 'ALL', label: 'All' }, { key: 'VEG', label: 'Veg' },
  { key: 'NON_VEG', label: 'Non-Veg' }, { key: 'EGG', label: 'Egg' },
];

// Display-only shortening of the real category name. Never merges categories.
export function shortCategoryName(name: string): string {
  return name
    .replace('Non-Vegetarian ', 'Non-Veg ')
    .replace('Vegetarian ', 'Veg ')
    .replace('Chicken, Mutton & Seafood ', '')
    .replace(' Dishes', '')
    .replace(' & Quick Meals', '')
    .replace(' & Appetizers', '')
    .trim();
}

function iconFor(name: string): React.ElementType {
  const n = name.toLowerCase();
  if (/(biryani|biriyani|rice|pulao)/.test(n)) return Wheat;
  if (/(bread|roti|naan)/.test(n)) return Sandwich;
  if (/(beverage|drink|juice|tea|coffee)/.test(n)) return Coffee;
  if (/(ice cream)/.test(n)) return IceCreamCone;
  if (/(dessert|sweet)/.test(n)) return Cookie;
  if (/(salad)/.test(n)) return Salad;
  if (/(soup)/.test(n)) return Soup;
  if (/(egg)/.test(n)) return Egg;
  if (/(chicken|starter|tandoor|kebab)/.test(n)) return Drumstick;
  if (/(mutton|seafood|fish|non-veg)/.test(n)) return Beef;
  return UtensilsCrossed;
}

const COLLAPSED_ROWS = 2;
const COLS = 4; // mobile grid columns; collapsed state shows COLS * COLLAPSED_ROWS cells

const tileClass =
  'relative min-h-[62px] px-1.5 py-2 rounded-2xl text-[11px] font-semibold flex flex-col items-center justify-center gap-1 text-center leading-tight transition cursor-pointer';

export const CategoryBrowser: React.FC<CategoryBrowserProps> = ({
  categories, selectedCategoryId, onSelectCategory, counts,
  dietaryFilter, onSelectDietaryFilter, onReset, canReset,
}) => {
  const [expanded, setExpanded] = useState(false);

  // Cells available in the collapsed grid: "All" + categories (+ a toggle tile if some are hidden).
  const capacity = COLS * COLLAPSED_ROWS;
  const needsToggle = categories.length + 1 > capacity;
  const collapsedSlots = needsToggle ? capacity - 2 : capacity - 1; // minus All (and toggle)

  const shown = useMemo(() => {
    if (expanded || !needsToggle) return categories;
    const first = categories.slice(0, collapsedSlots);
    const sel = categories.find((c) => c.id === selectedCategoryId);
    // keep the active category visible even when it lives in the hidden part
    if (sel && !first.some((c) => c.id === sel.id)) first[first.length - 1] = sel;
    return first;
  }, [categories, expanded, needsToggle, collapsedSlots, selectedCategoryId]);

  const hiddenCount = categories.length - shown.length;
  const tileStyle = (selected: boolean, empty = false): React.CSSProperties =>
    selected
      ? { background: 'var(--primary)', color: '#fff', boxShadow: '0 3px 10px rgba(217,93,43,.25)', border: '1px solid var(--primary)' }
      : { background: 'var(--white)', color: 'var(--text-primary)', border: '1px solid var(--border)', opacity: empty ? 0.5 : 1 };

  return (
    <section aria-label="Menu categories and dietary filters" className="space-y-2.5">
      <div className={`grid gap-2 auto-rows-fr grid-cols-4 sm:grid-cols-6 md:grid-cols-8`}>
        <button type="button" onClick={() => onSelectCategory(null)} className={tileClass}
          style={tileStyle(selectedCategoryId === null)} aria-pressed={selectedCategoryId === null}>
          <Grid2X2 size={18} aria-hidden />
          <span>All</span>
        </button>

        {shown.map((category) => {
          const selected = category.id === selectedCategoryId;
          const count = counts[category.id] ?? 0;
          const Icon = iconFor(category.name);
          return (
            <button key={category.id} type="button" aria-pressed={selected}
              onClick={() => onSelectCategory(selected ? null : category.id)}
              className={tileClass} style={tileStyle(selected, count === 0)}>
              <Icon size={18} aria-hidden style={{ color: selected ? '#fff' : 'var(--primary)' }} />
              <span className="line-clamp-2 break-words">{shortCategoryName(category.name)}</span>
              <span className="text-[10px] font-medium" style={{ opacity: 0.75 }}>{count}</span>
            </button>
          );
        })}

        {needsToggle && (
          <button type="button" onClick={() => setExpanded((v) => !v)} aria-expanded={expanded}
            className={tileClass}
            style={{ background: 'var(--primary-bg)', color: 'var(--primary)', border: '1px dashed var(--primary)' }}>
            {expanded ? <ChevronUp size={18} aria-hidden /> : <ChevronDown size={18} aria-hidden />}
            <span>{expanded ? 'Show less' : `+${hiddenCount} more`}</span>
          </button>
        )}
      </div>

      {/* Dietary filters — one compact row */}
      <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar" role="group" aria-label="Dietary filters">
        {DIETARY_OPTIONS.map(({ key, label }) => {
          const active = dietaryFilter === key;
          const bg = key === 'VEG' ? 'var(--green)' : key === 'NON_VEG' ? '#B91C1C' : key === 'EGG' ? '#B45309' : 'var(--primary)';
          return (
            <button key={key} type="button" aria-pressed={active} onClick={() => onSelectDietaryFilter(key)}
              className="shrink-0 px-4 py-2 rounded-full text-xs font-bold transition cursor-pointer"
              style={active ? { background: bg, color: '#fff', border: `1px solid ${bg}` }
                            : { background: 'var(--white)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
              {label}
            </button>
          );
        })}
        {canReset && (
          <button type="button" onClick={onReset} className="shrink-0 ml-auto px-3 py-2 text-xs font-bold cursor-pointer"
            style={{ color: 'var(--primary)' }}>
            Reset
          </button>
        )}
      </div>
    </section>
  );
};
