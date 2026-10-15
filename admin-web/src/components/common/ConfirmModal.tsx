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
  /** Shown instead of the confirm button when onConfirm fails with this error code. */
  fallbackAction?: {
    errorCode: string;
    label: string;
    onClick: () => Promise<void> | void;
  };
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
  fallbackAction,
}) => {
  const [reason, setReason] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleConfirm = async () => {
    if (requireReason && !reason.trim()) {
      setError('A reason is mandatory for this action.');
      return;
    }
    setError(null);
    setErrorCode(null);
    setIsSubmitting(true);
    try {
      await onConfirm(reason.trim());
      setReason('');
      onCancel();
    } catch (err: any) {
      setError(err?.message || 'Operation failed');
      setErrorCode(err?.code || null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => {
    setError(null);
    setErrorCode(null);
    onCancel();
  };

  const handleFallback = async () => {
    if (!fallbackAction) return;
    setIsSubmitting(true);
    try {
      await fallbackAction.onClick();
      setError(null);
      setErrorCode(null);
      onCancel();
    } catch (err: any) {
      setError(err?.message || 'Operation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const showFallback = !!fallbackAction && errorCode === fallbackAction.errorCode;

  const buttonColors =
    variant === 'danger'
      ? 'bg-rose-600 hover:bg-rose-500 text-white'
      : variant === 'warning'
        ? 'bg-amber-600 hover:bg-amber-500 text-white'
        : 'bg-brand-600 hover:bg-brand-500 text-white';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div className="w-full max-w-md rounded-2xl bg-white border border-gray-200 p-6 shadow-2xl">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div
              className={`p-2.5 rounded-xl ${
                variant === 'danger'
                  ? 'bg-rose-50 text-rose-600 border border-rose-200'
                  : 'bg-amber-50 text-amber-600 border border-amber-200'
              }`}
            >
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">{title}</h3>
              <p className="text-sm text-gray-500 mt-1">{description}</p>
            </div>
          </div>
          <button
            onClick={handleCancel}
            disabled={isSubmitting}
            className="text-gray-400 hover:text-gray-700 p-1 rounded-lg cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {requireReason && (
          <div className="mt-4">
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-700 mb-1">
              Mandatory Audit Reason
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder={reasonPlaceholder}
              rows={3}
              className="w-full rounded-xl bg-slate-50 border border-gray-300 p-3 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
            />
          </div>
        )}

        {error && (
          <p className="mt-3 text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <div className="mt-6 flex items-center justify-end gap-3">
          <button
            type="button"
            onClick={handleCancel}
            disabled={isSubmitting}
            className="px-4 py-2 rounded-xl text-sm font-medium text-gray-700 hover:bg-gray-100 border border-gray-300 cursor-pointer"
          >
            {cancelLabel}
          </button>
          {showFallback ? (
            <button
              type="button"
              onClick={handleFallback}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-sm font-semibold transition cursor-pointer bg-brand-600 hover:bg-brand-500 text-white"
            >
              {isSubmitting ? 'Processing...' : fallbackAction!.label}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleConfirm}
              disabled={isSubmitting}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition cursor-pointer ${buttonColors}`}
            >
              {isSubmitting ? 'Processing...' : confirmLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
