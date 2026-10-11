import React from 'react';
import type { MenuCategory } from '../types';

interface CategoryTabsProps {
  categories: MenuCategory[];
  selectedCategoryId: string | null;
  onSelectCategory: (id: string | null) => void;
  dietaryFilter: 'ALL' | 'VEG' | 'NON_VEG' | 'EGG';
  onSelectDietaryFilter: (filter: 'ALL' | 'VEG' | 'NON_VEG' | 'EGG') => void;
}

export const CategoryTabs: React.FC<CategoryTabsProps> = ({
  categories,
  selectedCategoryId,
  onSelectCategory,
  dietaryFilter,
  onSelectDietaryFilter,
}) => {
  return (
    <div className="sticky top-[61px] z-20 bg-slate-900/95 backdrop-blur-md border-b border-slate-800/80 px-4 py-2.5 space-y-2">
      {/* Category Pills */}
      <div className="flex items-center space-x-2 overflow-x-auto no-scrollbar scroll-smooth">
        <button
          onClick={() => onSelectCategory(null)}
          className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
            selectedCategoryId === null
              ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
              : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white'
          }`}
        >
          All Items
        </button>
        {categories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => onSelectCategory(cat.id)}
            className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs font-medium transition-all ${
              selectedCategoryId === cat.id
                ? 'bg-orange-500 text-white shadow-sm shadow-orange-500/30'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white'
            }`}
          >
            {cat.name}
          </button>
        ))}
      </div>

      {/* Dietary Filters */}
      <div className="flex items-center space-x-1.5 text-[11px]">
        <button
          onClick={() => onSelectDietaryFilter('ALL')}
          className={`px-2.5 py-1 rounded-md transition-colors ${
            dietaryFilter === 'ALL'
              ? 'bg-slate-700 text-white font-semibold'
              : 'bg-slate-800/50 text-slate-400 hover:text-slate-200'
          }`}
        >
          All Types
        </button>

        <button
          onClick={() => onSelectDietaryFilter('VEG')}
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md transition-colors ${
            dietaryFilter === 'VEG'
              ? 'bg-emerald-950 text-emerald-400 border border-emerald-600 font-semibold'
              : 'bg-slate-800/50 text-slate-400 hover:text-emerald-400'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
          <span>Veg Only</span>
        </button>

        <button
          onClick={() => onSelectDietaryFilter('NON_VEG')}
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md transition-colors ${
            dietaryFilter === 'NON_VEG'
              ? 'bg-rose-950 text-rose-400 border border-rose-600 font-semibold'
              : 'bg-slate-800/50 text-slate-400 hover:text-rose-400'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-rose-500"></span>
          <span>Non-Veg</span>
        </button>

        <button
          onClick={() => onSelectDietaryFilter('EGG')}
          className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md transition-colors ${
            dietaryFilter === 'EGG'
              ? 'bg-amber-950 text-amber-400 border border-amber-600 font-semibold'
              : 'bg-slate-800/50 text-slate-400 hover:text-amber-400'
          }`}
        >
          <span className="w-2 h-2 rounded-full bg-amber-400"></span>
          <span>Egg</span>
        </button>
      </div>
    </div>
  );
};
