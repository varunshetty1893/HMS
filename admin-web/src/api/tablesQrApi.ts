import { apiClient } from './client';
import {
  QrPrintCardResponse,
  QrRegenerateResponse,
  RestaurantTable,
} from '@/types/api';

export const tablesQrApi = {
  listTables: async (activeOnly = false, floor?: string): Promise<RestaurantTable[]> => {
    const params = new URLSearchParams();
    if (activeOnly) params.append('active_only', 'true');
    if (floor) params.append('floor_or_zone', floor);
    return apiClient<RestaurantTable[]>(`/admin/tables?${params.toString()}`);
  },

  createTable: async (payload: {
    table_number: number;
    display_name: string;
    seating_capacity?: number | null;
    floor_or_zone?: string | null;
  }): Promise<RestaurantTable> => {
    return apiClient<RestaurantTable>('/admin/tables', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateTable: async (
    tableId: string,
    payload: Partial<{
      table_number: number;
      display_name: string;
      seating_capacity: number | null;
      floor_or_zone: string | null;
      operational_status: string;
      is_active: boolean;
    }>
  ): Promise<RestaurantTable> => {
    return apiClient<RestaurantTable>(`/admin/tables/${tableId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  regenerateQr: async (
    tableId: string,
    reason: string = 'ROTATED_BY_ADMIN'
  ): Promise<QrRegenerateResponse> => {
    return apiClient<QrRegenerateResponse>(`/admin/tables/${tableId}/qr/regenerate`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  },

  getPrintableQrCard: async (tableId: string): Promise<QrPrintCardResponse> => {
    return apiClient<QrPrintCardResponse>(`/admin/tables/${tableId}/qr-print`);
  },
};
