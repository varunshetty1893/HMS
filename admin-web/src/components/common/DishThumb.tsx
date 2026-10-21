import React, { useState } from 'react';
import { UtensilsCrossed } from 'lucide-react';
import type { MenuItem } from '@/types/api';
import { dishImageCandidates } from '@/utils/dishArt';

/** Photo -> item illustration -> placeholder icon. */
export const DishThumb: React.FC<{ item: MenuItem; className?: string }> = ({ item, className = 'w-16 h-16' }) => {
  const candidates = dishImageCandidates(item);
  return <Inner key={candidates.join('|')} name={item.name} candidates={candidates} className={className} />;
};

const Inner: React.FC<{ name: string; candidates: string[]; className: string }> = ({ name, candidates, className }) => {
  const [index, setIndex] = useState(0);
  const src = candidates[index];
  if (!src) {
    return (
      <div className={`${className} rounded-xl border border-dashed border-slate-200 bg-slate-50 flex items-center justify-center shrink-0 text-slate-300`}>
        <UtensilsCrossed size={20} />
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={name}
      loading="lazy"
      draggable={false}
      onError={() => setIndex((i) => i + 1)}
      className={`${className} rounded-xl object-cover border border-slate-200 shrink-0 bg-slate-50`}
    />
  );
};
