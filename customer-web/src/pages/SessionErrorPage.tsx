import React from 'react';
import { AlertTriangle, UtensilsCrossed, Smartphone } from 'lucide-react';
import { useSession } from '../context/SessionContext';

interface SessionErrorPageProps {
  message?: string;
}

export const SessionErrorPage: React.FC<SessionErrorPageProps> = ({
  message = 'Please scan your dining table\'s QR code to view the menu and place orders.',
}) => {
  const { startDemoSession } = useSession();

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-6 text-white text-center">
      <div className="max-w-md w-full bg-slate-900/90 border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6 backdrop-blur-sm">
        <div className="w-16 h-16 rounded-2xl bg-amber-500/20 text-amber-400 border border-amber-500/30 flex items-center justify-center mx-auto shadow-inner">
          <AlertTriangle size={32} />
        </div>

        <div>
          <h2 className="text-xl font-bold text-white mb-2">Dining Table Required</h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            {message}
          </p>
        </div>

        {/* Development / Testing Quick Access */}
        <div className="space-y-3 pt-2">
          <button
            onClick={startDemoSession}
            id="btn-preview-demo-table"
            className="w-full bg-gradient-to-r from-orange-500 via-amber-500 to-orange-600 hover:from-orange-600 hover:to-amber-600 text-white font-semibold py-3.5 px-4 rounded-2xl flex items-center justify-center space-x-2 text-sm shadow-lg shadow-orange-500/25 transition-all transform active:scale-98 cursor-pointer"
          >
            <UtensilsCrossed size={18} />
            <span>Preview Customer Menu (Table 4 Demo)</span>
          </button>
          <p className="text-[11px] text-slate-500">
            Click above to instantly explore the customer menu, cart & ordering without scanning a physical QR code.
          </p>
        </div>

        {/* Explanation for Real Restaurant Flow */}
        <div className="bg-slate-800/60 border border-slate-700/60 rounded-2xl p-4 text-xs text-slate-300 space-y-2.5 text-left">
          <div className="flex items-center space-x-2 text-orange-400 font-semibold">
            <Smartphone size={16} />
            <span>How QR ordering works for customers:</span>
          </div>
          <ol className="list-decimal list-inside space-y-1.5 text-slate-400 pl-1 text-[11px] leading-relaxed">
            <li>Guests don't scan from inside the app; they use their <strong>phone camera</strong> or <strong>Google Lens</strong> to scan the table's physical QR sticker.</li>
            <li>The phone camera opens the table link: <code className="text-amber-400 font-mono">http://localhost:3001/?qr=...</code></li>
            <li>The menu loads automatically linked to that specific table!</li>
          </ol>
        </div>
      </div>
    </div>
  );
};
