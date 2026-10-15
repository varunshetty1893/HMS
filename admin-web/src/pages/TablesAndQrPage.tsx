import React, { useEffect, useState } from 'react';
import { tablesQrApi } from '@/api/tablesQrApi';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ConfirmModal } from '@/components/common/ConfirmModal';
import { PrintableQrCardModal } from '@/components/qr/PrintableQrCardModal';
import {
  Layers,
  Plus,
  Power,
  Printer,
  QrCode,
  RefreshCw,
  Trash2,
  Users,
  X,
} from 'lucide-react';
import { QrPrintCardResponse, RestaurantTable } from '@/types/api';
import { usePageTheme } from '@/hooks/usePageTheme';

export const TablesAndQrPage: React.FC = () => {
  const { L, heading, sub, muted, border, card, cardInner } = usePageTheme();
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

  // Delete Confirmation Modal
  const [tableToDelete, setTableToDelete] = useState<RestaurantTable | null>(null);

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

  const handleToggleActive = async (table: RestaurantTable) => {
    try {
      await tablesQrApi.updateTable(table.id, { is_active: !table.is_active });
      fetchTables();
    } catch (err: any) {
      alert(err?.message || 'Failed to update table');
    }
  };

  // Errors are re-thrown so the confirm dialog shows them inline (no browser alert).
  const handleConfirmDelete = async () => {
    if (!tableToDelete) return;
    await tablesQrApi.deleteTable(tableToDelete.id);
    setTableToDelete(null);
    fetchTables();
  };

  // Used when the table has order history: hide it instead of deleting it.
  const handleDeactivateInstead = async () => {
    if (!tableToDelete) return;
    await tablesQrApi.updateTable(tableToDelete.id, { is_active: false });
    setTableToDelete(null);
    fetchTables();
  };

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight" style={{ color: heading }}>Dining Tables & QR Management</h1>
          <p className="text-sm mt-1" style={{ color: sub }}>
            Add or remove tables, turn them on or off, and print the QR card for each table
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
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
          {error}
        </div>
      )}

      {/* Tables Grid */}
      {isLoading ? (
        <div className="p-12 text-center" style={{ color: muted }}>Loading tables...</div>
      ) : tables.length === 0 ? (
        <div className="p-12 text-center rounded-3xl" style={{ ...card, color: muted }}>
          No dining tables configured yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {tables.map((table) => (
            <div
              key={table.id}
              className="p-6 rounded-3xl shadow-sm flex flex-col justify-between transition hover:shadow-md"
              style={{ ...card, opacity: table.is_active ? 1 : 0.6 }}
            >
              <div>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xl font-black" style={{ color: heading }}>{table.display_name}</span>
                    <span className="text-xs font-mono" style={{ color: muted }}>#{table.table_number}</span>
                  </div>
                  <StatusBadge
                    status={table.is_active ? table.occupancy_status || 'AVAILABLE' : 'DISABLED'}
                    size="sm"
                  />
                </div>

                <div className="mt-3 flex items-center gap-3 text-xs" style={{ color: sub }}>
                  <span className="flex items-center gap-1">
                    <Users className="w-3.5 h-3.5" style={{ color: muted }} />
                    <span>{table.seating_capacity || 4} seats</span>
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Layers className="w-3.5 h-3.5" style={{ color: muted }} />
                    <span>{table.floor_or_zone || 'Floor'}</span>
                  </span>
                </div>

                {/* QR Metadata */}
                <div className="mt-4 p-3 rounded-2xl flex items-center justify-between text-xs font-mono" style={cardInner}>
                  <div className="flex items-center gap-2">
                    <QrCode className="w-4 h-4 text-brand-600" />
                    <span style={{ color: heading }}>v{table.active_qr_version || 1}</span>
                  </div>
                  <span className="text-[11px]" style={{ color: muted }}>{table.active_qr_prefix || 'prefix-**'}</span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-6 pt-4 border-t flex items-center justify-between gap-2" style={{ borderTopColor: border }}>
                <button
                  onClick={() => handleOpenPrintCard(table)}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl text-xs font-semibold transition cursor-pointer"
                  style={{
                    backgroundColor: L ? '#f5f0e8' : '#1e293b',
                    color: heading,
                    border: `1px solid ${border}`,
                  }}
                >
                  <Printer className="w-3.5 h-3.5" />
                  <span>Print QR</span>
                </button>
                <button
                  onClick={() => setTableToRegenerate(table)}
                  title="Rotate QR Token"
                  className="p-2 rounded-xl text-xs font-semibold text-amber-600 hover:bg-amber-50 border border-amber-200 transition cursor-pointer"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleToggleActive(table)}
                  title={table.is_active ? 'Make inactive (hide this table)' : 'Make active again'}
                  className={`p-2 rounded-xl text-xs font-semibold border transition cursor-pointer ${
                    table.is_active
                      ? 'text-emerald-600 border-emerald-200 hover:bg-emerald-50'
                      : 'text-slate-500 border-slate-300 hover:bg-slate-100'
                  }`}
                >
                  <Power className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setTableToDelete(table)}
                  title="Delete table"
                  className="p-2 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 border border-rose-200 transition cursor-pointer"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Table Modal */}
      {isAddTableOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-3xl p-6 shadow-2xl" style={card}>
            <div className="flex items-center justify-between pb-4 border-b" style={{ borderBottomColor: border }}>
              <h3 className="text-lg font-bold" style={{ color: heading }}>Create Dining Table</h3>
              <button onClick={() => setIsAddTableOpen(false)} style={{ color: muted }} className="cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateTable} className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Table Number</label>
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
                    className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none"
                    style={{
                      backgroundColor: L ? '#faf7f2' : '#0f172a',
                      border: `1.5px solid ${border}`,
                      color: heading,
                    }}
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Seating Capacity</label>
                  <input
                    type="number"
                    value={seatingCapacity}
                    onChange={(e) => setSeatingCapacity(Number(e.target.value))}
                    min={1}
                    max={30}
                    className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none"
                    style={{
                      backgroundColor: L ? '#faf7f2' : '#0f172a',
                      border: `1.5px solid ${border}`,
                      color: heading,
                    }}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Display Label</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Table 12"
                  required
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm focus:outline-none"
                  style={{
                    backgroundColor: L ? '#faf7f2' : '#0f172a',
                    border: `1.5px solid ${border}`,
                    color: heading,
                  }}
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Floor / Section</label>
                <input
                  type="text"
                  value={floorOrZone}
                  onChange={(e) => setFloorOrZone(e.target.value)}
                  placeholder="Ground Floor, Rooftop, Terrace..."
                  className="w-full px-3.5 py-2.5 rounded-xl text-sm focus:outline-none"
                  style={{
                    backgroundColor: L ? '#faf7f2' : '#0f172a',
                    border: `1.5px solid ${border}`,
                    color: heading,
                  }}
                />
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsAddTableOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium transition cursor-pointer"
                  style={{ color: sub }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-md cursor-pointer"
                >
                  Create & Generate QR v1
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* QR Card Modal */}
      <PrintableQrCardModal cardData={selectedCard} onClose={() => setSelectedCard(null)} />

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={!!tableToDelete}
        title={`Delete ${tableToDelete?.display_name ?? 'table'}?`}
        description="This removes the table and its QR code for good. Tables that already have orders cannot be deleted, but you can deactivate them (hidden, history kept)."
        confirmLabel="Delete table"
        variant="danger"
        onConfirm={handleConfirmDelete}
        onCancel={() => setTableToDelete(null)}
        fallbackAction={{
          errorCode: 'TABLE_HAS_HISTORY',
          label: 'Deactivate instead',
          onClick: handleDeactivateInstead,
        }}
      />

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
