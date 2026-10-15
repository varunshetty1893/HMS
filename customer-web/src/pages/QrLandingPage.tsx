import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useSession } from '../context/SessionContext';
import { QrCode, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';
import {
  clearPendingQrToken,
  extractQrToken,
  savePendingQrToken,
  stripQrTokenFromPath,
} from '../utils/qrToken';
import { HmsApiError } from '../api';

interface QrLandingPageProps {
  onSuccess: () => void;
  onError: (msg: string) => void;
}

function describeFailure(err: unknown): string {
  if (err instanceof HmsApiError) {
    switch (err.code) {
      case 'QR_TOKEN_INVALID_OR_REVOKED':
        return err.message;
      case 'TABLE_NOT_AVAILABLE':
        return err.message;
      case 'API_NOT_CONFIGURED':
      case 'API_UNREACHABLE':
        return err.message;
      default:
        if (err.httpStatus === 429) {
          return 'Too many attempts. Please wait a minute and tap Try again.';
        }
        return err.message || 'This QR code could not be opened.';
    }
  }
  return 'Unable to reach restaurant servers. Please check your network connection and try again.';
}

export const QrLandingPage: React.FC<QrLandingPageProps> = ({ onSuccess, onError }) => {
  const { initFromQr, error: sessionError } = useSession();
  const [statusMessage, setStatusMessage] = useState<string>('Verifying Table QR...');
  const [errorDetails, setErrorDetails] = useState<string | null>(null);

  // Parent passes new callback functions on every render; keep them in refs so they can
  // never re-trigger the resolve effect (that caused duplicate requests and a lost token).
  const onSuccessRef = useRef(onSuccess);
  const onErrorRef = useRef(onError);
  onSuccessRef.current = onSuccess;
  onErrorRef.current = onError;

  const inFlight = useRef(false);

  const resolve = useCallback(async () => {
    if (inFlight.current) return;

    const token = extractQrToken();
    if (!token) {
      setErrorDetails('No table QR token detected. Please scan the QR code located on your dining table.');
      return;
    }

    inFlight.current = true;
    setErrorDetails(null);
    // Remember the token until it has been resolved, so a reload/retry reuses it.
    savePendingQrToken(token);

    try {
      setStatusMessage('Connecting to Table...');
      const ok = await initFromQr(token);

      if (ok) {
        // Only now is it safe to strip the secret from the address bar.
        clearPendingQrToken();
        try {
          const cleanUrl = stripQrTokenFromPath(window.location.pathname);
          window.history.replaceState(null, document.title, cleanUrl);
        } catch {
          // ignore history errors in non-browser envs
        }
        onSuccessRef.current();
      } else {
        const msg = 'This QR code could not be opened. Tap Try again, or ask staff to check the table QR.';
        setErrorDetails(msg);
        onErrorRef.current('QR code resolution failed');
      }
    } catch (err) {
      setErrorDetails(describeFailure(err));
      onErrorRef.current('Network error');
    } finally {
      inFlight.current = false;
    }
  }, [initFromQr]);

  useEffect(() => {
    void resolve();
  }, [resolve]);

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-6 text-center"
      style={{ background: 'var(--cream, #FFF8ED)' }}
    >
      <div
        className="max-w-sm w-full rounded-3xl p-8 space-y-6 shadow-md"
        style={{
          background: 'var(--white)',
          border: '1px solid var(--border)',
          boxShadow: '0 8px 30px rgba(40, 40, 32, 0.06)',
        }}
      >
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto shadow-sm"
          style={{
            background: 'var(--primary-bg)',
            color: 'var(--primary)',
            border: '1px solid rgba(217, 93, 43, 0.2)',
          }}
        >
          <QrCode size={32} />
        </div>

        <div>
          <span
            className="text-[11px] font-bold tracking-widest uppercase px-3 py-1 rounded-full inline-block mb-2"
            style={{
              background: 'var(--primary-bg)',
              color: 'var(--primary)',
            }}
          >
            SpiceHub Dining
          </span>
          <h2
            className="text-xl font-bold mb-1 tracking-tight"
            style={{ color: 'var(--text-primary)' }}
          >
            Welcome to Your Table
          </h2>
          <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
            Instant digital ordering, straight to the kitchen.
          </p>
        </div>

        {errorDetails ? (
          <div className="space-y-4">
            <div
              className="rounded-2xl p-4 text-xs flex items-start gap-3 text-left"
              style={{
                background: '#FEF2F2',
                border: '1px solid #FCA5A5',
                color: '#B91C1C',
              }}
            >
              <AlertCircle size={18} className="shrink-0 mt-0.5 text-red-500" />
              <span>{sessionError || errorDetails}</span>
            </div>

            <button
              onClick={() => void resolve()}
              className="w-full text-white font-semibold py-3 px-4 rounded-xl flex items-center justify-center gap-2 text-xs transition-all shadow-sm"
              style={{ background: 'var(--primary)' }}
            >
              <RefreshCw size={14} />
              <span>Try again</span>
            </button>
          </div>
        ) : (
          <div className="space-y-3 py-3">
            <Loader2
              size={28}
              className="animate-spin mx-auto"
              style={{ color: 'var(--primary)' }}
            />
            <p
              className="text-xs font-medium animate-pulse"
              style={{ color: 'var(--text-secondary)' }}
            >
              {statusMessage}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
