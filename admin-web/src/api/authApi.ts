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

  getMe: async (): Promise<User> => {
    return apiClient<User>('/auth/me');
  },
};
