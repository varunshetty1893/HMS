import React, { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '@/api/authApi';
import {
  authCookieMode,
  clearSession,
  getAccessToken,
  getRefreshToken,
  getStoredUser,
  refreshSession,
  saveSession,
} from '@/auth/session';
import { adminWs } from '@/realtime/adminWs';
import { User } from '@/types/api';

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => getStoredUser<User>());
  const [token, setToken] = useState<string | null>(() => getAccessToken());
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      // Cookie mode: the access token only lives in memory, so after a reload ask the backend
      // for a fresh one using the httpOnly refresh cookie (no cookie => stay logged out).
      if (authCookieMode && !getAccessToken()) {
        await refreshSession();
      }
      const storedToken = getAccessToken();
      if (storedToken) {
        try {
          const me = await authApi.getMe();
          if (me.role !== 'ADMIN') {
            throw new Error('Access denied: ADMIN role required.');
          }
          setUser(me);
          setToken(getAccessToken());
          saveSession({ access_token: getAccessToken() ?? storedToken, user: me });
          adminWs.connect();
        } catch {
          // Token invalid or non-admin
          setUser(null);
          setToken(null);
          clearSession();
          adminWs.disconnect();
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username: string, password: string) => {
    const tokens = await authApi.login(username, password);
    if (tokens.user.role !== 'ADMIN') {
      throw new Error('Access denied: Only ADMIN role can access this portal.');
    }

    saveSession({
      access_token: tokens.access_token,
      refresh_token: tokens.refresh_token,
      user: tokens.user,
    });

    setToken(tokens.access_token);
    setUser(tokens.user);
    adminWs.connect();
  };

  const logout = async () => {
    // Start revoking first so the request still carries the access token / refresh cookie,
    // then clear credentials and state immediately so logout feels instant.
    const revoke = authApi.logout(getRefreshToken() || undefined);
    clearSession();

    setToken(null);
    setUser(null);
    adminWs.disconnect();

    revoke.catch(() => {});
  };

  return (
    <AuthContext.Provider value={{ user, token, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
