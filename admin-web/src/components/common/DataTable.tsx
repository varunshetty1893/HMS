import React from 'react';
import { ChevronLeft, ChevronRight, Inbox } from 'lucide-react';
import { usePageTheme } from '@/hooks/usePageTheme';

export interface Column<T> {
  key: string;
  header: string;
  render?: (row: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  keyField: keyof T;
  isLoading?: boolean;
  emptyMessage?: string;
  pagination?: {
    page: number;
    pageSize: number;
    totalItems: number;
    totalPages: number;
    onPageChange: (newPage: number) => void;
  };
}

export function DataTable<T>({
  columns,
  data,
  keyField,
  isLoading = false,
  emptyMessage = 'No records found',
  pagination,
}: DataTableProps<T>) {
  const { L, heading, sub, muted, border, tableWrap, thead, tbodyRow, tbodyRowHover } = usePageTheme();

  if (isLoading) {
    return (
      <div className="w-full rounded-2xl p-12 text-center" style={tableWrap}>
        <div className="inline-block w-8 h-8 border-4 border-brand-500 border-t-transparent rounded-full animate-spin"></div>
        <p className="mt-3 text-sm" style={{ color: muted }}>Loading records...</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="w-full rounded-2xl p-12 text-center" style={tableWrap}>
        <div className="mx-auto w-12 h-12 rounded-2xl flex items-center justify-center" style={{ backgroundColor: L ? '#f5f0e8' : 'rgba(30,41,59,0.8)', color: muted }}>
          <Inbox className="w-6 h-6" />
        </div>
        <h4 className="mt-3 text-base font-semibold" style={{ color: heading }}>Empty</h4>
        <p className="mt-1 text-sm" style={{ color: muted }}>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="w-full rounded-2xl overflow-hidden shadow-sm" style={tableWrap}>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm" style={{ color: heading }}>
          <thead className="text-xs uppercase tracking-wider border-b" style={{ ...thead, borderBottomColor: border }}>
            <tr>
              {columns.map((col) => (
                <th key={col.key} className={`px-5 py-3.5 font-semibold ${col.className || ''}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y" style={{ borderColor: border }}>
            {data.map((row) => (
              <tr
                key={String(row[keyField])}
                className="transition"
                style={{ ...tbodyRow, borderBottomColor: border }}
                onMouseEnter={(e) => {
                  if (tbodyRowHover.backgroundColor) {
                    e.currentTarget.style.backgroundColor = tbodyRowHover.backgroundColor as string;
                  }
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'transparent';
                }}
              >
                {columns.map((col) => (
                  <td key={col.key} className={`px-5 py-3.5 ${col.className || ''}`}>
                    {col.render ? col.render(row) : (row as any)[col.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {pagination && pagination.totalPages > 1 && (
        <div
          className="flex items-center justify-between px-5 py-3 border-t text-xs"
          style={{
            borderTopColor: border,
            backgroundColor: L ? '#f5f0e8' : 'rgba(2,6,23,0.4)',
            color: sub,
          }}
        >
          <div>
            Showing {(pagination.page - 1) * pagination.pageSize + 1} to{' '}
            {Math.min(pagination.page * pagination.pageSize, pagination.totalItems)} of{' '}
            {pagination.totalItems} entries
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="p-1.5 rounded-lg border transition disabled:opacity-40 cursor-pointer"
              style={{ borderColor: border, color: heading }}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-semibold" style={{ color: heading }}>
              Page {pagination.page} of {pagination.totalPages}
            </span>
            <button
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page >= pagination.totalPages}
              className="p-1.5 rounded-lg border transition disabled:opacity-40 cursor-pointer"
              style={{ borderColor: border, color: heading }}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
