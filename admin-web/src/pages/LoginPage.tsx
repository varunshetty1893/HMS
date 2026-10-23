import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Lock, User as UserIcon } from 'lucide-react';
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage';
import { isDevDemoEnabled, purgeAdminMockStorageIfProduction } from '@/utils/env';

interface LoginPageProps {
  onSuccess: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onSuccess }) => {
  const { login } = useAuth();

  const [username, setUsername] = useState(() => (isDevDemoEnabled() ? 'admin' : ''));
  const [password, setPassword] = useState(() => (isDevDemoEnabled() ? 'AdminPass123!' : ''));
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showForgot, setShowForgot] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    purgeAdminMockStorageIfProduction();
  }, []);

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

  if (showForgot) {
    return (
      <ForgotPasswordPage
        onBack={(message) => {
          setShowForgot(false);
          if (message) {
            setNotice(message);
            setError(null);
          }
        }}
      />
    );
  }

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-slate-50">
      <div className="w-full max-w-md rounded-2xl p-8 sm:p-10 shadow-lg bg-white border border-gray-200">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <img
            src="/logo.png"
            alt="Spice Hub Family Restaurant"
            className="mx-auto w-20 h-20 mb-3 rounded-full shadow-sm"
          />
          <h1 className="text-2xl font-bold tracking-tight text-gray-900">
            Admin Portal
          </h1>
          <p className="text-sm mt-1 text-gray-500 font-medium">
            Spice Hub Family Restaurant • Control Panel
          </p>
        </div>

        {notice && (
          <div className="mb-6 p-4 rounded-xl text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            {notice}
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 rounded-xl text-xs font-semibold flex items-center gap-2 bg-rose-50 text-rose-700 border border-rose-200">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5 text-gray-700">
              Username
            </label>
            <div className="relative">
              <UserIcon className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                autoComplete="username"
                required
                className="w-full pl-11 pr-4 py-3 rounded-xl text-sm bg-white border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5 text-gray-700">
              Password
            </label>
            <div className="relative">
              <Lock className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                className="w-full pl-11 pr-4 py-3 rounded-xl text-sm bg-white border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full mt-2 py-3.5 px-4 rounded-xl text-sm font-bold text-white bg-brand-600 hover:bg-brand-500 shadow-sm transition cursor-pointer flex items-center justify-center gap-2 active:scale-[0.99] disabled:opacity-70"
          >
            {isLoading ? 'Authenticating...' : 'Sign In to Dashboard'}
          </button>
          <div className="text-center">
            <button
              type="button"
              onClick={() => setShowForgot(true)}
              className="text-xs font-semibold text-brand-600 hover:text-brand-500 cursor-pointer"
            >
              Forgot password?
            </button>
          </div>
        </form>

        {/* Staff Credentials Helper Card (Omitted in Production) */}
        {isDevDemoEnabled() && (
          <div className="mt-6 p-4 rounded-xl text-xs bg-slate-50 border border-dashed border-gray-300 text-gray-600 flex flex-col gap-1.5">
            <div className="flex items-center justify-between font-semibold text-gray-800">
              <span>🔑 [DEV ONLY] Staff Account Access:</span>
              <button
                type="button"
                onClick={() => {
                  setUsername('admin');
                  setPassword('AdminPass123!');
                }}
                className="px-2 py-0.5 rounded-md text-[11px] bg-brand-100 hover:bg-brand-200 text-brand-700 font-bold transition cursor-pointer"
              >
                Auto-Fill
              </button>
            </div>
            <div className="flex items-center justify-between font-mono text-[11px] pt-1">
              <span>
                Username: <strong className="text-gray-900 font-bold">admin</strong>
              </span>
              <span>
                Password: <strong className="text-gray-900 font-bold">AdminPass123!</strong>
              </span>
            </div>
          </div>
        )}

        <div className="mt-6 pt-4 border-t border-gray-200 text-center">
          <p className="text-xs text-gray-400">
            Staff access only • 5 failed attempts trigger 15-minute lock
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
