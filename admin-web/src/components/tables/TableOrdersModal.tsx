import React, { useEffect, useState } from 'react';
import {
  AlertCircle,
  Check,
  Flame,
  Layers,
  Pencil,
  RefreshCw,
  Users,
  UtensilsCrossed,
  X,
} from 'lucide-react';
import { tablesQrApi } from '@/api/tablesQrApi';
import { ordersBillsApi } from '@/api/ordersBillsApi';
import { RestaurantTable, Order, OrderItem } from '@/types/api';
import { formatInr } from '@/utils/currency';
import { StatusBadge } from '@/components/common/StatusBadge';
import { usePageTheme } from '@/hooks/usePageTheme';

interface TableOrdersModalProps {
  table: RestaurantTable | null;
  onClose: () => void;
  onTableUpdated?: () => void;
}

interface FlattenedDishItem {
  orderId: string;
  orderNumber: string;
  orderVersion: number;
  orderStatus: string;
  orderSource: string;
  placedAt: string;
  item: OrderItem;
}

export const TableOrdersModal: React.FC<TableOrdersModalProps> = ({
  table,
  onClose,
  onTableUpdated,
}) => {
  const { L, heading, sub, muted, border } = usePageTheme();

  const [sessionDetail, setSessionDetail] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Price Edit Inline State
  const [editingItemId, setEditingItemId] = useState<string | null>(null);
  const [editPriceValue, setEditPriceValue] = useState<string>('');
  const [editReasonValue, setEditReasonValue] = useState<string>('');
  const [isSavingPrice, setIsSavingPrice] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const fetchSession = async () => {
    if (!table) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await tablesQrApi.getTableSession(table.id);
      setSessionDetail(data);
    } catch (err: any) {
      setError(err?.message || 'Failed to load table orders and bill information.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (table) {
      fetchSession();
      setEditingItemId(null);
      setSaveError(null);
    }
  }, [table?.id]);

  if (!table) return null;

  // Flatten active order items across all orders in the session
  const orders: Order[] = sessionDetail?.orders || [];
  const allDishes: FlattenedDishItem[] = [];

  orders.forEach((ord) => {
    (ord.items || []).forEach((it) => {
      allDishes.push({
        orderId: ord.id,
        orderNumber: ord.order_number,
        orderVersion: ord.version || 1,
        orderStatus: ord.status,
        orderSource: ord.source,
        placedAt: ord.placed_at,
        item: it,
      });
    });
  });

  const totalOutstanding =
    sessionDetail?.current_outstanding_amount !== undefined
      ? parseFloat(sessionDetail.current_outstanding_amount)
      : orders.reduce((acc, o) => acc + (parseFloat(o.order_subtotal) || 0), 0);

  const handleStartEdit = (dish: FlattenedDishItem) => {
    const raw = dish.item as any;
    const currentPrice = raw.unit_price_snapshot || raw.unit_price || '0.00';
    setEditingItemId(dish.item.id);
    setEditPriceValue(parseFloat(currentPrice).toFixed(2));
    setEditReasonValue('Price adjusted by admin');
    setSaveError(null);
  };

  const handleSavePrice = async (dish: FlattenedDishItem) => {
    const newPriceNum = parseFloat(editPriceValue);
    if (isNaN(newPriceNum) || newPriceNum < 0) {
      setSaveError('Please enter a valid price (greater than or equal to 0).');
      return;
    }

    setIsSavingPrice(true);
    setSaveError(null);
    try {
      await ordersBillsApi.adjustOrderItem(dish.orderId, dish.item.id, {
        expected_version: dish.orderVersion,
        adjustment_type: 'CUSTOM_PRICE',
        custom_unit_price: newPriceNum,
        reason: editReasonValue.trim() || 'Price adjusted by admin',
      });

      setSuccessBanner(
        `Updated price for ${(dish.item as any).item_name || (dish.item as any).item_name_snapshot || 'dish'} to ${formatInr(newPriceNum)}.`
      );
      setEditingItemId(null);
      await fetchSession();
      onTableUpdated?.();
      setTimeout(() => setSuccessBanner(null), 4000);
    } catch (err: any) {
      setSaveError(err?.message || 'Failed to update item price.');
    } finally {
      setIsSavingPrice(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs animate-in fade-in">
      <div
        className="w-full max-w-4xl rounded-3xl shadow-2xl border flex flex-col overflow-hidden max-h-[90vh] animate-in zoom-in-95"
        style={{
          backgroundColor: L ? '#ffffff' : '#0f172a',
          borderColor: border,
        }}
      >
        {/* Header */}
        <div
          className="p-6 border-b flex items-start justify-between gap-4"
          style={{
            backgroundColor: L ? '#f8f9fa' : '#1e293b',
            borderColor: border,
          }}
        >
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-black" style={{ color: heading }}>
                {table.display_name} (Table #{table.table_number})
              </h2>
              <StatusBadge
                status={
                  sessionDetail?.session_status === 'ACTIVE'
                    ? 'OCCUPIED'
                    : table.current_occupancy || table.occupancy_status || 'OCCUPIED'
                }
              />
              {sessionDetail?.session_code && (
                <span
                  className="px-2.5 py-1 rounded-lg text-xs font-mono font-bold"
                  style={{
                    backgroundColor: L ? '#e2e8f0' : '#334155',
                    color: heading,
                  }}
                >
                  {sessionDetail.session_code}
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 mt-2 text-xs" style={{ color: sub }}>
              <span className="flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" style={{ color: muted }} />
                <span>{table.seating_capacity || 4} Seats</span>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5" style={{ color: muted }} />
                <span>{table.floor_or_zone || 'Floor'}</span>
              </span>
              <span>•</span>
              <span className="flex items-center gap-1.5 font-mono font-bold text-brand-600">
                <UtensilsCrossed className="w-3.5 h-3.5" />
                <span>{orders.length} Active Orders ({allDishes.length} Items)</span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={fetchSession}
              disabled={isLoading}
              title="Refresh table orders"
              className="p-2 rounded-xl border transition cursor-pointer hover:bg-slate-100"
              style={{ borderColor: border, color: heading }}
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-xl text-gray-400 hover:text-gray-700 hover:bg-gray-100 cursor-pointer transition"
              title="Close"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Success Banner */}
        {successBanner && (
          <div className="px-6 py-2.5 bg-emerald-50 border-b border-emerald-200 text-xs font-bold text-emerald-800 flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600 shrink-0" />
            <span>{successBanner}</span>
          </div>
        )}

        {/* Global Error Banner */}
        {saveError && (
          <div className="px-6 py-2.5 bg-rose-50 border-b border-rose-200 text-xs font-bold text-rose-800 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{saveError}</span>
          </div>
        )}

        {/* Body Content */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {isLoading ? (
            <div className="py-16 flex flex-col items-center justify-center gap-3" style={{ color: muted }}>
              <div className="w-8 h-8 border-4 border-t-transparent rounded-full animate-spin border-brand-500" />
              <span className="text-sm">Loading table orders & bill...</span>
            </div>
          ) : error ? (
            <div className="p-6 rounded-2xl bg-rose-50 border border-rose-200 text-rose-700 text-center">
              <p className="font-semibold text-sm mb-2">{error}</p>
              <button
                onClick={fetchSession}
                className="px-4 py-2 rounded-xl text-xs font-bold bg-rose-600 text-white cursor-pointer"
              >
                Retry Loading
              </button>
            </div>
          ) : allDishes.length === 0 ? (
            <div className="p-12 text-center rounded-2xl border" style={{ borderColor: border, color: muted }}>
              <UtensilsCrossed className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <h3 className="text-base font-bold mb-1" style={{ color: heading }}>
                No Active Dishes Ordered
              </h3>
              <p className="text-xs max-w-sm mx-auto">
                This table currently has no active orders placed by guests or staff.
              </p>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-bold uppercase tracking-wider" style={{ color: muted }}>
                  Current Orders & Dishes ({allDishes.length})
                </h3>
                <span className="text-xs font-mono font-bold text-brand-600">
                  Click the pencil icon on any item to update its bill price
                </span>
              </div>

              <div
                className="rounded-2xl border overflow-hidden shadow-xs"
                style={{ borderColor: border }}
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr
                        className="border-b font-bold uppercase tracking-wider text-[11px]"
                        style={{
                          backgroundColor: L ? '#f1f5f9' : '#1e293b',
                          borderColor: border,
                          color: muted,
                        }}
                      >
                        <th className="py-3 px-4">Dish / Item</th>
                        <th className="py-3 px-4">Order #</th>
                        <th className="py-3 px-4">Status</th>
                        <th className="py-3 px-4 text-center">Qty</th>
                        <th className="py-3 px-4 text-right">Unit Price</th>
                        <th className="py-3 px-4 text-right">Line Total</th>
                        <th className="py-3 px-4 text-center">Price Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y" style={{ borderColor: border }}>
                      {allDishes.map((dish, idx) => {
                        const raw = dish.item as any;
                        const itemName = dish.item.item_name || raw.item_name_snapshot || 'Dish';
                        const itemCode = dish.item.item_code || raw.item_code_snapshot || '';
                        const variantName = dish.item.variant_name || raw.variant_name_snapshot || '';
                        const unitPrice = parseFloat(raw.unit_price_snapshot || raw.unit_price || 0);
                        const lineSubtotal = parseFloat(raw.line_subtotal || 0);
                        const activeQty = raw.active_quantity ?? raw.quantity ?? 1;
                        const isEditingThis = editingItemId === dish.item.id;

                        return (
                          <tr
                            key={dish.item.id || `dish-${idx}`}
                            className="transition"
                            style={{
                              backgroundColor: isEditingThis
                                ? L ? '#fffbeb' : '#1e201e'
                                : 'transparent',
                            }}
                          >
                            <td className="py-3.5 px-4 font-semibold">
                              <div className="flex flex-col">
                                <div className="flex items-center gap-1.5 flex-wrap">
                                  <span style={{ color: heading }} className="text-sm font-bold">
                                    {itemName}
                                  </span>
                                  {itemCode && (
                                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-orange-100 text-orange-800 border border-orange-200">
                                      {itemCode}
                                    </span>
                                  )}
                                </div>
                                {variantName && (
                                  <span className="text-[11px]" style={{ color: muted }}>
                                    Portion / Variant: {variantName}
                                  </span>
                                )}
                                {dish.item.item_notes && (
                                  <span className="text-[11px] text-amber-600 italic">
                                    Note: "{dish.item.item_notes}"
                                  </span>
                                )}
                              </div>
                            </td>

                            <td className="py-3.5 px-4 font-mono font-bold" style={{ color: heading }}>
                              <div className="flex items-center gap-1.5">
                                <Flame className="w-3.5 h-3.5 text-brand-500 shrink-0" />
                                <span>{dish.orderNumber}</span>
                              </div>
                            </td>

                            <td className="py-3.5 px-4">
                              <StatusBadge status={dish.orderStatus} size="sm" />
                            </td>

                            <td className="py-3.5 px-4 text-center font-bold" style={{ color: heading }}>
                              {activeQty}x
                            </td>

                            <td className="py-3.5 px-4 text-right font-mono font-bold">
                              {isEditingThis ? (
                                <div className="flex flex-col items-end gap-1">
                                  <div className="flex items-center gap-1">
                                    <span style={{ color: muted }}>₹</span>
                                    <input
                                      type="number"
                                      step="0.01"
                                      min="0"
                                      value={editPriceValue}
                                      onChange={(e) => setEditPriceValue(e.target.value)}
                                      className="w-24 px-2 py-1 rounded-lg border font-mono font-bold text-xs text-right focus:outline-none focus:border-brand-500"
                                      style={{
                                        backgroundColor: L ? '#ffffff' : '#0f172a',
                                        borderColor: border,
                                        color: heading,
                                      }}
                                    />
                                  </div>
                                </div>
                              ) : (
                                <span style={{ color: heading }}>
                                  {formatInr(unitPrice)}
                                </span>
                              )}
                            </td>

                            <td className="py-3.5 px-4 text-right font-mono font-black text-sm" style={{ color: heading }}>
                              {formatInr(lineSubtotal)}
                            </td>

                            <td className="py-3.5 px-4 text-center">
                              {isEditingThis ? (
                                <div className="flex items-center justify-center gap-1.5">
                                  <button
                                    onClick={() => handleSavePrice(dish)}
                                    disabled={isSavingPrice}
                                    title="Save new price for this bill"
                                    className="px-2.5 py-1 rounded-lg text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 transition cursor-pointer shadow-xs flex items-center gap-1 disabled:opacity-50"
                                  >
                                    <Check className="w-3.5 h-3.5" />
                                    <span>Save</span>
                                  </button>
                                  <button
                                    onClick={() => setEditingItemId(null)}
                                    disabled={isSavingPrice}
                                    className="px-2 py-1 rounded-lg text-xs font-semibold hover:bg-slate-200 transition cursor-pointer text-slate-500"
                                  >
                                    Cancel
                                  </button>
                                </div>
                              ) : (
                                <button
                                  onClick={() => handleStartEdit(dish)}
                                  title="Edit price for this item"
                                  className="px-2.5 py-1 rounded-lg text-xs font-semibold text-brand-600 hover:text-brand-800 hover:bg-brand-50 border border-brand-200 transition cursor-pointer flex items-center gap-1 mx-auto"
                                >
                                  <Pencil className="w-3 h-3" />
                                  <span>Edit Price</span>
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer / Bill Summary */}
        <div
          className="p-6 border-t flex flex-col sm:flex-row items-center justify-between gap-4"
          style={{
            backgroundColor: L ? '#f8f9fa' : '#1e293b',
            borderColor: border,
          }}
        >
          <div>
            <span className="text-xs uppercase font-bold tracking-wider" style={{ color: muted }}>
              Total Unpaid Spend
            </span>
            <div className="text-2xl font-black font-mono text-brand-600">
              {formatInr(totalOutstanding)}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 rounded-xl text-xs font-bold border transition cursor-pointer hover:bg-slate-200"
              style={{
                borderColor: border,
                color: heading,
              }}
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
