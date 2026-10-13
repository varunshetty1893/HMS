import React from 'react';
import { Printer, X } from 'lucide-react';
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
  if (!cardData) return null;

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
      <div className="w-full max-w-md rounded-2xl bg-white border border-gray-200 p-6 shadow-2xl overflow-hidden relative">
        {/* Controls - Hidden during print */}
        <div className="no-print flex items-center justify-between pb-4 border-b border-gray-200">
          <div>
            <h3 className="text-base font-bold text-gray-900">Table QR Standee Card</h3>
            <p className="text-xs text-gray-500">Token v{cardData.token_version} • Prefix {cardData.token_prefix}</p>
          </div>
          <div className="flex items-center gap-2">
            {isDevDemoEnabled() && (
              <button
                onClick={() => {
                  sessionStorage.setItem('hms_table_number', cardData.table_number.toString());
                  sessionStorage.setItem('hms_table_name', cardData.display_name);
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

        {/* The Printable Standee Card */}
        <div className="mt-6 p-8 bg-white text-slate-900 rounded-2xl shadow-xl flex flex-col items-center text-center border-4 border-slate-900">
          <img src="/logo.png" alt="Spice Hub" className="w-20 h-20 mb-2" />
          <div className="uppercase tracking-widest text-[11px] font-black text-brand-600 mb-1">
            {cardData.restaurant_name}
          </div>
          <div className="text-3xl font-black tracking-tight text-slate-950 mb-4">
            {cardData.display_name}
          </div>

          {/* QR Code Container */}
          <div className="p-4 bg-slate-50 border-2 border-slate-200 rounded-2xl mb-4 shadow-inner">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?size=220x220&data=${encodeURIComponent(
                cardData.ordering_url
              )}`}
              alt={`QR for ${cardData.display_name}`}
              className="w-48 h-48 block"
            />
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
