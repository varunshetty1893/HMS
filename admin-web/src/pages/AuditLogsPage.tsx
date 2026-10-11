import React, { useEffect, useState } from 'react';
import { settingsAuditApi } from '@/api/settingsAuditApi';
import { formatDateTimeIst } from '@/utils/dateIst';
import { DataTable } from '@/components/common/DataTable';
import {
  Eye,
  RefreshCw,
  ShieldAlert,
  X,
} from 'lucide-react';
import { AuditLog, PaginationMeta } from '@/types/api';

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
  const [actionFilter, setActionFilter] = useState<string>('');
  const [roleFilter, setRoleFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Detail Modal for JSON snapshot inspection
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = async (page = 1) => {
    setIsLoading(true);
    try {
      const data = await settingsAuditApi.listAuditLogs({
        action_type: actionFilter || undefined,
        actor_role: roleFilter || undefined,
        page,
        page_size: 20,
      });
      setLogs(data.items);
      setPagination(data.pagination);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch audit records');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(1);
  }, [actionFilter, roleFilter]);

  const columns = [
    {
      key: 'created_at',
      header: 'Timestamp (IST)',
      render: (row: AuditLog) => (
        <span className="font-mono text-xs text-slate-300">
          {formatDateTimeIst(row.created_at)}
        </span>
      ),
    },
    {
      key: 'action_type',
      header: 'Action Event',
      render: (row: AuditLog) => (
        <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-indigo-950/70 text-indigo-300 border border-indigo-800/50">
          {row.action_type}
        </span>
      ),
    },
    {
      key: 'actor',
      header: 'Actor & Role',
      render: (row: AuditLog) => (
        <div className="text-xs">
          <span className="font-semibold text-white">@{row.actor_role}</span>
          {row.actor_user_id && (
            <span className="block text-[11px] font-mono text-slate-500">
              {row.actor_user_id.slice(0, 8)}...
            </span>
          )}
        </div>
      ),
    },
    {
      key: 'entity',
      header: 'Target Entity',
      render: (row: AuditLog) => (
        <div className="text-xs font-mono">
          <span className="text-slate-300 uppercase">{row.entity_type}</span>
          <span className="block text-[11px] text-slate-500">#{row.entity_id}</span>
        </div>
      ),
    },
    {
      key: 'reason',
      header: 'Audit Reason',
      render: (row: AuditLog) => (
        <span className="text-xs text-slate-400 italic">
          {row.reason ? `"${row.reason}"` : '—'}
        </span>
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
          className="p-1.5 rounded-lg text-indigo-400 hover:text-indigo-300 hover:bg-indigo-950/40 border border-transparent hover:border-indigo-800/50 transition cursor-pointer"
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
          <h1 className="text-2xl font-black tracking-tight text-white flex items-center gap-2.5">
            <ShieldAlert className="w-6 h-6 text-indigo-400" />
            <span>Immutable Audit Log Viewer</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Database trigger-protected chronological trace of all state mutations & overrides
          </p>
        </div>

        <button
          onClick={() => fetchLogs(pagination.page)}
          className="flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh Trace</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={actionFilter}
          onChange={(e) => setActionFilter(e.target.value)}
          className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none"
        >
          <option value="">All Action Types</option>
          <option value="PRICE_VARIANT_PRICE_CHANGED">PRICE_VARIANT_PRICE_CHANGED</option>
          <option value="QR_TOKEN_ROTATED">QR_TOKEN_ROTATED</option>
          <option value="STAFF_USER_CREATED">STAFF_USER_CREATED</option>
          <option value="STAFF_USER_UPDATED">STAFF_USER_UPDATED</option>
          <option value="STAFF_PASSWORD_RESET">STAFF_PASSWORD_RESET</option>
          <option value="RESTAURANT_SETTINGS_UPDATED">RESTAURANT_SETTINGS_UPDATED</option>
          <option value="ORDER_MODIFIED">ORDER_MODIFIED</option>
          <option value="ORDER_CANCELLED">ORDER_CANCELLED</option>
          <option value="BILL_GENERATED">BILL_GENERATED</option>
          <option value="BILL_DISCOUNT_APPLIED">BILL_DISCOUNT_APPLIED</option>
          <option value="BILL_VOIDED_FOR_REVISION">BILL_VOIDED_FOR_REVISION</option>
          <option value="PAYMENT_RECORDED">PAYMENT_RECORDED</option>
          <option value="SESSION_LIMIT_OVERRIDDEN">SESSION_LIMIT_OVERRIDDEN</option>
        </select>

        <select
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          className="px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-white focus:outline-none"
        >
          <option value="">All Actor Roles</option>
          <option value="ADMIN">ADMIN</option>
          <option value="WAITER">WAITER</option>
          <option value="KITCHEN">KITCHEN</option>
          <option value="CUSTOMER_SESSION">CUSTOMER_SESSION</option>
          <option value="SYSTEM">SYSTEM</option>
        </select>
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-xs">
          <div className="w-full max-w-2xl rounded-3xl bg-slate-900 border border-slate-800 p-6 shadow-2xl relative max-h-[85vh] flex flex-col">
            <div className="flex items-start justify-between pb-4 border-b border-slate-800">
              <div>
                <span className="px-2.5 py-1 rounded-full text-xs font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-800/50">
                  {selectedLog.action_type}
                </span>
                <h3 className="text-base font-bold text-white mt-2">
                  Target: {selectedLog.entity_type} #{selectedLog.entity_id}
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Logged {formatDateTimeIst(selectedLog.created_at)} by @{selectedLog.actor_role}
                </p>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto mt-4 space-y-4 pr-1">
              {selectedLog.reason && (
                <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-xs">
                  <span className="font-bold text-slate-400 block mb-0.5">Audit Reason:</span>
                  <span className="text-slate-200">"{selectedLog.reason}"</span>
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Previous State */}
                <div className="space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-rose-400 block">
                    Previous State
                  </span>
                  <pre className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-60">
                    {selectedLog.old_value_json
                      ? JSON.stringify(selectedLog.old_value_json, null, 2)
                      : 'null'}
                  </pre>
                </div>

                {/* New State */}
                <div className="space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 block">
                    New State
                  </span>
                  <pre className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-60">
                    {selectedLog.new_value_json
                      ? JSON.stringify(selectedLog.new_value_json, null, 2)
                      : 'null'}
                  </pre>
                </div>
              </div>

              {selectedLog.metadata_json && (
                <div className="space-y-1.5">
                  <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block">
                    Event Metadata
                  </span>
                  <pre className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-xs font-mono text-slate-400 overflow-x-auto max-h-36">
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
