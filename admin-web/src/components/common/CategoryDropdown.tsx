import React, { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown, LayoutGrid } from 'lucide-react';

export interface CategoryOption {
  id: string;
  name: string;
  count: number;
}

interface Props {
  options: CategoryOption[];
  totalCount: number;
  value: string; // 'ALL' or a category id
  onChange: (id: string) => void;
}

/** Compact category picker: one button, scrollable list (no horizontal scrolling needed). */
export const CategoryDropdown: React.FC<Props> = ({ options, totalCount, value, onChange }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const selected = value === 'ALL' ? null : options.find((o) => o.id === value);
  const label = selected ? selected.name : 'All Categories';
  const count = selected ? selected.count : totalCount;

  const Row: React.FC<{ id: string; name: string; count: number }> = ({ id, name, count: n }) => {
    const active = value === id;
    return (
      <button
        type="button"
        role="option"
        aria-selected={active}
        onClick={() => { onChange(id); setOpen(false); }}
        className={`w-full flex items-center justify-between gap-3 px-3 py-2 text-left text-sm rounded-lg cursor-pointer transition ${
          active ? 'bg-brand-50 text-brand-700 font-bold' : 'text-slate-700 hover:bg-slate-50'
        }`}
      >
        <span className="flex items-center gap-2 min-w-0">
          {active ? <Check className="w-4 h-4 shrink-0" /> : <span className="w-4 shrink-0" />}
          <span className="truncate">{name}</span>
        </span>
        <span className="text-[11px] font-semibold px-1.5 rounded-full bg-slate-100 text-slate-500">{n}</span>
      </button>
    );
  };

  return (
    <div className="relative w-full md:w-72 shrink-0" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className={`w-full flex items-center justify-between gap-2 px-3.5 py-2 rounded-xl bg-white border text-sm font-semibold cursor-pointer shadow-xs transition ${
          open ? 'border-brand-500 ring-1 ring-brand-500' : 'border-slate-200 hover:border-slate-300'
        }`}
      >
        <span className="flex items-center gap-2 min-w-0 text-slate-900">
          <LayoutGrid className="w-4 h-4 text-slate-400 shrink-0" />
          <span className="truncate">{label}</span>
          <span className="text-[11px] font-bold px-1.5 rounded-full bg-slate-100 text-slate-600">{count}</span>
        </span>
        <ChevronDown className={`w-4 h-4 text-slate-400 shrink-0 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute z-40 left-0 right-0 mt-2 max-h-80 overflow-y-auto rounded-2xl bg-white border border-slate-200 shadow-xl p-1.5"
        >
          <Row id="ALL" name="All Categories" count={totalCount} />
          <div className="my-1 border-t border-slate-100" />
          {options.map((o) => (
            <Row key={o.id} id={o.id} name={o.name} count={o.count} />
          ))}
        </div>
      )}
    </div>
  );
};
