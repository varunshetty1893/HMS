import { apiClient } from './client';
import { AuditLogFacets, AuditLogPageResponse, RestaurantSettings } from '@/types/api';

export interface AuditLogFilters {
  action_type?: string;
  entity_type?: string;
  entity_id?: string;
  actor_role?: string;
  q?: string;
  from?: string;
  to?: string;
  page?: number;
  page_size?: number;
}

function auditParams(filters: AuditLogFilters): URLSearchParams {
  const params = new URLSearchParams();
  (Object.entries(filters) as [string, string | number | undefined][]).forEach(([k, v]) => {
    if (v !== undefined && v !== '') params.append(k, String(v));
  });
  return params;
}

export const settingsAuditApi = {
  getSettings: async (): Promise<RestaurantSettings> => {
    return apiClient<RestaurantSettings>('/admin/settings');
  },

  updateSettings: async (payload: Partial<RestaurantSettings>): Promise<RestaurantSettings> => {
    return apiClient<RestaurantSettings>('/admin/settings', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  listAuditLogs: async (filters: AuditLogFilters = {}): Promise<AuditLogPageResponse> => {
    return apiClient<AuditLogPageResponse>(`/admin/audit-logs?${auditParams(filters).toString()}`);
  },

  getAuditFacets: async (): Promise<AuditLogFacets> => {
    return apiClient<AuditLogFacets>('/admin/audit-logs/facets');
  },

  /** Downloads ALL entries matching the filters (server-side, not just the visible page). */
  exportAuditLogsXlsx: async (filters: AuditLogFilters = {}): Promise<Blob> => {
    const { page: _p, page_size: _ps, ...rest } = filters;
    return apiClient<Blob>(`/admin/audit-logs/export.xlsx?${auditParams(rest).toString()}`);
  },
};
