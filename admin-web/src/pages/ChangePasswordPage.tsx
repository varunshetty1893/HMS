import React, { useState } from 'react';
import { KeyRound, Lock, CheckCircle2 } from 'lucide-react';
import { authApi } from '@/api/authApi';
import { useAuth } from '@/context/AuthContext';

const MIN_LENGTH = 8;

const inputClass =
  'w-full pl-11 pr-4 py-3 rounded-xl text-sm bg-white border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition';

export const ChangePasswordPage: React.FC = () => {
  const { logout } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (next.length < MIN_LENGTH) return setError(`New password must be at least ${MIN_LENGTH} characters.`);
    if (next !== confirm) return setError('New password and confirmation do not match.');
    if (next === current) return setError('New password must be different from the current one.');

    setBusy(true);
    try {
      await authApi.changePassword(current, next);
      setDone(true);
      // Every session of this admin is revoked by the server; sign in again with the new password.
      setTimeout(() => void logout(), 2000);
    } catch (err: any) {
      setError(err?.message || 'Could not change password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="p-6 max-w-lg">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-brand-100">
          <KeyRound className="w-5 h-5 text-brand-600" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-900">Change Password</h2>
          <p className="text-sm text-gray-500">You will be signed out everywhere after changing it.</p>
        </div>
      </div>

      {done ? (
        <div className="p-5 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-800 flex items-center gap-3">
          <CheckCircle2 className="w-6 h-6 shrink-0" />
          <div className="text-sm font-semibold">Password changed. Signing you out — please log in with the new password.</div>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4 p-6 rounded-2xl bg-white border border-gray-200 shadow-sm">
          {error && (
            <div className="p-3 rounded-xl text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
              ⚠️ {error}
            </div>
          )}
          {[
            { label: 'Current password', value: current, set: setCurrent, auto: 'current-password' },
            { label: 'New password', value: next, set: setNext, auto: 'new-password' },
            { label: 'Confirm new password', value: confirm, set: setConfirm, auto: 'new-password' },
          ].map((f) => (
            <div key={f.label}>
              <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5 text-gray-700">
                {f.label}
              </label>
              <div className="relative">
                <Lock className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="password"
                  value={f.value}
                  onChange={(e) => f.set(e.target.value)}
                  autoComplete={f.auto}
                  required
                  className={inputClass}
                />
              </div>
            </div>
          ))}
          <p className="text-xs text-gray-500">Minimum {MIN_LENGTH} characters.</p>
          <button
            type="submit"
            disabled={busy}
            className="w-full py-3 rounded-xl text-sm font-bold text-white bg-brand-600 hover:bg-brand-500 shadow-sm transition cursor-pointer disabled:opacity-70"
          >
            {busy ? 'Updating...' : 'Update Password'}
          </button>
        </form>
      )}
    </div>
  );
};

export default ChangePasswordPage;
