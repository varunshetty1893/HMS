import React, { useState } from 'react';
import { useAuth } from '@/context/AuthContext';
import { Lock, User as UserIcon } from 'lucide-react';

interface LoginPageProps {
  onSuccess: () => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onSuccess }) => {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
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
      className="min-h-screen w-full flex items-center justify-center p-4"
      style={{
        background: 'linear-gradient(135deg, #FFF8ED 0%, #FDF3E3 50%, #FAF0DF 100%)',
      }}
    >
      <div
        className="w-full max-w-md rounded-3xl p-8 sm:p-10 shadow-2xl transition-all"
        style={{
          background: '#FFFFFF',
          border: '1px solid #F2E7D5',
          boxShadow: '0 20px 40px -15px rgba(217, 93, 43, 0.12), 0 0 0 1px rgba(242, 231, 213, 0.8)',
        }}
      >
        {/* Brand Header */}
        <div className="text-center mb-8">
          <img
            src="/logo.png"
            alt="Spice Hub Family Restaurant"
            className="mx-auto w-28 h-28 mb-3 drop-shadow-lg"
          />
          <h1 className="text-2xl font-black tracking-tight" style={{ color: '#282820' }}>
            Admin Portal
          </h1>
          <p className="text-sm mt-1.5 font-medium" style={{ color: '#7A7568' }}>
            Spice Hub Family Restaurant • Control Panel
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            className="mb-6 p-4 rounded-2xl text-xs font-semibold flex items-center gap-2"
            style={{
              background: '#FEF2F2',
              color: '#B91C1C',
              border: '1px solid #FCA5A5',
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
              style={{ color: '#57534E' }}
            >
              Username
            </label>
            <div className="relative">
              <UserIcon className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: '#9CA3AF' }} />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                autoComplete="username"
                required
                className="w-full pl-11 pr-4 py-3 rounded-xl text-sm transition outline-none"
                style={{
                  background: '#FFFDF9',
                  border: '1.5px solid #F2E7D5',
                  color: '#282820',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = '#D95D2B';
                  e.currentTarget.style.boxShadow = '0 0 0 3px rgba(217, 93, 43, 0.15)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = '#F2E7D5';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              />
            </div>
          </div>

          <div>
            <label
              className="block text-xs font-bold uppercase tracking-wider mb-1.5"
              style={{ color: '#57534E' }}
            >
              Password
            </label>
            <div className="relative">
              <Lock className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: '#9CA3AF' }} />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                autoComplete="current-password"
                required
                className="w-full pl-11 pr-4 py-3 rounded-xl text-sm transition outline-none"
                style={{
                  background: '#FFFDF9',
                  border: '1.5px solid #F2E7D5',
                  color: '#282820',
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = '#D95D2B';
                  e.currentTarget.style.boxShadow = '0 0 0 3px rgba(217, 93, 43, 0.15)';
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = '#F2E7D5';
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
              background: '#D95D2B',
              boxShadow: '0 8px 18px -4px rgba(217, 93, 43, 0.4)',
              opacity: isLoading ? 0.7 : 1,
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#C84E1D')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#D95D2B')}
          >
            {isLoading ? 'Authenticating...' : 'Sign In to Dashboard'}
          </button>
        </form>

        {/* Staff Credentials Helper Card */}
        <div
          className="mt-6 p-3.5 rounded-2xl text-xs flex flex-col gap-1"
          style={{
            background: '#FFFDF9',
            border: '1px dashed #E5D9C5',
            color: '#7A7568',
          }}
        >
          <div className="flex items-center justify-between font-semibold" style={{ color: '#282820' }}>
            <span>🔑 Staff Account Access:</span>
            <span className="px-2 py-0.5 rounded-md font-mono text-[11px]" style={{ background: '#FDF1EB', color: '#D95D2B' }}>
              ADMIN
            </span>
          </div>
          <div className="flex items-center justify-between font-mono text-[11px] pt-1">
            <span>Username: <strong style={{ color: '#282820' }}>admin</strong></span>
            <span>Password: <strong style={{ color: '#282820' }}>AdminPass123!</strong></span>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t text-center" style={{ borderColor: '#F2E7D5' }}>
          <p className="text-xs" style={{ color: '#A8A29E' }}>
            Staff access only • 5 failed attempts trigger 15-minute lock
          </p>
        </div>
      </div>
    </div>
  );
};
