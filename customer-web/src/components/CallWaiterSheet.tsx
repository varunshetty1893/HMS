import React, { useState, useEffect, useCallback } from 'react';
import { BellRing, ChevronRight, CheckCircle2, Clock, X, Loader2, Hand } from 'lucide-react';
import { callWaiter, cancelWaiterRequest, getActiveWaiterRequest, HmsApiError } from '../api';
import type { WaiterRequest, WaiterRequestReason } from '../types';

interface CallWaiterSheetProps {
  isOpen: boolean;
  onClose: () => void;
  hasTableSession?: boolean;
}

const REASONS: { key: WaiterRequestReason; label: string; emoji: string; description: string }[] = [
  { key: 'ASSISTANCE', label: 'Need Assistance', emoji: '🙋', description: 'General help at your table' },
  { key: 'CUTLERY',   label: 'Cutlery / Napkins', emoji: '🍴', description: 'Cutlery, napkins, or condiments' },
  { key: 'WATER',     label: 'Water / Refill', emoji: '💧', description: 'Water or beverage refill' },
  { key: 'OTHER',     label: 'Something Else', emoji: '✋', description: 'Other table-side request' },
];

const STATUS_LABELS: Record<string, { text: string; className: string; icon: React.ReactNode }> = {
  PENDING:   { text: 'Calling waiter…', className: 'wr-pending',   icon: <Clock size={14} /> },
  CLAIMED:   { text: 'Waiter is on the way!', className: 'wr-claimed',   icon: <BellRing size={14} /> },
  COMPLETED: { text: 'Request fulfilled ✓', className: 'wr-completed', icon: <CheckCircle2 size={14} /> },
};

