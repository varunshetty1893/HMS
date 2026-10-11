import React from 'react';
import { QrCode, AlertTriangle } from 'lucide-react';

interface SessionErrorPageProps {
  message?: string;
}

export const SessionErrorPage: React.FC<SessionErrorPageProps> = ({
  message = 'Your dining session could not be verified or the table QR code has expired.',
}) => {
  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-white text-center">
      <div className="max-w-sm w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center justify-center mx-auto">
          <AlertTriangle size={32} />
        </div>

        <div>
          <h2 className="text-xl font-bold text-white mb-2">Session Expired</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            {message}
          </p>
        </div>

        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4 text-xs text-slate-300 space-y-2 text-left">
          <div className="flex items-center space-x-2 text-orange-400 font-semibold">
            <QrCode size={16} />
            <span>How to re-connect:</span>
          </div>
          <ol className="list-decimal list-inside space-y-1 text-slate-400 pl-1">
            <li>Scan the QR code printed on your table again.</li>
            <li>Or ask your server for table assistance.</li>
          </ol>
        </div>
      </div>
    </div>
  );
};
