import React from 'react';
import { UtensilsCrossed, Smartphone, Sparkles, QrCode } from 'lucide-react';
import { useSession } from '../context/SessionContext';

interface SessionErrorPageProps {
  message?: string;
}

export const SessionErrorPage: React.FC<SessionErrorPageProps> = ({
  message = 'Please scan your dining table\'s QR code to view the menu and place orders.',
}) => {
  const { startDemoSession } = useSession();

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-6 text-center"
      style={{ background: 'var(--cream, #FFF8ED)' }}
    >
      <div
        className="max-w-md w-full rounded-3xl p-8 space-y-6 shadow-md transition-all"
        style={{
          background: 'var(--white)',
          border: '1px solid var(--border)',
          boxShadow: '0 8px 30px rgba(40, 40, 32, 0.06)',
        }}
      >
        {/* Restaurant Icon Badge */}
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto shadow-sm"
          style={{
            background: 'var(--primary-bg)',
            color: 'var(--primary)',
            border: '1px solid rgba(217, 93, 43, 0.2)',
          }}
        >
          <QrCode size={34} />
        </div>

        <div>
          <span
            className="text-[11px] font-bold tracking-widest uppercase px-3 py-1 rounded-full inline-block mb-2"
            style={{
              background: 'var(--primary-bg)',
              color: 'var(--primary)',
            }}
          >
            SpiceHub Family Restaurant
          </span>
          <h2
            className="text-xl font-bold mb-2 tracking-tight"
            style={{ color: 'var(--text-primary)' }}
          >
            Dining Table Required
          </h2>
          <p
            className="text-xs leading-relaxed max-w-sm mx-auto"
            style={{ color: 'var(--text-secondary)' }}
          >
            {message}
          </p>
        </div>

        {/* Development / Testing Quick Access */}
        <div className="space-y-3 pt-1">
          <button
            onClick={startDemoSession}
            id="btn-preview-demo-table"
            className="w-full text-white font-semibold py-3.5 px-4 rounded-2xl flex items-center justify-center gap-2 text-sm shadow-md transition-all transform active:scale-98 cursor-pointer"
            style={{
              background: 'var(--primary)',
              boxShadow: '0 4px 16px rgba(217, 93, 43, 0.28)',
            }}
          >
            <UtensilsCrossed size={18} />
            <span>Preview Customer Menu (Table 4 Demo)</span>
          </button>
          <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>
            Instant interactive demo to explore dishes, cart, variant picker & ordering.
          </p>
        </div>

        {/* Explanation for Real Restaurant Flow */}
        <div
          className="rounded-2xl p-4 text-xs space-y-2.5 text-left"
          style={{
            background: 'var(--bg-subtle)',
            border: '1px solid var(--border)',
          }}
        >
          <div
            className="flex items-center gap-2 font-semibold"
            style={{ color: 'var(--primary)' }}
          >
            <Smartphone size={16} />
            <span>How QR ordering works at your table:</span>
          </div>
          <ol
            className="list-decimal list-inside space-y-1.5 pl-1 text-[11px] leading-relaxed"
            style={{ color: 'var(--text-secondary)' }}
          >
            <li>
              Point your <strong>phone camera</strong> or <strong>Google Lens</strong> at the QR sticker on the dining table.
            </li>
            <li>Tap the pop-up link to open your table's dedicated ordering session.</li>
            <li>Browse the menu, customize your order, and send directly to our kitchen!</li>
          </ol>
        </div>

        <div className="flex items-center justify-center gap-1.5 text-[11px]" style={{ color: 'var(--text-muted)' }}>
          <Sparkles size={13} style={{ color: 'var(--primary)' }} />
          <span>Freshly prepared • Authentic spices • Contactless dining</span>
        </div>
      </div>
    </div>
  );
};
