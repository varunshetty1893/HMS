import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

// ─── Reusable pagination hook ─────────────────────────────────────────────────
export function usePagination<T>(items: T[], pageSize = 15) {
  const [page, setPage] = useState(1);

  // Reset to page 1 whenever the underlying data changes
  useEffect(() => {
    setPage(1);
  }, [items]);

  const totalPages = Math.max(1, Math.ceil(items.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const start = (safePage - 1) * pageSize;
  const slice = items.slice(start, start + pageSize);

  return {
    slice,
    page: safePage,
    totalPages,
    totalItems: items.length,
    pageSize,
    start,
    end: Math.min(start + pageSize, items.length),
    setPage,
    hasPrev: safePage > 1,
    hasNext: safePage < totalPages,
    prev: () => setPage((p) => Math.max(1, p - 1)),
    next: () => setPage((p) => Math.min(totalPages, p + 1)),
  };
}

// ─── Pagination controls component ───────────────────────────────────────────
interface PaginationBarProps {
  page: number;
  totalPages: number;
  totalItems: number;
  start: number;
  end: number;
  hasPrev: boolean;
  hasNext: boolean;
  prev: () => void;
  next: () => void;
  setPage: (p: number) => void;
  border: string;
  muted: string;
  heading: string;
}

export const PaginationBar: React.FC<PaginationBarProps> = ({
  page,
  totalPages,
  totalItems,
  start,
  end,
  hasPrev,
  hasNext,
  prev,
  next,
  border,
  muted,
  heading,
}) => {
  if (totalItems === 0) return null;
  return (
    <div
      className="flex items-center justify-between px-6 py-3 border-t text-xs"
      style={{ borderTopColor: border, color: muted }}
    >
      <span>
        Showing <strong style={{ color: heading }}>{start + 1}–{end}</strong> of{' '}
        <strong style={{ color: heading }}>{totalItems}</strong> records
      </span>
      <div className="flex items-center gap-2">
        <button
          onClick={prev}
          disabled={!hasPrev}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          style={{ borderColor: border, color: heading }}
        >
          <ChevronLeft className="w-3.5 h-3.5" />
          Prev
        </button>
        <span className="px-2 font-mono" style={{ color: heading }}>
          {page} / {totalPages}
        </span>
        <button
          onClick={next}
          disabled={!hasNext}
          className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium border transition disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          style={{ borderColor: border, color: heading }}
        >
          Next
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

