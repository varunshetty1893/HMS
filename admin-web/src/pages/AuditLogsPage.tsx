import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { settingsAuditApi, AuditLogFilters } from '@/api/settingsAuditApi';
import { formatDateTimeIst } from '@/utils/dateIst';
import { DataTable } from '@/components/common/DataTable';
import {
  Download,
  Eye,
  Loader2,
  RefreshCw,
  Search,
  ShieldAlert,
  X,
} from 'lucide-react';
import { AuditLog, PaginationMeta } from '@/types/api';

/* ─── Helpers ─────────────────────────────────────────────────────────────── */

const ACTION_LABELS: Record<string, string> = {
  PRICE_VARIANT_PRICE_CHANGED: 'Dish Price Changed',
  QR_TOKEN_ROTATED: 'QR Code Regenerated',
  QR_REGENERATED: 'QR Code Regenerated',
  STAFF_USER_CREATED: 'New Staff Account Created',
  STAFF_USER_UPDATED: 'Staff Account Updated',
  STAFF_PASSWORD_RESET: 'Staff Password Reset',
  RESTAURANT_SETTINGS_UPDATED: 'Restaurant Settings Changed',
  ORDER_MODIFIED: 'Order Items Modified',
  ORDER_CANCELLED: 'Order Cancelled',
  BILL_GENERATED: 'Bill Generated',
  BILL_DISCOUNT_APPLIED: 'Manager Discount Applied',
  BILL_VOIDED_FOR_REVISION: 'Bill Cancelled to Fix Order',
  PAYMENT_RECORDED: 'Customer Payment Received',
  SESSION_LIMIT_OVERRIDDEN: 'Spending Limit Overridden',
  AUDIT_LOG_EXPORTED: 'Audit Log Exported',
};

const titleCase = (code: string) =>
  code
    .toLowerCase()
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

const actionLabel = (code: string) => ACTION_LABELS[code] || titleCase(code);

/** Colour-code badges so risky events stand out at a glance (all pass WCAG AA on white). */
const badgeClass = (code: string): string => {
  if (/(CANCEL|VOID|DELETE|REJECT|OVERRID|RESET|DEACTIVAT)/.test(code))
    return 'bg-rose-50 text-rose-800 border-rose-300';
  if (/(PAYMENT|BILL|DISCOUNT|PRICE)/.test(code)) return 'bg-sky-50 text-sky-800 border-sky-300';
  if (/(CREATED|UPLOADED|GENERATED)/.test(code)) return 'bg-emerald-50 text-emerald-800 border-emerald-300';
  if (/(UPDATED|CHANGED|MODIFIED|ROTATED|REGENERATED)/.test(code))
    return 'bg-amber-50 text-amber-900 border-amber-300';
  return 'bg-slate-100 text-slate-800 border-slate-300';
};

/** Today's calendar date in IST as YYYY-MM-DD, shifted by `offsetDays`. */
const istDate = (offsetDays = 0): string => {
  const d = new Date(Date.now() + offsetDays * 86400000);
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(d);
};

type Preset = 'all' | 'today' | '7d' | '30d' | 'custom';

const PRESETS: { id: Preset; label: string }[] = [
  { id: 'all', label: 'All time' },
  { id: 'today', label: 'Today' },
  { id: '7d', label: 'Last 7 days' },
  { id: '30d', label: 'Last 30 days' },
  { id: 'custom', label: 'Custom' },
];

const selectCls =
  'px-3.5 py-2 rounded-xl bg-white border border-slate-300 text-xs font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-orange-300 shadow-xs';

/* ─── Page ────────────────────────────────────────────────────────────────── */

