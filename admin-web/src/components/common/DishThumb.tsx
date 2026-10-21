import React from 'react';
import { UtensilsCrossed } from 'lucide-react';
import type { MenuItem } from '@/types/api';
import { dishImageCandidates } from '@/utils/dishArt';

/** Restaurant photo -> neutral placeholder. Never show a mismatched cartoon. */
export const DishThumb: React.FC<{ item: MenuItem; className?: string }> = ({ item, className = 'w-16 h-16' }) => {
  const src = dishImageCandidates(item)[0];
  if (!src) {
    return (
      <div className={`${className} rounded-xl border border-dashed border-slate-200 bg-slate-50 flex items-center justify-center shrink-0 text-slate-300`}>
        <UtensilsCrossed size={20} />
      </div>
    );
  }
  // Intentionally stateless: the menu can refresh from placeholders to 90
  // online photos in one update.  Keeping this renderer hook-free prevents a
  // hook-order crash when that happens.  A failed external URL simply becomes
  // the neutral utensil placeholder.
  return (
    <div className={`${className} relative rounded-xl border border-slate-200 shrink-0 bg-slate-50 overflow-hidden`}>
      <img
        src={src}
        alt={item.name}
        loading="lazy"
        draggable={false}
        onError={(event) => {
          event.currentTarget.classList.add('hidden');
          event.currentTarget.nextElementSibling?.classList.remove('hidden');
        }}
        className="w-full h-full object-cover"
      />
      <div className="hidden absolute inset-0 flex items-center justify-center text-slate-300">
        <UtensilsCrossed size={20} />
      </div>
    </div>
  );
};
