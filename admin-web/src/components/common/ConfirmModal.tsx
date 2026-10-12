import React, { useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'primary';
  requireReason?: boolean;
  reasonPlaceholder?: string;
  onConfirm: (reason?: string) => Promise<void> | void;
  onCancel: () => void;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'danger',
  requireReason = false,
  reasonPlaceholder = 'Please enter reason...',
  onConfirm,
  onCancel,
}) => {
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    if (requireReason && !reason.trim()) {
      setError('A reason is mandatory for this action.');
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await onConfirm(reason.trim());
      setReason('');
      onCancel();
    } catch (err: any) {
      setError(err?.message || 'Operation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const buttonColors =
    variant === 'danger'
      ? 'bg-rose-600 hover:bg-rose-500 text-white'
      : variant === 'warning'
        ? 'bg-amber-600 hover:bg-amber-500 text-white'
        : 'bg-brand-600 hover:bg-brand-500 text-white';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
      <div className="w-full max-w-md rounded-2xl bg-slate-900 border border-slate-800 p-6 shadow-2xl">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-xl ${
                variant === 'danger'
                  ? 'bg-rose-950/60 text-rose-400 border border-rose-800/40'
                  : 'bg-amber-950/60 text-amber-400 border border-amber-800/40'
              }`}
            >
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-ink">{title}</h3>
              <p className="text-sm text-slate-400 mt-1">{description}</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            disabled={isSubmitting}
            className="text-slate-400 hover:text-ink p-1 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {requireReason && (
          <div className="mt-4">
            <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Mandatory Audit Reason
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={reasonPlaceholder}
              rows={3}
              className="w-full rounded-xl bg-slate-950 border border-slate-800 p-3 text-sm text-ink placeholder-slate-500 focus:outline-none focus:border-brand-500"
            />
          </div>
        )}

        {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-xl text-sm font-medium text-slate-300 hover:bg-slate-800 border border-slate-700/60"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={handleConfirm}
            disabled={isSubmitting}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition ${buttonColors}`}
          >
            {isSubmitting ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
