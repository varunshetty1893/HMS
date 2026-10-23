import React, { useState } from 'react';
import { ArrowLeft, KeyRound, Lock, User as UserIcon } from 'lucide-react';
import { authApi } from '@/api/authApi';

interface ForgotPasswordPageProps {
  onBack: (message?: string) => void;
}

const MIN_LENGTH = 8;

const inputClass =
  'w-full pl-11 pr-4 py-3 rounded-xl text-sm bg-white border border-gray-300 text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition';

/** Break-glass reset for a locked-out admin: needs the ADMIN_RECOVERY_KEY set on the server. */
export const ForgotPasswordPage: React.FC<ForgotPasswordPageProps> = ({ onBack }) => {
  const [username, setUsername] = useState('');
  const [recoveryKey, setRecoveryKey] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (next.length < MIN_LENGTH) return setError(`New password must be at least ${MIN_LENGTH} characters.`);
    if (next !== confirm) return setError('New password and confirmation do not match.');

    setBusy(true);
    try {
      await authApi.recoveryReset(username.trim(), recoveryKey.trim(), next);
      onBack('Password reset. Please sign in with your new password.');
    } catch (err: any) {
      setError(err?.message || 'Could not reset password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex items-center justify-center p-4 bg-slate-50">
      <div className="w-full max-w-md rounded-2xl p-8 sm:p-10 shadow-lg bg-white border border-gray-200">
        <button
          type="button"
          onClick={() => onBack()}
          className="flex items-center gap-1.5 text-xs font-semibold text-gray-500 hover:text-gray-800 mb-5 cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" /> Back to sign in
        </button>
        <div className="text-center mb-6">
          <div className="mx-auto w-14 h-14 rounded-full flex items-center justify-center bg-brand-100 mb-3">
            <KeyRound className="w-7 h-7 text-brand-600" />
          </div>
          <h1 className="text-xl font-bold text-gray-900">Reset Admin Password</h1>
          <p className="text-xs mt-1 text-gray-500">
            Enter the recovery key from your server settings (ADMIN_RECOVERY_KEY).
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            ⚠️ {error}
          </div>
        )}

        <form onSubmit={submit} className="space-y-4">
          <div className="relative">
            <UserIcon className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input className={inputClass} placeholder="Admin username" value={username}
              onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
          </div>
          <div className="relative">
            <KeyRound className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input className={inputClass} type="password" placeholder="Recovery key" value={recoveryKey}
              onChange={(e) => setRecoveryKey(e.target.value)} autoComplete="off" required />
          </div>
          <div className="relative">
            <Lock className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input className={inputClass} type="password" placeholder={`New password (min ${MIN_LENGTH})`} value={next}
              onChange={(e) => setNext(e.target.value)} autoComplete="new-password" required />
          </div>
          <div className="relative">
            <Lock className="w-5 h-5 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
            <input className={inputClass} type="password" placeholder="Confirm new password" value={confirm}
              onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" required />
          </div>
          <button
            type="submit"
            disabled={busy}
            className="w-full py-3.5 rounded-xl text-sm font-bold text-white bg-brand-600 hover:bg-brand-500 shadow-sm transition cursor-pointer disabled:opacity-70"
          >
            {busy ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ForgotPasswordPage;
