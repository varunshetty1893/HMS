import React, { useEffect, useState } from 'react';
import { useSession } from '../context/SessionContext';
import { QrCode, AlertCircle, RefreshCw } from 'lucide-react';

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
      } catch (err: unknown) {
        setErrorDetails('Unable to reach restaurant servers. Please check your network connection.');
        onError('Network error');
      }
    };

    resolve();
  }, [initFromQr, onSuccess, onError]);

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-white text-center">
      <div className="max-w-sm w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-orange-500/20 text-orange-400 border border-orange-500/30 flex items-center justify-center mx-auto shadow-inner">
          <QrCode size={32} />
        </div>

        <div>
          <h2 className="text-xl font-bold text-white mb-2">Welcome to HMS Dining</h2>
          <p className="text-sm text-slate-400">
            Fast, seamless digital ordering right from your table.
          </p>
        </div>

        {errorDetails ? (
          <div className="space-y-4">
            <div className="bg-rose-950/60 border border-rose-800 rounded-2xl p-4 text-xs text-rose-300 flex items-start space-x-3 text-left">
              <AlertCircle size={18} className="text-rose-400 shrink-0 mt-0.5" />
              <span>{errorDetails}</span>
            </div>

            <button
              onClick={() => window.location.reload()}
              className="w-full bg-slate-800 hover:bg-slate-700 text-white font-semibold py-2.5 px-4 rounded-xl flex items-center justify-center space-x-2 text-xs transition"
            >
              <RefreshCw size={14} />
              <span>Retry</span>
            </button>
          </div>
        ) : (
          <div className="space-y-3 py-2">
            <div className="w-6 h-6 border-2 border-orange-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p className="text-xs text-slate-400 animate-pulse">{statusMessage}</p>
          </div>
        )}
      </div>
    </div>
  );
};
