import React, { useState } from 'react';
import { UtensilsCrossed } from 'lucide-react';
import type { MenuItem } from '../types';
import { dishImageCandidates } from '../utils/dishImages';

interface DishImageProps {
  item: MenuItem;
  className?: string;
  iconSize?: number;
}

/** Shows the item's real photo, else a dish-specific photographic fallback. */
export const DishImage: React.FC<DishImageProps> = ({ item, className = '', iconSize = 24 }) => {
  const candidates = dishImageCandidates(item);
  const key = candidates.join('|');
  return <DishImageInner key={key} name={item.name} candidates={candidates} className={className} iconSize={iconSize} />;
};

const DishImageInner: React.FC<{ name: string; candidates: string[]; className: string; iconSize: number }> = ({
  name, candidates, className, iconSize,
}) => {
  const [index, setIndex] = useState(0);
  const src = candidates[index];
  if (!src) {
    return (
      <div
        className={`flex items-center justify-center ${className}`}
        style={{ background: 'linear-gradient(135deg, var(--primary-bg), var(--bg-subtle))' }}
        role="img"
        aria-label={`${name} (picture not available)`}
      >
        <UtensilsCrossed size={iconSize} style={{ color: 'var(--primary-light)' }} aria-hidden />
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={name}
      className={`object-cover ${className}`}
      loading="lazy"
      draggable={false}
      onError={() => setIndex((i) => i + 1)}
    />
  );
};
