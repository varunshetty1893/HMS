import { apiClient } from './client';
import { User, UserRole, UserStatus } from '@/types/api';

export const staffApi = {
  listStaff: async (role?: UserRole, activeOnly = false): Promise<User[]> => {
    const params = new URLSearchParams();
    if (role) params.append('role', role);
    if (activeOnly) params.append('active_only', 'true');
    return apiClient<User[]>(`/admin/users?${params.toString()}`);
  },

  createStaff: async (payload: {
    username: string;
    full_name: string;
    password: string;
    role: UserRole;
  }): Promise<User> => {
    return apiClient<User>('/admin/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  updateStaff: async (
    userId: string,
    payload: Partial<{
      full_name: string;
      role: UserRole;
      status: UserStatus;
      is_active: boolean;
    }>
  ): Promise<User> => {
    return apiClient<User>(`/admin/users/${userId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  resetPassword: async (userId: string, newPassword: string): Promise<User> => {
    return apiClient<User>(`/admin/users/${userId}/reset-password`, {
      method: 'POST',
      body: JSON.stringify({ new_password: newPassword }),
    });
  },

  unlockStaff: async (userId: string): Promise<User> => {
    return apiClient<User>(`/admin/users/${userId}/unlock`, {
      method: 'POST',
    });
  },
};
