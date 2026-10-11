import { apiClient } from './client';
import { AuditLogPageResponse, RestaurantSettings } from '@/types/api';

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

  listAuditLogs: async (filters: {
    action_type?: string;
    entity_type?: string;
    entity_id?: string;
    actor_role?: string;
    from?: string;
    to?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<AuditLogPageResponse> => {
    const params = new URLSearchParams();
    if (filters.action_type) params.append('action_type', filters.action_type);
    if (filters.entity_type) params.append('entity_type', filters.entity_type);
    if (filters.entity_id) params.append('entity_id', filters.entity_id);
    if (filters.actor_role) params.append('actor_role', filters.actor_role);
    if (filters.from) params.append('from', filters.from);
    if (filters.to) params.append('to', filters.to);
    if (filters.page) params.append('page', String(filters.page));
    if (filters.page_size) params.append('page_size', String(filters.page_size));

    return apiClient<AuditLogPageResponse>(`/admin/audit-logs?${params.toString()}`);
  },
};
