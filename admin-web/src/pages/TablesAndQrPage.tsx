import React, { useEffect, useState } from 'react';
import { tablesQrApi } from '@/api/tablesQrApi';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ConfirmModal } from '@/components/common/ConfirmModal';
import { PrintableQrCardModal } from '@/components/qr/PrintableQrCardModal';
import {
  Layers,
  Plus,
  Printer,
  QrCode,
  RefreshCw,
  Users,
  X,
} from 'lucide-react';
import { QrPrintCardResponse, RestaurantTable } from '@/types/api';

export const TablesAndQrPage: React.FC = () => {
  const [tables, setTables] = useState<RestaurantTable[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Table Modal
  const [isAddTableOpen, setIsAddTableOpen] = useState(false);
  const [tableNumber, setTableNumber] = useState<number>(1);
  const [displayName, setDisplayName] = useState('');
  const [seatingCapacity, setSeatingCapacity] = useState<number>(4);
  const [floorOrZone, setFloorOrZone] = useState('Ground Floor');

  // Printable Card Modal
  const [selectedCard, setSelectedCard] = useState<QrPrintCardResponse | null>(null);

  // Regenerate Confirmation Modal
  const [tableToRegenerate, setTableToRegenerate] = useState<RestaurantTable | null>(null);

  const fetchTables = async () => {
    setIsLoading(true);
    try {
      const data = await tablesQrApi.listTables(false);
      setTables(data);
      if (data.length > 0) {
        setTableNumber(Math.max(...data.map((t) => t.table_number)) + 1);
      }
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch table records');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchTables();
  }, []);

  const handleCreateTable = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await tablesQrApi.createTable({
        table_number: Number(tableNumber),
        display_name: displayName.trim() || `Table ${tableNumber}`,
        seating_capacity: Number(seatingCapacity) || 4,
        floor_or_zone: floorOrZone.trim() || null,
      });
      setIsAddTableOpen(false);
      setDisplayName('');
      fetchTables();
    } catch (err: any) {
      alert(err?.message || 'Failed to create table');
    }
  };

  const handleOpenPrintCard = async (table: RestaurantTable) => {
    try {
      const card = await tablesQrApi.getPrintableQrCard(table.id);
      setSelectedCard(card);
    } catch (err: any) {
      alert(err?.message || 'Failed to load printable QR details');
    }
  };

  const handleConfirmRegenerate = async (reason?: string) => {
    if (!tableToRegenerate) return;
    try {
      await tablesQrApi.regenerateQr(tableToRegenerate.id, reason || 'ROTATED_BY_ADMIN');
      alert(`QR rotated for Table ${tableToRegenerate.table_number}. The old QR token is now immediately invalid (410 Gone).`);
      setTableToRegenerate(null);
      fetchTables();
    } catch (err: any) {
      alert(err?.message || 'Failed to regenerate QR token');
    }
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight text-ink">Dining Tables & QR Management</h1>
          <p className="text-sm text-slate-400 mt-1">
            Physical table registry, cryptographic QR token rotation, and printable standees
          </p>
        </div>
        <button
          onClick={() => setIsAddTableOpen(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-600/30 transition cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Add Dining Table</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
          {error}
        </div>
      )}

      {/* Tables Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-500">Loading tables...</div>
      ) : tables.length === 0 ? (
        <div className="p-12 text-center rounded-3xl bg-slate-900/40 border border-slate-800 text-slate-400">
          No dining tables configured yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {tables.map((table) => (
            <div
              key={table.id}
              className="p-6 rounded-3xl bg-slate-900/90 border border-slate-800 shadow-xl flex flex-col justify-between hover:border-slate-700 transition"
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl font-black text-ink">{table.display_name}</span>
                    <span className="text-xs font-mono text-slate-500">#{table.table_number}</span>
                  </div>
                  <StatusBadge status={table.occupancy_status || 'AVAILABLE'} size="sm" />
                </div>

                <div className="mt-3 flex items-center gap-3 text-xs text-slate-400">
                  <span className="flex items-center gap-1">
                    <Users className="w-3.5 h-3.5 text-slate-500" />
                    <span>{table.seating_capacity || 4} seats</span>
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5 text-slate-500" />
                    <span>{table.floor_or_zone || 'Floor'}</span>
                  </span>
                </div>

                {/* QR Metadata */}
                <div className="mt-4 p-3 rounded-2xl bg-slate-950/70 border border-slate-800/60 flex items-center justify-between text-xs font-mono">
                  <div className="flex items-center gap-2">
                    <QrCode className="w-4 h-4 text-brand-400" />
                    <span className="text-slate-300">v{table.active_qr_version || 1}</span>
                  </div>
                  <span className="text-[11px] text-slate-500">{table.active_qr_prefix || 'prefix-**'}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between gap-2">
                <button
                  onClick={() => handleOpenPrintCard(table)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Standee</span>
                </button>
                <button
                  onClick={() => setTableToRegenerate(table)}
                  title="Rotate QR Token"
                  className="p-2 rounded-xl text-xs font-semibold text-amber-400 hover:bg-amber-950/30 border border-amber-900/40 transition"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Table Modal */}
      {isAddTableOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-3xl bg-slate-900 border border-slate-800 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-ink">Create Dining Table</h3>
              <button onClick={() => setIsAddTableOpen(false)} className="text-slate-400 hover:text-ink">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateTable} className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Table Number</label>
                  <input
                    type="number"
                    value={tableNumber}
                    onChange={(e) => {
                      const num = Number(e.target.value);
                      setTableNumber(num);
                      setDisplayName(`Table ${num}`);
                    }}
                    required
                    min={1}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm font-mono text-ink focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Seating Capacity</label>
                  <input
                    type="number"
                    value={seatingCapacity}
                    onChange={(e) => setSeatingCapacity(Number(e.target.value))}
                    min={1}
                    max={30}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm font-mono text-ink focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Display Label</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Table 12"
                  required
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-ink focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Floor / Section</label>
                <input
                  type="text"
                  value={floorOrZone}
                  onChange={(e) => setFloorOrZone(e.target.value)}
                  placeholder="Ground Floor, Rooftop, Terrace..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-ink focus:outline-none focus:border-brand-500"
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddTableOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium text-slate-300 hover:bg-slate-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white"
                >
                  Create & Generate QR v1
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Standee Modal */}
      <PrintableQrCardModal cardData={selectedCard} onClose={() => setSelectedCard(null)} />

      {/* Rotate Confirmation Modal */}
      <ConfirmModal
        isOpen={!!tableToRegenerate}
        title={`Rotate QR for Table ${tableToRegenerate?.table_number}`}
        description="Rotating will issue a new cryptographic QR token version (v+1) and immediately invalidate the current printed QR standee (410 Gone). Guests scanning the old QR will be rejected."
        confirmLabel="Rotate Token Now"
        requireReason={true}
        reasonPlaceholder="Printed standee replaced / suspected photo leak..."
        variant="warning"
        onConfirm={handleConfirmRegenerate}
        onCancel={() => setTableToRegenerate(null)}
      />
    </div>
  );
};
