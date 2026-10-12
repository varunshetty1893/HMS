import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { Lock, User as UserIcon } from 'lucide-react';

interface LoginPageProps {
  onSuccess: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onSuccess }) => {
  const { login } = useAuth();
  const { theme } = useTheme();
  const isLight = theme === 'light';

  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('AdminPass123!');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setError('Username and password are required');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await login(username.trim(), password);
      onSuccess();
    } catch (err: any) {
      setError(err?.message || 'Login failed. Please check credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen w-full flex items-center justify-center p-4 transition-colors duration-200"
      style={{
        backgroundColor: isLight ? '#f5f0e8' : '#020617',
        backgroundImage: isLight
          ? 'radial-gradient(circle at 50% 20%, #FFF8ED 0%, #f5f0e8 100%)'
          : 'radial-gradient(circle at 50% 20%, #0f172a 0%, #020617 100%)',
      }}
    >
      <div
        className="w-full max-w-md rounded-3xl p-8 sm:p-10 shadow-2xl transition-all"
        style={{
          backgroundColor: isLight ? '#ffffff' : '#0f172a',
          borderColor: isLight ? '#e4d9c8' : '#334155',
          borderWidth: 1,
          borderStyle: 'solid',
          boxShadow: isLight
            ? '0 20px 40px -15px rgba(217, 93, 43, 0.12), 0 0 0 1px rgba(228, 217, 200, 0.8)'
            : '0 25px 50px -12px rgba(0, 0, 0, 0.7), 0 0 0 1px rgba(51, 65, 85, 0.5)',
        }}
      >
        {/* Brand Header */}
        <div className="text-center mb-8">
          <img
            src="/logo.png"
            alt="Spice Hub Family Restaurant"
            className="mx-auto w-24 h-24 mb-3 drop-shadow-xl rounded-full"
          />
          <h1
            className="text-2xl font-black tracking-tight"
            style={{ color: isLight ? '#282820' : '#f8fafc' }}
          >
            Admin Portal
          </h1>
          <p
            className="text-sm mt-1.5 font-medium"
            style={{ color: isLight ? '#756a56' : '#94a3b8' }}
          >
            Spice Hub Family Restaurant • Control Panel
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            className="mb-6 p-4 rounded-2xl text-xs font-semibold flex items-center gap-2"
            style={{
              backgroundColor: isLight ? '#fee2e2' : '#450a0a',
              color: isLight ? '#b91c1c' : '#f87171',
              borderColor: isLight ? '#fca5a5' : '#7f1d1d',
              borderWidth: 1,
              borderStyle: 'solid',
            }}
          >
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              className="block text-xs font-bold uppercase tracking-wider mb-1.5"
              style={{ color: isLight ? '#5a5545' : '#94a3b8' }}
            >
              Username
            </label>
            <div className="relative">
              <UserIcon
                className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2"
                style={{ color: isLight ? '#94a3b8' : '#64748b' }}
              />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                autoComplete="username"
                required
                className="w-full pl-11 pr-4 py-3 rounded-xl text-sm transition outline-none"
                style={{
                  backgroundColor: isLight ? '#faf7f2' : '#020617',
                  borderColor: isLight ? '#e4d9c8' : '#334155',
                  borderWidth: 1.5,
                  borderStyle: 'solid',
                  color: isLight ? '#282820' : '#f8fafc',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = '#D95D2B';
                  e.currentTarget.style.boxShadow = '0 0 0 3px rgba(217, 93, 43, 0.2)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = isLight ? '#e4d9c8' : '#334155';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </div>
          </div>

          <div>
            <label
              className="block text-xs font-bold uppercase tracking-wider mb-1.5"
              style={{ color: isLight ? '#5a5545' : '#94a3b8' }}
            >
              Password
            </label>
            <div className="relative">
              <Lock
                className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2"
                style={{ color: isLight ? '#94a3b8' : '#64748b' }}
              />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                className="w-full pl-11 pr-4 py-3 rounded-xl text-sm transition outline-none"
                style={{
                  backgroundColor: isLight ? '#faf7f2' : '#020617',
                  borderColor: isLight ? '#e4d9c8' : '#334155',
                  borderWidth: 1.5,
                  borderStyle: 'solid',
                  color: isLight ? '#282820' : '#f8fafc',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = '#D95D2B';
                  e.currentTarget.style.boxShadow = '0 0 0 3px rgba(217, 93, 43, 0.2)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = isLight ? '#e4d9c8' : '#334155';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 py-3.5 px-4 rounded-xl text-sm font-bold text-white transition cursor-pointer flex items-center justify-center gap-2 active:scale-[0.99]"
            style={{
              backgroundColor: '#D95D2B',
              boxShadow: '0 8px 20px -4px rgba(217, 93, 43, 0.5)',
              opacity: isLoading ? 0.7 : 1,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#EB7444')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#D95D2B')}
          >
            {isLoading ? 'Authenticating...' : 'Sign In to Dashboard'}
          </button>
        </form>

        {/* Staff Credentials Helper Card */}
        <div
          className="mt-6 p-4 rounded-2xl text-xs flex flex-col gap-1.5"
          style={{
            backgroundColor: isLight ? '#faf7f2' : '#020617',
            borderColor: isLight ? '#e4d9c8' : '#1e293b',
            borderWidth: 1,
            borderStyle: 'dashed',
            color: isLight ? '#756a56' : '#94a3b8',
          }}
        >
          <div
            className="flex items-center justify-between font-semibold"
            style={{ color: isLight ? '#282820' : '#f8fafc' }}
          >
            <span>🔑 Staff Account Access:</span>
            <span
              className="px-2 py-0.5 rounded-md font-mono text-[11px]"
              style={{
                backgroundColor: isLight ? '#ffedd5' : '#431407',
                color: '#D95D2B',
              }}
            >
              ADMIN
            </span>
          </div>
          <div className="flex items-center justify-between font-mono text-[11px] pt-1">
            <span>
              Username: <strong style={{ color: isLight ? '#282820' : '#f8fafc' }}>admin</strong>
            </span>
            <span>
              Password: <strong style={{ color: isLight ? '#282820' : '#f8fafc' }}>AdminPass123!</strong>
            </span>
          </div>
        </div>

        <div
          className="mt-6 pt-4 border-t text-center"
          style={{ borderColor: isLight ? '#e4d9c8' : '#1e293b' }}
        >
          <p className="text-xs" style={{ color: isLight ? '#8a7e69' : '#64748b' }}>
            Staff access only • 5 failed attempts trigger 15-minute lock
          </p>
        </div>
      </div>
    </div>
  );
};