export const CallWaiterSheet: React.FC<CallWaiterSheetProps> = ({
  isOpen,
  onClose,
}) => {
  const [phase, setPhase] = useState<'pick' | 'requesting' | 'active'>('pick');
  const [activeRequest, setActiveRequest] = useState<WaiterRequest | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState(false);

  // On open, check for an existing active request
  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    getActiveWaiterRequest().then((req) => {
      if (req && (req.status === 'PENDING' || req.status === 'CLAIMED')) {
        setActiveRequest(req);
        setPhase('active');
      } else {
        setActiveRequest(null);
        setPhase('pick');
      }
    });
  }, [isOpen]);

  // Poll for status updates every 5 seconds while active
  useEffect(() => {
    if (phase !== 'active') return;
    const id = setInterval(async () => {
      const req = await getActiveWaiterRequest();
      if (!req || req.status === 'COMPLETED' || req.status === 'CANCELLED') {
        if (req?.status === 'COMPLETED') {
          setActiveRequest(req);
          // Auto-close after showing completion for 3s
          setTimeout(() => { setPhase('pick'); setActiveRequest(null); onClose(); }, 3000);
        } else {
          setActiveRequest(null);
          setPhase('pick');
        }
        clearInterval(id);
      } else {
        setActiveRequest(req);
      }
    }, 5000);
    return () => clearInterval(id);
  }, [phase, onClose]);

  const handlePickReason = useCallback(async (reason: WaiterRequestReason) => {
    setPhase('requesting');
    setError(null);
    try {
      const req = await callWaiter(reason);
      setActiveRequest(req);
      setPhase('active');
    } catch (err) {
      setPhase('pick');
      if (err instanceof HmsApiError) {
        setError(err.message || 'Failed to call waiter. Please try again.');
      } else {
        setError('Network error. Please try again.');
      }
    }
  }, []);

  const handleCancel = useCallback(async () => {
    if (!activeRequest || isCancelling) return;
    setIsCancelling(true);
    try {
      await cancelWaiterRequest(activeRequest.id);
      setActiveRequest(null);
      setPhase('pick');
    } catch (err) {
      if (err instanceof HmsApiError) {
        setError(err.message);
      }
    } finally {
      setIsCancelling(false);
    }
  }, [activeRequest, isCancelling]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 animate-fade-in"
      style={{ background: 'rgba(40,40,32,0.45)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="absolute bottom-0 left-0 right-0 bottom-sheet animate-slide-up max-w-md mx-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Handle bar */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="w-10 h-1 rounded-full" style={{ background: 'var(--border)' }} />
        </div>

        {/* Header */}
        <div className="flex items-center justify-between px-5 pt-2 pb-4">
          <div className="flex items-center gap-2.5">
            <div
              className="w-10 h-10 rounded-2xl flex items-center justify-center"
              style={{ background: 'var(--primary-bg)', color: 'var(--primary)' }}
            >
              <Hand size={20} />
            </div>
            <div>
              <h2 className="font-bold text-base" style={{ color: 'var(--text-primary)' }}>
                Call Waiter
              </h2>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                We'll send someone right away
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center transition-colors"
            style={{ background: 'var(--bg-subtle)', color: 'var(--text-secondary)' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="mx-5 mb-3 px-4 py-3 rounded-xl text-sm flex items-center justify-between"
            style={{ background: '#FEF2F2', color: '#B91C1C', border: '1px solid #FCA5A5' }}>
            <span>{error}</span>
            <button onClick={() => setError(null)}><X size={14} /></button>
          </div>
        )}

        {/* Phase: pick reason */}
        {phase === 'pick' && (
          <div className="px-5 pb-6 space-y-2.5">
            <p className="text-xs font-semibold uppercase tracking-wide mb-3"
              style={{ color: 'var(--text-muted)' }}>
              What do you need?
            </p>
            {REASONS.map(({ key, label, emoji, description }) => (
              <button
                key={key}
                onClick={() => handlePickReason(key)}
                className="w-full flex items-center gap-3 p-3.5 rounded-2xl border text-left transition-all cursor-pointer"
                style={{
                  background: 'var(--bg-subtle)',
                  borderColor: 'var(--border)',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--primary)';
                  e.currentTarget.style.background = 'var(--primary-bg)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.background = 'var(--bg-subtle)';
                }}
              >
                <span className="text-2xl">{emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                    {label}
                  </div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{description}</div>
                </div>
                <ChevronRight size={16} style={{ color: 'var(--text-muted)' }} />
              </button>
            ))}
          </div>
        )}

        {/* Phase: requesting (spinner) */}
        {phase === 'requesting' && (
          <div className="px-5 pb-8 flex flex-col items-center gap-3 pt-2">
            <Loader2 size={36} className="animate-spin" style={{ color: 'var(--primary)' }} />
            <p className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
              Notifying staff…
            </p>
          </div>
        )}

        {/* Phase: active request */}
        {phase === 'active' && activeRequest && (
          <div className="px-5 pb-6 space-y-4">
            {/* Status badge */}
            <div className="flex items-center justify-center">
              <div
                className={`flex items-center gap-2 px-4 py-2.5 rounded-full font-semibold text-sm ${STATUS_LABELS[activeRequest.status]?.className ?? ''}`}
              >
                {STATUS_LABELS[activeRequest.status]?.icon}
                {STATUS_LABELS[activeRequest.status]?.text ?? activeRequest.status}
              </div>
            </div>

            {/* Request details */}
            <div
              className="rounded-2xl p-4 space-y-2"
              style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border)' }}
            >
              <div className="flex items-center justify-between">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Reason</span>
                <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {REASONS.find(r => r.key === activeRequest.reason)?.label ?? activeRequest.reason}
                </span>
              </div>
              {activeRequest.notes && (
                <div className="flex items-start justify-between gap-2">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Note</span>
                  <span className="text-xs text-right" style={{ color: 'var(--text-secondary)' }}>
                    {activeRequest.notes}
                  </span>
                </div>
              )}
              <div className="flex items-center justify-between">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Sent at</span>
                <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                  {new Date(activeRequest.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
            </div>

            {/* Cancel (only PENDING) */}
            {activeRequest.status === 'PENDING' && (
              <button
                onClick={handleCancel}
                disabled={isCancelling}
                className="w-full py-2.5 rounded-xl border text-sm font-medium transition-colors flex items-center justify-center gap-2"
                style={{
                  borderColor: 'var(--border)',
                  color: 'var(--text-secondary)',
                  background: 'transparent',
                }}
              >
                {isCancelling ? <Loader2 size={14} className="animate-spin" /> : <X size={14} />}
                Cancel Request
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
