import { apiClient } from './client';
import { AuthTokens, User } from '@/types/api';

export const authApi = {
  login: async (username: string, password: string): Promise<AuthTokens> => {
    return apiClient<AuthTokens>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },

  logout: async (refreshToken?: string): Promise<void> => {
    try {
      await apiClient<void>('/auth/logout', {
        method: 'POST',
        body: JSON.stringify({ refresh_token: refreshToken || null }),
      });
    } catch {
      // Ignored on logout
    }
  },

  changePassword: async (currentPassword: string, newPassword: string): Promise<void> => {
    await apiClient<{ status: string }>('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    });
  },

  recoveryReset: async (username: string, recoveryKey: string, newPassword: string): Promise<void> => {
    await apiClient<{ status: string }>('/auth/admin-recovery-reset', {
      method: 'POST',
      body: JSON.stringify({ username, recovery_key: recoveryKey, new_password: newPassword }),
    });
  },

  getMe: async (): Promise<User> => {
    return apiClient<User>('/auth/me');
  },
};
