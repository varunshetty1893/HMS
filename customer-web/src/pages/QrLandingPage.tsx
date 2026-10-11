import React, { useEffect, useState } from 'react';
import { useSession } from '../context/SessionContext';
import { QrCode, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';

interface QrLandingPageProps {
  onSuccess: () => void;
  onError: (msg: string) => void;
}

export const QrLandingPage: React.FC<QrLandingPageProps> = ({ onSuccess, onError }) => {
  const { initFromQr } = useSession();
  const [statusMessage, setStatusMessage] = useState<string>('Verifying Table QR...');
  const [errorDetails, setErrorDetails] = useState<string | null>(null);

  useEffect(() => {
    const parseToken = (): string | null => {
      // 1. Path check: /q/:qrToken
      const pathMatches = window.location.pathname.match(/\/q\/([^/?#]+)/);
      if (pathMatches && pathMatches[1]) {
        return pathMatches[1];
      }

      // 2. Query param check: ?qr=... or ?token=...
      const urlParams = new URLSearchParams(window.location.search);
      const queryToken = urlParams.get('qr') || urlParams.get('token');
      if (queryToken) {
        return queryToken;
      }

      // 3. Hash check: #/q/:token or #token
      const hash = window.location.hash;
      const hashMatches = hash.match(/\/q\/([^/?#]+)/);
      if (hashMatches && hashMatches[1]) {
        return hashMatches[1];
      }

      return null;
    };

    const token = parseToken();

    if (!token) {
      setErrorDetails('No table QR token detected. Please scan the QR code located on your dining table.');
      return;
    }

    // Resolve QR token
    const resolve = async () => {
      try {
        setStatusMessage('Connecting to Table...');
        const ok = await initFromQr(token);

        // Security rule: Immediately strip raw QR secret from URL history bar
        try {
          const cleanUrl = window.location.pathname.replace(/\/q\/[^/?#]+/, '/') || '/';
          window.history.replaceState(null, document.title, cleanUrl);
        } catch {
          // ignore history errors in non-browser envs
        }

        if (ok) {
          onSuccess();
        } else {
          setErrorDetails('This QR code is either invalid, revoked, or the dining table is currently closed.');
          onError('QR code resolution failed');
        }
      } catch {
        setErrorDetails('Unable to reach restaurant servers. Please check your network connection.');
        onError('Network error');
      }
    };

    resolve();
  }, [initFromQr, onSuccess, onError]);

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
              <span>{errorDetails}</span>
            </div>

            <button
              onClick={() => window.location.reload()}
              className="w-full text-white font-semibold py-3 px-4 rounded-xl flex items-center justify-center gap-2 text-xs transition-all shadow-sm"
              style={{ background: 'var(--primary)' }}
            >
              <RefreshCw size={14} />
              <span>Retry Scan</span>
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
