import React, { useMemo, useState } from 'react';
import {
  AlertCircle,
  History,
  PlusCircle,
  Sliders,
  Tag,
  X,
} from 'lucide-react';
import { formatInr } from '@/utils/currency';
import { formatDateTimeIst } from '@/utils/dateIst';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Order, OrderItem, OrderItemAdjustmentRequest } from '@/types/api';
import { ordersBillsApi } from '@/api/ordersBillsApi';

interface OrderDetailDrawerProps {
  order: Order | null;
  onClose: () => void;
  onRequestVoid?: (order: Order) => void;
  onOrderUpdated?: (order: Order) => void;
}

export const OrderDetailDrawer: React.FC<OrderDetailDrawerProps> = ({
  order,
  onClose,
  onRequestVoid,
  onOrderUpdated,
}) => {
  const [activeOrder, setActiveOrder] = useState<Order | null>(order);

  React.useEffect(() => {
    setActiveOrder(order);
  }, [order]);

  // Adjustment Modal State
  const [adjustingItem, setAdjustingItem] = useState<OrderItem | null>(null);
  const [adjType, setAdjType] = useState<string>('CUSTOM_PORTION');
  const [customPortionName, setCustomPortionName] = useState('');
  const [customPrice, setCustomPrice] = useState('');
  const [extraPieces, setExtraPieces] = useState(1);
  const [extraPiecePrice, setExtraPiecePrice] = useState('');
  const [discountPercent, setDiscountPercent] = useState('10');
  const [discountAmount, setDiscountAmount] = useState('10');
  const [surchargeAmount, setSurchargeAmount] = useState('20');
  const [adjReason, setAdjReason] = useState('');
  const [isSubmittingAdj, setIsSubmittingAdj] = useState(false);
  const [adjError, setAdjError] = useState<string | null>(null);

  if (!activeOrder) return null;

  const canCancel =
    activeOrder.status !== 'COMPLETED' &&
    activeOrder.status !== 'CANCELLED' &&
    activeOrder.status !== 'REJECTED';

  const canAdjust =
    activeOrder.status !== 'COMPLETED' &&
    activeOrder.status !== 'CANCELLED' &&
    activeOrder.status !== 'REJECTED';

  const formatSourceLabel = (src: string) => {
    if (src === 'CUSTOMER_QR') return 'Customer QR';
    if (src === 'WAITER') return 'Waiter App';
    return src;
  };

  const formatModType = (mod: string) => {
    switch (mod) {
      case 'ITEM_QUANTITY_INCREASED':
        return 'Quantity Increased';
      case 'ITEM_QUANTITY_DECREASED':
        return 'Quantity Reduced';
      case 'ITEM_CANCELLED':
        return 'Dish Cancelled';
      case 'ORDER_CANCELLED':
        return 'Order Cancelled';
      case 'PRICE_ADJUSTED':
        return 'Price Adjusted';
      case 'PORTION_CHANGED':
        return 'Portion Changed';
      case 'EXTRA_PIECES_ADDED':
        return 'Extra Pieces Added';
      case 'DISCOUNT_APPLIED':
        return 'Discount Applied';
      default:
        return mod.replace(/_/g, ' ');
    }
  };

  const openAdjustmentModal = (item: OrderItem) => {
    setAdjustingItem(item);
    const hasCustomPortion = Boolean(item.custom_portion_name);
    const hasExtra = (item.extra_pieces_count || 0) > 0;
    const defaultType = hasCustomPortion ? 'CUSTOM_PORTION' : hasExtra ? 'EXTRA_PIECES' : 'CUSTOM_PORTION';
    setAdjType(defaultType);
    setCustomPortionName(item.custom_portion_name || 'Half Portion');
    const baseP = parseFloat(item.base_price_snapshot || item.unit_price_snapshot) || 0;
    setCustomPrice(baseP > 0 ? (baseP / 2).toFixed(2) : '0.00');
    setExtraPieces(item.extra_pieces_count && item.extra_pieces_count > 0 ? item.extra_pieces_count : 1);
    setExtraPiecePrice(item.extra_piece_price ? String(parseFloat(item.extra_piece_price)) : '20');
    setDiscountPercent('10');
    setDiscountAmount('10');
    setSurchargeAmount('20');
    setAdjReason('');
    setAdjError(null);
  };

  // Live Recalculation Preview
  const preview = useMemo(() => {
    if (!adjustingItem) return null;
    const basePrice = parseFloat(adjustingItem.base_price_snapshot || adjustingItem.unit_price_snapshot) || 0;
    const activeQty = adjustingItem.active_quantity || 1;
    let newUnitPrice = basePrice;

    if (adjType === 'CUSTOM_PORTION') {
      const p = parseFloat(customPrice);
      newUnitPrice = !isNaN(p) && p >= 0 ? p : basePrice;
    } else if (adjType === 'EXTRA_PIECES') {
      const epPrice = parseFloat(extraPiecePrice) || 0;
      const count = Number(extraPieces) || 0;
      newUnitPrice = basePrice + count * epPrice;
    } else if (adjType === 'DISCOUNT_PERCENT') {
      const pct = parseFloat(discountPercent) || 0;
      newUnitPrice = Math.max(0, basePrice - (basePrice * pct) / 100);
    } else if (adjType === 'DISCOUNT_FIXED') {
      const amt = parseFloat(discountAmount) || 0;
      newUnitPrice = Math.max(0, basePrice - amt);
    } else if (adjType === 'SURCHARGE_FIXED') {
      const amt = parseFloat(surchargeAmount) || 0;
      newUnitPrice = basePrice + amt;
    } else if (adjType === 'CUSTOM_PRICE') {
      const p = parseFloat(customPrice);
      newUnitPrice = !isNaN(p) && p >= 0 ? p : basePrice;
    }

    const currentLineTotal = parseFloat(adjustingItem.line_subtotal) || 0;
    const newLineTotal = activeQty * newUnitPrice;
    const lineDelta = newLineTotal - currentLineTotal;
    const currentOrderSubtotal = parseFloat(activeOrder.order_subtotal || '0') || 0;
    const projectedOrderSubtotal = Math.max(0, currentOrderSubtotal + lineDelta);

    return {
      basePrice,
      currentUnitPrice: parseFloat(adjustingItem.unit_price_snapshot) || basePrice,
      newUnitPrice,
      currentLineTotal,
      newLineTotal,
      lineDelta,
      currentOrderSubtotal,
      projectedOrderSubtotal,
    };
  }, [
    adjustingItem,
    adjType,
    customPrice,
    extraPieces,
    extraPiecePrice,
    discountPercent,
    discountAmount,
    surchargeAmount,
    activeOrder?.order_subtotal,
  ]);

  const handleSaveAdjustment = async () => {
    if (!activeOrder || !adjustingItem) return;
    if (!adjReason.trim()) {
      setAdjError('Please enter a mandatory reason for this adjustment.');
      return;
    }
    if (adjReason.includes('<') || adjReason.includes('>')) {
      setAdjError('Reason cannot contain < or > characters.');
      return;
    }

    const payload: OrderItemAdjustmentRequest = {
      expected_version: activeOrder.version,
      adjustment_type: adjType,
      reason: adjReason.trim(),
    };

    if (adjType === 'CUSTOM_PORTION') {
      if (!customPortionName.trim()) {
        setAdjError('Please enter the portion name (e.g. Half Portion).');
        return;
      }
      const p = parseFloat(customPrice);
      if (isNaN(p) || p < 0) {
        setAdjError('Please enter a valid price for the custom portion.');
        return;
      }
      payload.custom_portion_name = customPortionName.trim();
      payload.custom_unit_price = p;
    } else if (adjType === 'EXTRA_PIECES') {
      const count = Number(extraPieces);
      if (isNaN(count) || count <= 0) {
        setAdjError('Extra pieces count must be at least 1.');
        return;
      }
      payload.extra_pieces = count;
    } else if (adjType === 'DISCOUNT_PERCENT') {
      const pct = parseFloat(discountPercent);
      if (isNaN(pct) || pct <= 0 || pct > 100) {
        setAdjError('Discount percentage must be between 1 and 100.');
        return;
      }
      payload.discount_percent = pct;
    } else if (adjType === 'DISCOUNT_FIXED') {
      const amt = parseFloat(discountAmount);
      if (isNaN(amt) || amt <= 0) {
        setAdjError('Discount amount must be greater than 0.');
        return;
      }
      payload.discount_amount = amt;
    } else if (adjType === 'SURCHARGE_FIXED') {
      const amt = parseFloat(surchargeAmount);
      if (isNaN(amt) || amt <= 0) {
        setAdjError('Surcharge amount must be greater than 0.');
        return;
      }
      payload.surcharge_amount = amt;
    } else if (adjType === 'CUSTOM_PRICE') {
      const p = parseFloat(customPrice);
      if (isNaN(p) || p < 0) {
        setAdjError('Please enter a valid price.');
        return;
      }
      payload.custom_unit_price = p;
    }

    setIsSubmittingAdj(true);
    setAdjError(null);
    try {
      const updated = await ordersBillsApi.adjustOrderItem(
        activeOrder.id,
        adjustingItem.id,
        payload
      );
      setActiveOrder(updated);
      setAdjustingItem(null);
      onOrderUpdated?.(updated);
    } catch (err: any) {
      setAdjError(err?.message || 'Failed to apply adjustment');
    } finally {
      setIsSubmittingAdj(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/40 backdrop-blur-xs">
      <div className="w-full max-w-lg bg-white border-l border-gray-200 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-bold text-gray-900">{activeOrder.order_number}</h2>
              <StatusBadge status={activeOrder.status} />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Table #{activeOrder.table_number || '—'} • Ordered via: {formatSourceLabel(activeOrder.source)} • Placed: {formatDateTimeIst(activeOrder.placed_at)}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-gray-400 hover:text-gray-700 cursor-pointer"
            title="Close details"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Order Items */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-600">
                Ordered Dishes ({activeOrder.items?.length || 0})
              </h3>
              {canAdjust && (
                <span className="text-[11px] font-medium text-brand-600 flex items-center gap-1">
                  <Sliders className="w-3.5 h-3.5" />
                  <span>Flexible Adjustments Enabled</span>
                </span>
              )}
            </div>

            <div className="divide-y divide-gray-100 rounded-2xl border border-gray-200 bg-slate-50 overflow-hidden">
              {activeOrder.items && activeOrder.items.length > 0 ? (
                activeOrder.items.map((item, idx) => {
                  const hasCustomPortion = Boolean(item.custom_portion_name);
                  const hasExtraPieces = (item.extra_pieces_count || 0) > 0;
                  const hasAdjustment = Boolean(item.adjustment_type);
                  const isPriceAltered =
                    item.base_price_snapshot &&
                    Number(item.base_price_snapshot) !== Number(item.unit_price_snapshot);

                  return (
                    <div
                      key={item.id || item.item_code || `item-${idx}`}
                      className="p-3.5 flex flex-col gap-2 bg-white hover:bg-slate-50/50 transition"
                    >
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-mono font-bold text-brand-700 bg-orange-100 px-1.5 py-0.5 rounded border border-orange-200">
                              {item.item_code}
                            </span>
                            <span className="text-sm font-semibold text-gray-900">{item.item_name}</span>
                            <span className="text-xs text-gray-500">({item.variant_name})</span>
                          </div>

                          {/* Adjustment Tags */}
                          {(hasCustomPortion || hasExtraPieces || hasAdjustment) && (
                            <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                              {hasCustomPortion && (
                                <span className="text-[10px] font-bold text-sky-800 bg-sky-50 px-2 py-0.5 rounded border border-sky-200 flex items-center gap-1">
                                  <Tag className="w-2.5 h-2.5" />
                                  <span>Portion: {item.custom_portion_name}</span>
                                </span>
                              )}
                              {hasExtraPieces && (
                                <span className="text-[10px] font-bold text-amber-900 bg-amber-50 px-2 py-0.5 rounded border border-amber-200 flex items-center gap-1">
                                  <PlusCircle className="w-2.5 h-2.5" />
                                  <span>
                                    +{item.extra_pieces_count} extra pc
                                    {item.extra_piece_price ? ` @ ${formatInr(item.extra_piece_price)}` : ''}
                                  </span>
                                </span>
                              )}
                              {hasAdjustment && (
                                <span className="text-[10px] font-semibold text-purple-800 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                                  {item.adjustment_type?.replace(/_/g, ' ')}
                                  {item.adjustment_reason ? ` • "${item.adjustment_reason}"` : ''}
                                </span>
                              )}
                            </div>
                          )}

                          {item.item_notes && (
                            <p className="text-xs text-amber-700 italic">Customer Note: "{item.item_notes}"</p>
                          )}

                          <div className="text-xs text-gray-500 flex items-center gap-2 pt-0.5">
                            <span>
                              Qty: <strong className="text-gray-900">{item.active_quantity}</strong>
                              {item.cancelled_quantity > 0 && (
                                <span className="text-rose-600 ml-1.5 font-medium">
                                  ({item.cancelled_quantity} cancelled)
                                </span>
                              )}
                            </span>
                            <span>•</span>
                            <span>
                              {isPriceAltered && (
                                <span className="line-through text-gray-400 mr-1.5 font-mono">
                                  {formatInr(item.base_price_snapshot || 0)}
                                </span>
                              )}
                              <span className="font-semibold text-gray-900 font-mono">
                                {formatInr(item.unit_price_snapshot)}
                              </span>{' '}
                              each
                            </span>
                          </div>
                        </div>

                        <div className="text-right flex flex-col items-end gap-1.5">
                          <span className="font-mono font-bold text-sm text-gray-900">
                            {formatInr(item.line_subtotal)}
                          </span>
                          {canAdjust && item.active_quantity > 0 && (
                            <button
                              type="button"
                              onClick={() => openAdjustmentModal(item)}
                              className="text-[11px] font-semibold text-brand-600 hover:text-brand-800 hover:bg-brand-50 px-2 py-1 rounded-lg border border-brand-200 transition cursor-pointer flex items-center gap-1"
                              title="Adjust price, portion, or extra pieces for this item"
                            >
                              <Sliders className="w-3 h-3" />
                              <span>Adjust</span>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-6 text-xs text-gray-400 text-center">No dishes attached to this order</div>
              )}
            </div>

            <div className="mt-4 flex items-center justify-between px-2">
              <span className="text-sm text-gray-600">Order Subtotal:</span>
              <span className="text-base font-bold font-mono text-gray-900">
                {formatInr(activeOrder.order_subtotal)}
              </span>
            </div>
          </div>

          {/* Modification History */}
          {activeOrder.modification_events && activeOrder.modification_events.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-gray-600 mb-3">
                <History className="w-4 h-4 text-amber-600" />
                <span>Order Change History ({activeOrder.modification_events.length})</span>
              </div>
              <div className="space-y-2">
                {activeOrder.modification_events.map((ev, idx) => (
                  <div
                    key={ev.id || `ev-${idx}`}
                    className="p-3 rounded-xl border border-amber-200 bg-amber-50 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between text-amber-800 font-semibold">
                      <span>{formatModType(ev.modification_type)}</span>
                      <span className="text-[10px] text-gray-500 font-mono">
                        {formatDateTimeIst(ev.created_at)}
                      </span>
                    </div>
                    <p className="text-gray-700">
                      Quantity: {ev.previous_quantity} → <strong className="text-gray-900">{ev.new_quantity}</strong> changed by{' '}
                      <span className="text-amber-800 font-mono font-semibold">@{ev.modified_by_role}</span>
                      {ev.price_delta && (
                        <span className="ml-2 font-mono font-semibold text-gray-900">
                          (Delta: {Number(ev.price_delta) >= 0 ? '+' : ''}{formatInr(ev.price_delta)})
                        </span>
                      )}
                    </p>
                    {ev.reason && <p className="text-gray-600 italic">"{ev.reason}"</p>}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Reason if cancelled/rejected */}
          {(activeOrder.cancellation_reason || activeOrder.rejection_reason) && (
            <div className="p-4 rounded-xl border border-rose-200 bg-rose-50">
              <div className="flex items-center gap-2 text-rose-700 font-bold text-xs uppercase tracking-wider mb-1">
                <AlertCircle className="w-4 h-4" />
                <span>Reason for Cancellation / Rejection</span>
              </div>
              <p className="text-sm text-rose-800">
                {activeOrder.cancellation_reason || activeOrder.rejection_reason}
              </p>
            </div>
          )}
        </div>

        {/* Footer Emergency Cancel action */}
        {canCancel && onRequestVoid && (
          <div className="p-6 border-t border-gray-200 bg-slate-50">
            <button
              onClick={() => onRequestVoid(activeOrder)}
              className="w-full py-2.5 px-4 rounded-xl text-sm font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-300 transition cursor-pointer"
            >
              Emergency Cancel Order
            </button>
            <p className="text-[11px] text-gray-500 text-center mt-2">
              Cancels the entire order, stops the kitchen, and removes charges from the bill.
            </p>
          </div>
        )}
      </div>

      {/* Item Adjustment Modal */}
      {adjustingItem && (
        <div className="fixed inset-0 z-60 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-lg overflow-hidden flex flex-col animate-in zoom-in-95">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-brand-100 text-brand-700 flex items-center justify-center">
                  <Sliders size={16} />
                </div>
                <div>
                  <h3 className="text-base font-bold text-slate-900">
                    Adjust Dish Price / Portion
                  </h3>
                  <p className="text-xs text-slate-500">
                    {adjustingItem.item_name} ({adjustingItem.variant_name})
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setAdjustingItem(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-700 cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Error Message */}
            {adjError && (
              <div className="px-6 py-2.5 bg-rose-50 border-b border-rose-200 text-xs font-semibold text-rose-700 flex items-center gap-2">
                <AlertCircle size={14} className="shrink-0" />
                <span>{adjError}</span>
              </div>
            )}

            {/* Modal Body */}
            <div className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
              {/* Adjustment Type Selector */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  Adjustment Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'CUSTOM_PORTION', label: 'Custom Portion', desc: 'e.g. Half Bowl @ ₹25' },
                    { id: 'EXTRA_PIECES', label: 'Extra Pieces', desc: 'e.g. +1 idli @ ₹20' },
                    { id: 'DISCOUNT_PERCENT', label: 'Discount %', desc: 'Item percentage off' },
                    { id: 'DISCOUNT_FIXED', label: 'Discount ₹', desc: 'Item flat rupee off' },
                    { id: 'SURCHARGE_FIXED', label: 'Surcharge ₹', desc: 'Special request fee' },
                    { id: 'CUSTOM_PRICE', label: 'Custom Price', desc: 'Direct price override' },
                  ].map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setAdjType(t.id)}
                      className={`p-2.5 rounded-xl border text-left transition cursor-pointer ${
                        adjType === t.id
                          ? 'bg-brand-50/70 border-brand-500 text-brand-900 ring-1 ring-brand-500'
                          : 'bg-white border-slate-200 text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <div className="text-xs font-bold">{t.label}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{t.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Dynamic Inputs Based on Type */}
              {adjType === 'CUSTOM_PORTION' && (
                <div className="p-4 bg-sky-50/60 border border-sky-200 rounded-2xl space-y-3">
                  <div>
                    <label className="block text-xs font-bold text-sky-950 mb-1">
                      Custom Portion Name
                    </label>
                    <input
                      type="text"
                      value={customPortionName}
                      onChange={(e) => setCustomPortionName(e.target.value)}
                      placeholder="e.g. Half Bowl, Kid Portion, Extra Large"
                      className="w-full px-3 py-2 rounded-xl border border-sky-300 bg-white text-sm text-slate-900 focus:outline-none focus:border-sky-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-sky-950 mb-1">
                      Portion Unit Price (₹)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={customPrice}
                      onChange={(e) => setCustomPrice(e.target.value)}
                      placeholder="25.00"
                      className="w-full px-3 py-2 rounded-xl border border-sky-300 bg-white font-mono font-bold text-sm text-slate-900 focus:outline-none focus:border-sky-500"
                    />
                  </div>
                </div>
              )}

              {adjType === 'EXTRA_PIECES' && (
                <div className="p-4 bg-amber-50/60 border border-amber-200 rounded-2xl space-y-3">
                  <div>
                    <label className="block text-xs font-bold text-amber-950 mb-1">
                      Number of Extra Pieces
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="50"
                      value={extraPieces}
                      onChange={(e) => setExtraPieces(parseInt(e.target.value) || 1)}
                      className="w-full px-3 py-2 rounded-xl border border-amber-300 bg-white font-mono font-bold text-sm text-slate-900 focus:outline-none focus:border-amber-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-amber-950 mb-1">
                      Price per Extra Piece (₹)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={extraPiecePrice}
                      onChange={(e) => setExtraPiecePrice(e.target.value)}
                      placeholder="20.00"
                      className="w-full px-3 py-2 rounded-xl border border-amber-300 bg-white font-mono font-bold text-sm text-slate-900 focus:outline-none focus:border-amber-500"
                    />
                  </div>
                </div>
              )}

              {adjType === 'DISCOUNT_PERCENT' && (
                <div className="p-4 bg-purple-50/60 border border-purple-200 rounded-2xl">
                  <label className="block text-xs font-bold text-purple-950 mb-1">
                    Discount Percentage (%)
                  </label>
                  <input
                    type="number"
                    step="0.5"
                    min="1"
                    max="100"
                    value={discountPercent}
                    onChange={(e) => setDiscountPercent(e.target.value)}
                    placeholder="10"
                    className="w-full px-3 py-2 rounded-xl border border-purple-300 bg-white font-mono font-bold text-sm text-slate-900 focus:outline-none focus:border-purple-500"
                  />
                </div>
              )}

              {adjType === 'DISCOUNT_FIXED' && (
                <div className="p-4 bg-purple-50/60 border border-purple-200 rounded-2xl">
                  <label className="block text-xs font-bold text-purple-950 mb-1">
                    Discount Amount per Unit (₹)
                  </label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    value={discountAmount}
                    onChange={(e) => setDiscountAmount(e.target.value)}
                    placeholder="15.00"
                    className="w-full px-3 py-2 rounded-xl border border-purple-300 bg-white font-mono font-bold text-sm text-slate-900 focus:outline-none focus:border-purple-500"
                  />
                </div>
              )}

              {adjType === 'SURCHARGE_FIXED' && (
                <div className="p-4 bg-emerald-50/60 border border-emerald-200 rounded-2xl">
                  <label className="block text-xs font-bold text-emerald-950 mb-1">
                    Surcharge per Unit (₹)
                  </label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    value={surchargeAmount}
                    onChange={(e) => setSurchargeAmount(e.target.value)}
                    placeholder="20.00"
                    className="w-full px-3 py-2 rounded-xl border border-emerald-300 bg-white font-mono font-bold text-sm text-slate-900 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              )}

              {adjType === 'CUSTOM_PRICE' && (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl">
                  <label className="block text-xs font-bold text-slate-900 mb-1">
                    New Effective Unit Price (₹)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={customPrice}
                    onChange={(e) => setCustomPrice(e.target.value)}
                    placeholder="45.00"
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 bg-white font-mono font-bold text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                  />
                </div>
              )}

              {/* Mandatory Reason */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  Reason for Adjustment <span className="text-rose-500">*</span>
                </label>
                <input
                  type="text"
                  value={adjReason}
                  onChange={(e) => setAdjReason(e.target.value)}
                  placeholder="e.g. Customer requested smaller half bowl, or Added 1 extra idli"
                  maxLength={255}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                />
              </div>

              {/* Live Preview Card */}
              {preview && (
                <div className="p-4 rounded-2xl bg-slate-900 text-white space-y-2">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                    Live Adjustment Preview
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-slate-400 block">Unit Price:</span>
                      <span className="font-mono text-sm">
                        {formatInr(preview.currentUnitPrice)} →{' '}
                        <strong className="text-emerald-400 font-bold">{formatInr(preview.newUnitPrice)}</strong>
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400 block">Line Total ({adjustingItem.active_quantity}x):</span>
                      <span className="font-mono text-sm">
                        {formatInr(preview.currentLineTotal)} →{' '}
                        <strong className="text-emerald-400 font-bold">{formatInr(preview.newLineTotal)}</strong>
                      </span>
                    </div>
                  </div>
                  <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-xs">
                    <span className="text-slate-300">New Order Subtotal:</span>
                    <span className="font-mono font-black text-sm text-amber-400">
                      {formatInr(preview.projectedOrderSubtotal)}
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Actions */}
            <div className="px-6 py-4 border-t border-slate-200 bg-slate-50 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setAdjustingItem(null)}
                disabled={isSubmittingAdj}
                className="px-4 py-2.5 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-200/60 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveAdjustment}
                disabled={isSubmittingAdj}
                className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-brand-600 hover:bg-brand-700 transition shadow-sm cursor-pointer disabled:opacity-50"
              >
                {isSubmittingAdj ? 'Applying...' : 'Apply Live Adjustment'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
