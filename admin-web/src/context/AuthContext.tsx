import React, { createContext, useContext, useEffect, useState } from 'react';
import { authApi } from '@/api/authApi';
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
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('hms_admin_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem('hms_admin_access_token');
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem('hms_admin_access_token');
      if (storedToken) {
        try {
          const me = await authApi.getMe();
          if (me.role !== 'ADMIN') {
            throw new Error('Access denied: ADMIN role required.');
          }
          setUser(me);
          localStorage.setItem('hms_admin_user', JSON.stringify(me));
          adminWs.connect();
        } catch {
          // Token invalid or non-admin
          setUser(null);
          setToken(null);
          localStorage.removeItem('hms_admin_access_token');
          localStorage.removeItem('hms_admin_refresh_token');
          localStorage.removeItem('hms_admin_user');
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

    localStorage.setItem('hms_admin_access_token', tokens.access_token);
    localStorage.setItem('hms_admin_refresh_token', tokens.refresh_token);
    localStorage.setItem('hms_admin_user', JSON.stringify(tokens.user));

    setToken(tokens.access_token);
    setUser(tokens.user);
    adminWs.connect();
  };

  const logout = async () => {
    const refreshToken = localStorage.getItem('hms_admin_refresh_token');

    // Immediately clear credentials and state so logout is instantaneous
    localStorage.removeItem('hms_admin_access_token');
    localStorage.removeItem('hms_admin_refresh_token');
    localStorage.removeItem('hms_admin_user');

    setToken(null);
    setUser(null);
    adminWs.disconnect();

    // Revoke token in background without blocking UI
    if (refreshToken) {
      authApi.logout(refreshToken).catch(() => {});
    }
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
