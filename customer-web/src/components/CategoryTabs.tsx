import React, { useRef, useEffect, useState } from 'react';
import type { MenuCategory } from '../types';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface CategoryTabsProps {
  categories: MenuCategory[];
  selectedCategoryId: string | null;
  onSelectCategory: (id: string | null) => void;
  dietaryFilter: 'ALL' | 'VEG' | 'NON_VEG' | 'EGG';
  onSelectDietaryFilter: (f: 'ALL' | 'VEG' | 'NON_VEG' | 'EGG') => void;
}

const DIETARY_OPTIONS: { key: 'ALL' | 'VEG' | 'NON_VEG' | 'EGG'; label: string }[] = [
  { key: 'ALL',     label: 'All' },
  { key: 'VEG',     label: 'Veg' },
  { key: 'NON_VEG', label: 'Non-Veg' },
  { key: 'EGG',     label: 'Egg' },
];

export const CategoryTabs: React.FC<CategoryTabsProps> = ({
  categories,
  selectedCategoryId,
  onSelectCategory,
  dietaryFilter,
  onSelectDietaryFilter,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLButtonElement>(null);

  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);

  const isDragging = useRef(false);
  const startX = useRef(0);
  const scrollLeftStart = useRef(0);

  const checkScroll = () => {
    if (!scrollRef.current) return;
    const { scrollLeft, scrollWidth, clientWidth } = scrollRef.current;
    setCanScrollLeft(scrollLeft > 5);
    setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 5);
  };

  useEffect(() => {
    checkScroll();
    window.addEventListener('resize', checkScroll);
    return () => window.removeEventListener('resize', checkScroll);
  }, [categories]);

  // Auto-scroll active tab into view
  useEffect(() => {
    if (activeRef.current && scrollRef.current) {
      const container = scrollRef.current;
      const el = activeRef.current;
      const offset = el.offsetLeft - container.offsetWidth / 2 + el.offsetWidth / 2;
      container.scrollTo({ left: offset, behavior: 'smooth' });
      setTimeout(checkScroll, 300);
    }
  }, [selectedCategoryId]);

  const handleScrollBy = (amount: number) => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({ left: amount, behavior: 'smooth' });
      setTimeout(checkScroll, 200);
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (!scrollRef.current) return;
    isDragging.current = true;
    startX.current = e.pageX - scrollRef.current.offsetLeft;
    scrollLeftStart.current = scrollRef.current.scrollLeft;
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging.current || !scrollRef.current) return;
    e.preventDefault();
    const x = e.pageX - scrollRef.current.offsetLeft;
    const walk = (x - startX.current) * 1.5;
    scrollRef.current.scrollLeft = scrollLeftStart.current - walk;
    checkScroll();
  };

  const handleMouseUp = () => {
    isDragging.current = false;
  };

  const handleWheel = (e: React.WheelEvent) => {
    if (scrollRef.current && e.deltaY !== 0) {
      scrollRef.current.scrollLeft += e.deltaY;
      checkScroll();
    }
  };

  return (
    <div
      className="sticky z-20"
      style={{
        top: '56px',
        background: 'var(--white)',
        borderBottom: '1px solid var(--border)',
      }}
    >
      <div className="max-w-5xl mx-auto relative">
        {/* Left Arrow Button for easy scrolling */}
        {canScrollLeft && (
          <button
            onClick={() => handleScrollBy(-180)}
            className="absolute left-1 top-2.5 z-10 w-7 h-7 rounded-full bg-white/95 shadow-md border border-stone-200 flex items-center justify-center transition-all cursor-pointer hover:bg-stone-50"
            style={{ color: 'var(--primary)' }}
            title="Scroll left"
          >
            <ChevronLeft size={16} />
          </button>
        )}

        {/* Right Arrow Button for easy scrolling */}
        {canScrollRight && (
          <button
            onClick={() => handleScrollBy(180)}
            className="absolute right-1 top-2.5 z-10 w-7 h-7 rounded-full bg-white/95 shadow-md border border-stone-200 flex items-center justify-center transition-all cursor-pointer hover:bg-stone-50"
            style={{ color: 'var(--primary)' }}
            title="Scroll right"
          >
            <ChevronRight size={16} />
          </button>
        )}

        {/* Category pills container (scrollbar hidden, touch + mouse drag + wheel scrollable) */}
        <div
          ref={scrollRef}
          onScroll={checkScroll}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          className="flex items-center gap-2 px-4 py-2.5 overflow-x-auto no-scrollbar scroll-smooth select-none"
          style={{
            scrollbarWidth: 'none',
            msOverflowStyle: 'none',
            cursor: isDragging.current ? 'grabbing' : 'grab',
          }}
        >
          {/* "All" pill */}
          <button
            ref={selectedCategoryId === null ? activeRef : null}
            onClick={() => onSelectCategory(null)}
            className="flex-shrink-0 px-4 py-1.5 rounded-full text-xs font-bold transition-all whitespace-nowrap cursor-pointer shadow-xs"
            style={
              selectedCategoryId === null
                ? { background: 'var(--primary)', color: '#fff' }
                : { background: 'var(--bg-subtle)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }
            }
          >
            All
          </button>

          {categories.map((cat) => (
            <button
              key={cat.id}
              ref={selectedCategoryId === cat.id ? activeRef : null}
              onClick={() => onSelectCategory(cat.id === selectedCategoryId ? null : cat.id)}
              className="flex-shrink-0 px-4 py-1.5 rounded-full text-xs font-bold transition-all whitespace-nowrap cursor-pointer shadow-xs"
              style={
                selectedCategoryId === cat.id
                  ? { background: 'var(--primary)', color: '#fff' }
                  : { background: 'var(--bg-subtle)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }
              }
            >
              {cat.name}
              <span
                className="ml-1.5 opacity-70 text-[10px] font-mono"
              >
                {cat.items.length}
              </span>
            </button>
          ))}
        </div>

        {/* Dietary quick-filter row */}
        <div
          className="flex items-center gap-1.5 px-4 pb-2.5 overflow-x-auto no-scrollbar select-none"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
        >
          {DIETARY_OPTIONS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => onSelectDietaryFilter(key)}
              className="flex-shrink-0 flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-bold transition-all whitespace-nowrap cursor-pointer"
              style={
                dietaryFilter === key
                  ? {
                      background: key === 'VEG' ? 'var(--green)' : key === 'NON_VEG' ? '#B91C1C' : key === 'EGG' ? '#B45309' : 'var(--primary)',
                      color: '#fff',
                    }
                  : {
                      background: 'var(--bg-subtle)',
                      color: 'var(--text-secondary)',
                      border: '1px solid var(--border)',
                    }
              }
            >
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
