import React from 'react';
import { UtensilsCrossed } from 'lucide-react';
import type { MenuItem } from '../types';
import { dishImageCandidates } from '../utils/dishImages';

interface DishImageProps {
  item: MenuItem;
  className?: string;
  iconSize?: number;
}

/** Shows the item's verified photo, else a neutral placeholder. */
export const DishImage: React.FC<DishImageProps> = ({ item, className = '', iconSize = 24 }) => {
  const src = dishImageCandidates(item)[0];
  if (!src) {
    return (
      <div
        className={`flex items-center justify-center ${className}`}
        style={{ background: 'linear-gradient(135deg, var(--primary-bg), var(--bg-subtle))' }}
        role="img"
        aria-label={`${item.name} (picture not available)`}
      >
        <UtensilsCrossed size={iconSize} style={{ color: 'var(--primary-light)' }} aria-hidden />
      </div>
    );
  }
  return (
    <div className={`relative overflow-hidden ${className}`}>
      <img
        src={src}
        alt={item.name}
        className="w-full h-full object-cover"
        loading="lazy"
        draggable={false}
        onError={(event) => {
          event.currentTarget.classList.add('hidden');
          event.currentTarget.nextElementSibling?.classList.remove('hidden');
        }}
      />
      <div
        className="hidden absolute inset-0 flex items-center justify-center"
        style={{ background: 'linear-gradient(135deg, var(--primary-bg), var(--bg-subtle))' }}
        role="img"
        aria-label={`${item.name} (picture not available)`}
      >
        <UtensilsCrossed size={iconSize} style={{ color: 'var(--primary-light)' }} aria-hidden />
      </div>
    </div>
  );
};
