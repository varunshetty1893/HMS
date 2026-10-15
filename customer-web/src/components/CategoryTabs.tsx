import React, { useMemo, useState } from 'react';
import type { MenuCategory } from '../types';
import { ChevronDown, Grid2X2, UtensilsCrossed } from 'lucide-react';

interface CategoryTabsProps {
  categories: MenuCategory[];
  selectedCategoryId: string | null;
  onSelectCategory: (id: string | null) => void;
  dietaryFilter: 'ALL' | 'VEG' | 'NON_VEG' | 'EGG';
  onSelectDietaryFilter: (f: 'ALL' | 'VEG' | 'NON_VEG' | 'EGG') => void;
}

const DIETARY_OPTIONS: { key: 'ALL' | 'VEG' | 'NON_VEG' | 'EGG'; label: string }[] = [
  { key: 'ALL', label: 'All' }, { key: 'VEG', label: 'Veg' },
  { key: 'NON_VEG', label: 'Non-Veg' }, { key: 'EGG', label: 'Egg' },
];

function shortCategoryName(name: string): string {
  return name.replace('Vegetarian ', 'Veg ').replace('Non-Vegetarian ', 'Non-Veg ')
    .replace('Chicken, Mutton & Seafood ', '').replace(' Dishes', '').replace(' & Quick Meals', ' & Meals');
}

export const CategoryTabs: React.FC<CategoryTabsProps> = ({
  categories, selectedCategoryId, onSelectCategory, dietaryFilter, onSelectDietaryFilter,
}) => {
  const [showAll, setShowAll] = useState(false);
  const visibleCategories = useMemo(() => {
    if (showAll || categories.length <= 5 || selectedCategoryId) return categories;
    return categories.slice(0, 5);
  }, [categories, selectedCategoryId, showAll]);

  return (
    <section className="sticky z-20 px-4 py-3" style={{ top: '72px', background: 'var(--cream, #FFF8ED)', borderBottom: '1px solid var(--border)' }} aria-label="Menu categories and dietary filters">
      <div className="max-w-5xl mx-auto space-y-2.5">
        <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
          <button type="button" onClick={() => onSelectCategory(null)} className="min-h-15 px-2 py-2 rounded-xl text-xs font-bold flex flex-col items-center justify-center gap-1 transition cursor-pointer" style={selectedCategoryId === null ? { background: 'var(--primary)', color: '#fff', boxShadow: '0 3px 10px rgba(217,93,43,.2)' } : { background: 'var(--white)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
            <Grid2X2 size={15} aria-hidden />
            <span>All Categories</span>
          </button>
          {visibleCategories.map((category) => {
            const selected = category.id === selectedCategoryId;
            return (
              <button key={category.id} type="button" onClick={() => onSelectCategory(selected ? null : category.id)} className="min-h-15 px-2 py-2 rounded-xl text-xs font-bold flex flex-col items-center justify-center gap-1 text-center leading-tight transition cursor-pointer" style={selected ? { background: 'var(--primary)', color: '#fff', boxShadow: '0 3px 10px rgba(217,93,43,.2)' } : { background: 'var(--white)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
                <UtensilsCrossed size={15} aria-hidden />
                <span>{shortCategoryName(category.name)}</span>
              </button>
            );
          })}
        </div>
        {categories.length > 5 && !selectedCategoryId && (
          <button type="button" onClick={() => setShowAll((value) => !value)} className="w-full py-1 text-[11px] font-semibold flex items-center justify-center gap-1 cursor-pointer" style={{ color: 'var(--primary)' }}>
            <span>{showAll ? 'Show fewer categories' : `Show all ${categories.length} categories`}</span>
            <ChevronDown size={13} className={showAll ? 'rotate-180 transition-transform' : 'transition-transform'} />
          </button>
        )}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar" aria-label="Dietary filters">
          {DIETARY_OPTIONS.map(({ key, label }) => (
            <button key={key} type="button" onClick={() => onSelectDietaryFilter(key)} className="shrink-0 px-3 py-1.5 rounded-full text-[11px] font-bold transition cursor-pointer" style={dietaryFilter === key ? { background: key === 'VEG' ? 'var(--green)' : key === 'NON_VEG' ? '#B91C1C' : key === 'EGG' ? '#B45309' : 'var(--primary)', color: '#fff' } : { background: 'var(--white)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>
              {label}
            </button>
          ))}
          {(selectedCategoryId || dietaryFilter !== 'ALL') && (
            <button type="button" onClick={() => { onSelectCategory(null); onSelectDietaryFilter('ALL'); }} className="shrink-0 px-3 py-1.5 text-[11px] font-bold cursor-pointer" style={{ color: 'var(--primary)' }}>Reset</button>
          )}
        </div>
      </div>
    </section>
  );
};
