import { apiClient } from './client';
import { MenuCategory, MenuItem, MenuPriceVariant } from '@/types/api';

export const menuApi = {
  listCategories: async (activeOnly = false): Promise<MenuCategory[]> => {
    return apiClient<MenuCategory[]>(`/admin/menu/categories?active_only=${activeOnly}`);
  },

  createCategory: async (payload: {
    name: string;
    description?: string | null;
    display_order?: number;
    is_active?: boolean;
  }): Promise<MenuCategory> => {
    return apiClient<MenuCategory>('/admin/menu/categories', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateCategory: async (
    categoryId: string,
    payload: Partial<{
      name: string;
      description: string | null;
      display_order: number;
      is_active: boolean;
    }>
  ): Promise<MenuCategory> => {
    return apiClient<MenuCategory>(`/admin/menu/categories/${categoryId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  deleteCategory: async (categoryId: string): Promise<void> => {
    return apiClient<void>(`/admin/menu/categories/${categoryId}`, {
      method: 'DELETE',
    });
  },

  reorderCategories: async (categories: { id: string; display_order: number }[]): Promise<{ status: string }> => {
    return apiClient<{ status: string }>('/admin/menu/categories/reorder', {
      method: 'PUT',
      body: JSON.stringify({ categories }),
    });
  },

  listItems: async (categoryId?: string, activeOnly = false): Promise<MenuItem[]> => {
    const params = new URLSearchParams();
    if (categoryId) params.append('category_id', categoryId);
    if (activeOnly) params.append('active_only', 'true');
    return apiClient<MenuItem[]>(`/admin/menu/items?${params.toString()}`);
  },

  createItem: async (payload: any): Promise<MenuItem> => {
    return apiClient<MenuItem>('/admin/menu/items', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  reorderItems: async (items: { id: string; display_order: number }[]): Promise<{ status: string }> => {
    return apiClient<{ status: string }>('/admin/menu/items/reorder', {
      method: 'PUT',
      body: JSON.stringify({ items }),
    });
  },

  updateItem: async (itemId: string, payload: any): Promise<MenuItem> => {
    return apiClient<MenuItem>(`/admin/menu/items/${itemId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  setItemAvailability: async (
    itemId: string,
    isAvailable: boolean,
    reason?: string
  ): Promise<MenuItem> => {
    return apiClient<MenuItem>(`/admin/menu/items/${itemId}/availability`, {
      method: 'PATCH',
      body: JSON.stringify({ is_available: isAvailable, reason: reason || null }),
    });
  },

  createVariant: async (itemId: string, payload: any): Promise<MenuPriceVariant> => {
    return apiClient<MenuPriceVariant>(`/admin/menu/items/${itemId}/variants`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateVariant: async (variantId: string, payload: any): Promise<MenuPriceVariant> => {
    return apiClient<MenuPriceVariant>(`/admin/menu/variants/${variantId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  uploadImage: async (itemId: string, file: File): Promise<MenuItem> => {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient<MenuItem>(`/admin/menu/items/${itemId}/image`, {
      method: 'POST',
      body: formData,
    });
  },

  deleteImage: async (itemId: string): Promise<void> => {
    return apiClient<void>(`/admin/menu/items/${itemId}/image`, {
      method: 'DELETE',
    });
  },
};
