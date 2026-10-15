import React, { useState } from 'react';
import { Copy, Printer, X } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { QrPrintCardResponse } from '@/types/api';
import { isDevDemoEnabled } from '@/utils/env';

interface PrintableQrCardModalProps {
  cardData: QrPrintCardResponse | null;
  onClose: () => void;
}

export const PrintableQrCardModal: React.FC<PrintableQrCardModalProps> = ({
  cardData,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);
  if (!cardData) return null;

  // Backend sends `qr_url` + `table_display_name`; older demo data used the other names.
  const orderingUrl = cardData.qr_url || cardData.ordering_url || '';
  const tableName = cardData.table_display_name || cardData.display_name || `Table ${cardData.table_number}`;
  const isLocalUrl = /localhost|127\.0\.0\.1/.test(orderingUrl);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(orderingUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      window.prompt('Copy this link:', orderingUrl);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div className="w-full max-w-md rounded-2xl bg-white border border-gray-200 p-6 shadow-2xl overflow-hidden relative">
        {/* Controls - Hidden during print */}
        <div className="no-print flex items-center justify-between pb-4 border-b border-gray-200">
          <div>
            <h3 className="text-base font-bold text-gray-900">Table QR Card</h3>
            <p className="text-xs text-gray-500">Token v{cardData.token_version} • Prefix {cardData.token_prefix}</p>
          </div>
          <div className="flex items-center gap-2">
            {isDevDemoEnabled() && (
              <button
                onClick={() => {
                  sessionStorage.setItem('hms_table_number', cardData.table_number.toString());
                  sessionStorage.setItem('hms_table_name', tableName);
                  sessionStorage.setItem('hms_table_id', cardData.table_id);
                  sessionStorage.setItem('hms_customer_token', `demo-token-table-${cardData.table_number}`);
                  const url = new URL(window.location.href);
                  url.searchParams.set('view', 'customer');
                  url.searchParams.set('table', cardData.table_number.toString());
                  window.history.pushState({}, '', url.toString());
                  window.dispatchEvent(new PopStateEvent('popstate'));
                  onClose();
                }}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm transition cursor-pointer"
                title="[DEV ONLY] Test the mobile QR ordering view for this table"
              >
                <span>📱 Test Order View</span>
              </button>
            )}
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-sm transition cursor-pointer"
            >
              <Printer className="w-4 h-4" />
              <span>Print Card</span>
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-700 p-1 rounded-lg cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="no-print mt-4 space-y-2">
          {isLocalUrl && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800">
              This QR points to <b>localhost</b>, so phones cannot open it. Set
              <b> PUBLIC_QR_BASE_URL</b> on the backend to your customer website link
              (for example https://your-customer-site.pages.dev/q).
            </div>
          )}
          <div className="flex items-center gap-2 p-2 rounded-xl bg-slate-50 border border-slate-200">
            <span className="flex-1 text-[11px] font-mono text-slate-600 truncate">{orderingUrl || 'No link'}</span>
            <button
              onClick={handleCopy}
              disabled={!orderingUrl}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold bg-slate-900 text-white cursor-pointer disabled:opacity-40"
            >
              <Copy className="w-3.5 h-3.5" />
              <span>{copied ? 'Copied' : 'Copy link'}</span>
            </button>
          </div>
        </div>

        {/* The printable table card */}
        <div className="mt-6 p-8 bg-white text-slate-900 rounded-2xl shadow-xl flex flex-col items-center text-center border-4 border-slate-900">
          <img src="/logo.png" alt="Spice Hub" className="w-20 h-20 mb-2" />
          <div className="uppercase tracking-widest text-[11px] font-black text-brand-600 mb-1">
            {cardData.restaurant_name}
          </div>
          <div className="text-3xl font-black tracking-tight text-slate-950 mb-4">
            {tableName}
          </div>

          {/* QR Code Container */}
          <div className="p-4 bg-slate-50 border-2 border-slate-200 rounded-2xl mb-4 shadow-inner">
            {orderingUrl ? (
              <QRCodeSVG value={orderingUrl} size={192} level="M" marginSize={2} className="block" />
            ) : (
              <div className="w-48 h-48 flex items-center justify-center text-xs text-rose-600 font-semibold">
                QR link missing. Check PUBLIC_QR_BASE_URL on the backend.
              </div>
            )}
          </div>

          <div className="space-y-1">
            <p className="text-sm font-bold text-slate-900">SCAN TO VIEW MENU & ORDER</p>
            <p className="text-[11px] text-slate-500 font-medium">No app download required • Pay at counter</p>
          </div>

          <div className="mt-6 pt-3 border-t border-slate-200 w-full flex justify-between items-center text-[10px] text-slate-400 font-mono">
            <span>TABLE #{cardData.table_number}</span>
            <span>TOKEN V{cardData.token_version}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
