import React, { useEffect, useState } from 'react';
import { staffApi } from '@/api/staffApi';
import { formatDateTimeIst } from '@/utils/dateIst';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ConfirmModal } from '@/components/common/ConfirmModal';
import {
  Eye,
  EyeOff,
  KeyRound,
  Plus,
  Unlock,
  UserCheck,
  UserX,
  X,
} from 'lucide-react';
import { User, UserRole } from '@/types/api';
import { usePageTheme } from '@/hooks/usePageTheme';
import { useAuth } from '@/context/AuthContext';

export const StaffManagementPage: React.FC = () => {
  const { L, heading, sub, muted, border, tableWrap, thead, tbodyRow, tbodyRowHover, tabInactive, card } = usePageTheme();
  const { user: currentUser } = useAuth();
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [staffList, setStaffList] = useState<User[]>([]);
  const [roleFilter, setRoleFilter] = useState<string>('ALL');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Staff Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<UserRole>('WAITER');

  // Reset Password Modal
  const [resetTargetUser, setResetTargetUser] = useState<User | null>(null);
  const [newResetPassword, setNewResetPassword] = useState('');

  // Deactivate User Confirmation
  const [userToDeactivate, setUserToDeactivate] = useState<User | null>(null);

  const fetchStaff = async () => {
    setIsLoading(true);
    try {
      const data = await staffApi.listStaff(
        roleFilter === 'ALL' ? undefined : (roleFilter as UserRole),
        false
      );
      setStaffList(data);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch staff accounts');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStaff();
  }, [roleFilter]);

  const handleCreateStaff = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUsername.trim() || !newFullName.trim() || !newPassword) return;

    try {
      await staffApi.createStaff({
        username: newUsername.trim(),
        full_name: newFullName.trim(),
        password: newPassword,
        role: newRole,
      });
      setIsCreateOpen(false);
      setShowNewPassword(false);
      setNewUsername('');
      setNewFullName('');
      setNewPassword('');
      fetchStaff();
    } catch (err: any) {
      alert(err?.message || 'Failed to create staff account');
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetTargetUser || !newResetPassword) return;

    try {
      await staffApi.resetPassword(resetTargetUser.id, newResetPassword);
      alert(`Password updated for @${resetTargetUser.username}. Existing sessions have been terminated.`);
      setResetTargetUser(null);
      setNewResetPassword('');
      setShowResetPassword(false);
      fetchStaff();
    } catch (err: any) {
      alert(err?.message || 'Failed to reset password');
    }
  };

  const handleUnlockUser = async (user: User) => {
    try {
      await staffApi.unlockStaff(user.id);
      alert(`Account @${user.username} unlocked successfully.`);
      fetchStaff();
    } catch (err: any) {
      alert(err?.message || 'Failed to unlock staff account');
    }
  };

  const handleToggleDeactivate = async () => {
    if (!userToDeactivate) return;
    try {
      const newActive = !userToDeactivate.is_active;
      await staffApi.updateStaff(userToDeactivate.id, {
        is_active: newActive,
        status: newActive ? 'ACTIVE' : 'DISABLED',
      });
      setUserToDeactivate(null);
      fetchStaff();
    } catch (err: any) {
      alert(err?.message || 'Failed to update account status');
    }
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight" style={{ color: heading }}>Staff Account Administration</h1>
          <p className="text-sm mt-1" style={{ color: sub }}>
            Waiters, Kitchen and Admin credentials, session revocation, and lockout management
          </p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-600/30 transition cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>New Staff Member</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
          {error}
        </div>
      )}

      {/* Role Filter */}
      <div className="flex items-center gap-2">
        {['ALL', 'WAITER', 'KITCHEN', 'ADMIN'].map((r) => (
          <button
            key={r}
            onClick={() => setRoleFilter(r)}
            className="px-3.5 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer"
            style={
              roleFilter === r
                ? { backgroundColor: '#D95D2B', color: '#ffffff', boxShadow: '0 2px 8px rgba(217,93,43,0.35)' }
                : tabInactive
            }
          >
            {r === 'ALL' ? 'All Roles' : `${r}s`}
          </button>
        ))}
      </div>

      {/* Staff Table */}
      {isLoading ? (
        <div className="p-12 text-center" style={{ color: muted }}>Loading staff records...</div>
      ) : staffList.length === 0 ? (
        <div className="p-12 text-center rounded-3xl" style={{ ...tableWrap, color: muted }}>
          No staff accounts found.
        </div>
      ) : (
        <div className="rounded-3xl overflow-hidden shadow-sm" style={tableWrap}>
          <table className="w-full text-left text-sm" style={{ color: heading }}>
            <thead className="text-xs uppercase tracking-wider border-b" style={{ ...thead, borderBottomColor: border }}>
              <tr>
                <th className="px-6 py-4 font-semibold">User</th>
                <th className="px-6 py-4 font-semibold">Role</th>
                <th className="px-6 py-4 font-semibold">Status</th>
                <th className="px-6 py-4 font-semibold">Last Login (IST)</th>
                <th className="px-6 py-4 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y" style={{ borderColor: border }}>
              {staffList.map((user) => (
                <tr
                  key={user.id}
                  className="transition"
                  style={{ ...tbodyRow, borderBottomColor: border }}
                  onMouseEnter={(e) => {
                    if (tbodyRowHover.backgroundColor) {
                      e.currentTarget.style.backgroundColor = tbodyRowHover.backgroundColor as string;
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-9 h-9 rounded-xl flex items-center justify-center font-bold text-xs"
                        style={{
                          backgroundColor: L ? '#f5f0e8' : '#1e293b',
                          color: heading,
                          border: `1px solid ${border}`,
                        }}
                      >
                        {user.username.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <div className="font-semibold" style={{ color: heading }}>{user.full_name}</div>
                        <div className="text-xs font-mono" style={{ color: muted }}>@{user.username}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className="text-xs font-mono font-bold px-2.5 py-1 rounded-full"
                      style={{
                        backgroundColor: user.role === 'ADMIN' ? '#ede9fe' : user.role === 'KITCHEN' ? '#ffedd5' : '#dbeafe',
                        color: user.role === 'ADMIN' ? '#5b21b6' : user.role === 'KITCHEN' ? '#9a3412' : '#1e40af',
                        border: '1px solid transparent',
                      }}
                    >
                      {user.role}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={user.status} size="sm" />
                    {user.failed_login_attempts > 0 && user.status === 'LOCKED' && (
                      <span className="text-xs text-rose-500 block mt-1 font-mono">
                        {user.failed_login_attempts} failed attempts
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-xs font-mono" style={{ color: sub }}>
                    {formatDateTimeIst(user.last_login_at)}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {/* Unlock button if locked */}
                      {user.status === 'LOCKED' && (
                        <button
                          onClick={() => handleUnlockUser(user)}
                          title="Unlock account"
                          aria-label={`Unlock @${user.username}`}
                          className="p-2 rounded-xl border transition cursor-pointer hover:brightness-95"
                          style={{ color: '#92400e', backgroundColor: '#fef3c7', borderColor: '#fcd34d' }}
                        >
                          <Unlock className="w-4 h-4" />
                        </button>
                      )}

                      {/* Reset password button */}
                      <button
                        onClick={() => {
                          setShowResetPassword(false);
                          setNewResetPassword('');
                          setResetTargetUser(user);
                        }}
                        title="Reset password"
                        aria-label={`Reset password for @${user.username}`}
                        className="p-2 rounded-xl border transition cursor-pointer hover:brightness-95"
                        style={{ color: '#9a3412', backgroundColor: '#ffedd5', borderColor: '#fdba74' }}
                      >
                        <KeyRound className="w-4 h-4" />
                      </button>

                      {/* Deactivate / Activate button (an admin cannot disable their own account) */}
                      <button
                        onClick={() => setUserToDeactivate(user)}
                        disabled={user.id === currentUser?.id}
                        title={
                          user.id === currentUser?.id
                            ? 'You cannot disable your own account'
                            : user.is_active
                              ? 'Disable account'
                              : 'Reactivate account'
                        }
                        aria-label={user.is_active ? `Disable @${user.username}` : `Reactivate @${user.username}`}
                        className="p-2 rounded-xl border transition cursor-pointer hover:brightness-95 disabled:opacity-40 disabled:cursor-not-allowed"
                        style={
                          user.is_active
                            ? { color: '#9f1239', backgroundColor: '#ffe4e6', borderColor: '#fda4af' }
                            : { color: '#166534', backgroundColor: '#dcfce7', borderColor: '#86efac' }
                        }
                      >
                        {user.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create Staff Modal */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-3xl p-6 shadow-2xl" style={card}>
            <div className="flex items-center justify-between pb-4 border-b" style={{ borderBottomColor: border }}>
              <h3 className="text-lg font-bold" style={{ color: heading }}>Create Staff Account</h3>
              <button onClick={() => setIsCreateOpen(false)} style={{ color: muted }} className="cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateStaff} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Username</label>
                <input
                  type="text"
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  placeholder="waiter_rahul"
                  required
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none"
                  style={{
                    backgroundColor: L ? '#faf7f2' : '#0f172a',
                    border: `1.5px solid ${border}`,
                    color: heading,
                  }}
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Full Name</label>
                <input
                  type="text"
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  placeholder="Rahul Kumar"
                  required
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm focus:outline-none"
                  style={{
                    backgroundColor: L ? '#faf7f2' : '#0f172a',
                    border: `1.5px solid ${border}`,
                    color: heading,
                  }}
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Assigned Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value as UserRole)}
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm focus:outline-none cursor-pointer"
                  style={{
                    backgroundColor: L ? '#faf7f2' : '#0f172a',
                    border: `1.5px solid ${border}`,
                    color: heading,
                  }}
                >
                  <option value="WAITER">WAITER (Floor orders & bill settlement)</option>
                  <option value="KITCHEN">KITCHEN (KDS ticket processing)</option>
                  <option value="ADMIN">ADMIN (Full administrative access)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Initial Password</label>
                <div className="relative">
                  <input
                    type={showNewPassword ? 'text' : 'password'}
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="At least 6 characters"
                    required
                    minLength={6}
                    autoComplete="new-password"
                    className="w-full pl-3.5 pr-11 py-2.5 rounded-xl text-sm focus:outline-none"
                    style={{
                      backgroundColor: L ? '#faf7f2' : '#0f172a',
                      border: `1.5px solid ${border}`,
                      color: heading,
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowNewPassword((v) => !v)}
                    aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                    title={showNewPassword ? 'Hide password' : 'Show password'}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg cursor-pointer hover:bg-slate-100"
                    style={{ color: sub }}
                  >
                    {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium transition cursor-pointer"
                  style={{ color: sub }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-md cursor-pointer"
                >
                  Create Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reset Password Modal */}
      {resetTargetUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div className="w-full max-w-sm rounded-3xl p-6 shadow-2xl" style={card}>
            <h3 className="text-base font-bold" style={{ color: heading }}>Reset Staff Password</h3>
            <p className="text-xs mt-1" style={{ color: sub }}>For @{resetTargetUser.username}</p>
            <form onSubmit={handleResetPassword} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>New Password</label>
                <div className="relative">
                  <input
                    type={showResetPassword ? 'text' : 'password'}
                    value={newResetPassword}
                    onChange={(e) => setNewResetPassword(e.target.value)}
                    placeholder="At least 6 characters"
                    required
                    minLength={6}
                    autoComplete="new-password"
                    className="w-full pl-3.5 pr-11 py-2.5 rounded-xl text-sm focus:outline-none"
                    style={{
                      backgroundColor: '#ffffff',
                      border: `1px solid ${border}`,
                      color: heading,
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowResetPassword((v) => !v)}
                    aria-label={showResetPassword ? 'Hide password' : 'Show password'}
                    title={showResetPassword ? 'Hide password' : 'Show password'}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg cursor-pointer hover:bg-slate-100"
                    style={{ color: sub }}
                  >
                    {showResetPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setResetTargetUser(null)}
                  className="px-4 py-2 rounded-xl text-xs font-medium transition cursor-pointer"
                  style={{ color: sub }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white shadow-md cursor-pointer"
                >
                  Set Password
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Deactivate Confirmation */}
      <ConfirmModal
        isOpen={!!userToDeactivate}
        title={`${userToDeactivate?.is_active ? 'Deactivate' : 'Reactivate'} Staff Account`}
        description={
          userToDeactivate?.is_active
            ? `Deactivating @${userToDeactivate?.username} will immediately revoke their refresh tokens and terminate active app sessions.`
            : `Reactivating @${userToDeactivate?.username} will restore their login access.`
        }
        confirmLabel={userToDeactivate?.is_active ? 'Disable Account' : 'Reactivate'}
        variant={userToDeactivate?.is_active ? 'danger' : 'primary'}
        onConfirm={handleToggleDeactivate}
        onCancel={() => setUserToDeactivate(null)}
      />
    </div>
  );
};