export const AuditLogsPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [pagination, setPagination] = useState<PaginationMeta>({
    page: 1,
    page_size: 20,
    total_items: 0,
    total_pages: 0,
    has_next: false,
    has_prev: false,
  });

  // Filters
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [entityFilter, setEntityFilter] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [preset, setPreset] = useState<Preset>('all');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  // Dropdown options discovered from real data
  const [actionOptions, setActionOptions] = useState<string[]>(Object.keys(ACTION_LABELS));
  const [entityOptions, setEntityOptions] = useState<string[]>([]);
  const [roleOptions, setRoleOptions] = useState<string[]>(['ADMIN', 'WAITER', 'KITCHEN', 'CUSTOMER', 'SYSTEM']);

  const [isLoading, setIsLoading] = useState(true);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);
  const requestId = useRef(0);

  // Debounce search typing
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search.trim()), 400);
    return () => clearTimeout(t);
  }, [search]);

  // Load filter options once
  useEffect(() => {
    settingsAuditApi
      .getAuditFacets()
      .then((f) => {
        setActionOptions(Array.from(new Set([...Object.keys(ACTION_LABELS), ...f.action_types])));
        setEntityOptions(f.entity_types);
        setRoleOptions(Array.from(new Set([...roleOptions, ...f.actor_roles])));
      })
      .catch(() => {
        /* filters still work with the built-in lists */
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const applyPreset = (p: Preset) => {
    setPreset(p);
    if (p === 'all') {
      setFromDate('');
      setToDate('');
    } else if (p === 'today') {
      setFromDate(istDate(0));
      setToDate(istDate(0));
    } else if (p === '7d') {
      setFromDate(istDate(-6));
      setToDate(istDate(0));
    } else if (p === '30d') {
      setFromDate(istDate(-29));
      setToDate(istDate(0));
    }
  };

  const activeFilters: AuditLogFilters = useMemo(
    () => ({
      q: debouncedSearch || undefined,
      action_type: actionFilter || undefined,
      entity_type: entityFilter || undefined,
      actor_role: roleFilter || undefined,
      from: fromDate || undefined,
      to: toDate || undefined,
    }),
    [debouncedSearch, actionFilter, entityFilter, roleFilter, fromDate, toDate]
  );

  const filterCount = Object.values(activeFilters).filter(Boolean).length;

  const fetchLogs = useCallback(
    async (page = 1) => {
      const myId = ++requestId.current;
      setIsLoading(true);
      try {
        const data = await settingsAuditApi.listAuditLogs({ ...activeFilters, page, page_size: 20 });
        if (myId !== requestId.current) return; // a newer request superseded this one
        setLogs(data.items);
        setPagination(data.pagination);
        setError(null);
      } catch (err: any) {
        if (myId !== requestId.current) return;
        setError(err?.message || 'Failed to fetch audit records');
      } finally {
        if (myId === requestId.current) setIsLoading(false);
      }
    },
    [activeFilters]
  );

  useEffect(() => {
    fetchLogs(1);
  }, [fetchLogs]);

  const clearFilters = () => {
    setSearch('');
    setDebouncedSearch('');
    setActionFilter('');
    setEntityFilter('');
    setRoleFilter('');
    applyPreset('all');
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      const blob = await settingsAuditApi.exportAuditLogsXlsx(activeFilters);
      if (!(blob instanceof Blob)) throw new Error('Unexpected export response from server.');
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `spicehub_audit_log_${istDate(0)}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err: any) {
      setError(err?.message || 'Failed to export audit log');
    } finally {
      setIsExporting(false);
    }
  };

  const columns = [
    {
      key: 'created_at',
      header: 'Timestamp (IST)',
      render: (row: AuditLog) => (
        <span className="font-mono text-xs font-medium text-slate-800 whitespace-nowrap">
          {formatDateTimeIst(row.created_at)}
        </span>
      ),
    },
    {
      key: 'action_type',
      header: 'Action Event',
      render: (row: AuditLog) => (
        <span
          title={actionLabel(row.action_type)}
          className={`px-2.5 py-1 rounded-full text-xs font-mono font-bold border ${badgeClass(row.action_type)}`}
        >
          {row.action_type}
        </span>
      ),
    },
    {
      key: 'actor',
      header: 'Actor & Role',
      render: (row: AuditLog) => (
        <div className="text-xs">
          <span className="font-semibold text-slate-900">@{row.actor_username || row.actor_role}</span>
          <span className="block text-[11px] font-mono text-slate-600">
            {row.actor_username ? `${row.actor_role}` : row.actor_user_id ? `${row.actor_user_id.slice(0, 8)}...` : ''}
          </span>
        </div>
      ),
    },
    {
      key: 'entity',
      header: 'Target Entity',
      render: (row: AuditLog) => (
        <div className="text-xs font-mono">
          <span className="font-semibold text-slate-800 uppercase">{row.entity_type}</span>
          <span className="block text-[11px] text-slate-600 break-all">#{row.entity_id}</span>
        </div>
      ),
    },
    {
      key: 'reason',
      header: 'Audit Reason',
      render: (row: AuditLog) => (
        <span className="text-xs text-slate-700 italic">{row.reason ? `"${row.reason}"` : '—'}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'text-right',
      render: (row: AuditLog) => (
        <button
          onClick={() => setSelectedLog(row)}
          title="Inspect State Snapshots"
          className="p-1.5 rounded-lg text-brand-700 hover:text-brand-800 hover:bg-orange-50 border border-transparent hover:border-orange-200 transition cursor-pointer"
        >
          <Eye className="w-4 h-4" />
        </button>
      ),
    },
  ];

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-ink flex items-center gap-2.5">
            <ShieldAlert className="w-6 h-6 text-brand-600" />
            <span>Immutable Audit Log Viewer</span>
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Database trigger-protected chronological trace of all state mutations & overrides
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => fetchLogs(pagination.page)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-white hover:bg-slate-50 text-slate-800 border border-slate-300 transition cursor-pointer"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
          <button
            onClick={handleExport}
            disabled={isExporting || pagination.total_items === 0}
            title={
              pagination.total_items === 0
                ? 'Nothing to export for these filters'
                : `Export all ${pagination.total_items} matching entries to Excel`
            }
            className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-brand-600 hover:bg-brand-700 text-white shadow-sm transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            <span>{isExporting ? 'Preparing…' : 'Export to Excel'}</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-300 text-xs font-medium text-rose-800">
          {error}
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search reason, entity ID, staff username…"
              className="pl-9 pr-8 py-2 w-72 rounded-xl bg-white border border-slate-300 text-xs text-slate-900 placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-orange-300 shadow-xs"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-800 cursor-pointer"
                title="Clear search"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <select value={actionFilter} onChange={(e) => setActionFilter(e.target.value)} className={selectCls}>
            <option value="">All Action Types</option>
            {actionOptions.map((a) => (
              <option key={a} value={a}>
                {actionLabel(a)}
              </option>
            ))}
          </select>

          <select value={entityFilter} onChange={(e) => setEntityFilter(e.target.value)} className={selectCls}>
            <option value="">All Entities</option>
            {entityOptions.map((e) => (
              <option key={e} value={e}>
                {titleCase(e)}
              </option>
            ))}
          </select>

          <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className={selectCls}>
            <option value="">All Actor Roles</option>
            {roleOptions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>

          {filterCount > 0 && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold text-brand-700 hover:bg-orange-50 border border-orange-200 transition cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear filters ({filterCount})</span>
            </button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-semibold text-slate-700 mr-1">Date (IST):</span>
          {PRESETS.map((p) => (
            <button
              key={p.id}
              onClick={() => applyPreset(p.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition cursor-pointer ${
                preset === p.id
                  ? 'bg-brand-600 text-white border-transparent shadow-sm'
                  : 'bg-white text-slate-700 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {p.label}
            </button>
          ))}
          {preset === 'custom' && (
            <div className="flex items-center gap-2 ml-1">
              <input
                type="date"
                value={fromDate}
                max={toDate || undefined}
                onChange={(e) => setFromDate(e.target.value)}
                className={selectCls}
                aria-label="From date"
              />
              <span className="text-xs text-slate-600">to</span>
              <input
                type="date"
                value={toDate}
                min={fromDate || undefined}
                onChange={(e) => setToDate(e.target.value)}
                className={selectCls}
                aria-label="To date"
              />
            </div>
          )}
          <span className="ml-auto text-xs font-medium text-slate-700">
            {pagination.total_items.toLocaleString('en-IN')} {pagination.total_items === 1 ? 'record' : 'records'}
          </span>
        </div>
      </div>

      {/* Table */}
      <DataTable
        columns={columns}
        data={logs}
        keyField="id"
        isLoading={isLoading}
        emptyMessage="No audit logs recorded matching this filter."
        pagination={{
          page: pagination.page,
          pageSize: pagination.page_size,
          totalItems: pagination.total_items,
          totalPages: pagination.total_pages,
          onPageChange: (newPage) => fetchLogs(newPage),
        }}
      />

      {/* Detail State Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="w-full max-w-2xl rounded-2xl bg-white border border-slate-200 p-6 shadow-2xl relative max-h-[85vh] flex flex-col">
            <div className="flex items-start justify-between pb-4 border-b border-slate-100">
              <div>
                <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-orange-50 text-orange-700 border border-orange-200">
                  {selectedLog.action_type}
                </span>
                <h3 className="text-base font-bold text-slate-900 mt-2">
                  Target: {selectedLog.entity_type} #{selectedLog.entity_id}
                </h3>
                <p className="text-xs text-slate-600 mt-0.5">
                  Logged {formatDateTimeIst(selectedLog.created_at)} by @{selectedLog.actor_username || selectedLog.actor_role}
                </p>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-slate-500 hover:text-slate-800 p-1 rounded-lg cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto mt-4 space-y-4 pr-1">
              {selectedLog.reason && (
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs">
                  <span className="font-bold text-slate-600 block mb-0.5">Audit Reason:</span>
                  <span className="text-slate-800">"{selectedLog.reason}"</span>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Previous State */}
                <div className="space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-rose-600 block">
                    Previous State
                  </span>
                  <pre className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700 overflow-x-auto max-h-60">
                    {selectedLog.old_value_json
                      ? JSON.stringify(selectedLog.old_value_json, null, 2)
                      : 'null'}
                  </pre>
                </div>

                {/* New State */}
                <div className="space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 block">
                    New State
                  </span>
                  <pre className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700 overflow-x-auto max-h-60">
                    {selectedLog.new_value_json
                      ? JSON.stringify(selectedLog.new_value_json, null, 2)
                      : 'null'}
                  </pre>
                </div>
              </div>

              {selectedLog.metadata_json && (
                <div className="space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-600 block">
                    Event Metadata
                  </span>
                  <pre className="p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700 overflow-x-auto max-h-36">
                    {JSON.stringify(selectedLog.metadata_json, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
