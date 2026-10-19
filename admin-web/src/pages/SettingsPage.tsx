import React, { useEffect, useState } from 'react';
import { settingsAuditApi } from '@/api/settingsAuditApi';
import { formatDateTimeIst } from '@/utils/dateIst';
import {
  Building2,
  CheckCircle2,
  Percent,
  Save,
  ShieldCheck,
} from 'lucide-react';
import { RestaurantSettings } from '@/types/api';
import { usePageTheme } from '@/hooks/usePageTheme';

export const SettingsPage: React.FC = () => {
  const { L, heading, sub, muted, border, card, cardInner } = usePageTheme();
  const [settings, setSettings] = useState<RestaurantSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form Fields
  const [restaurantName, setRestaurantName] = useState('');
  const [address, setAddress] = useState('');
  const [phone, setPhone] = useState('');
  const [gstin, setGstin] = useState('');
  const [cgstPercentage, setCgstPercentage] = useState('2.50');
  const [sgstPercentage, setSgstPercentage] = useState('2.50');
  const [serviceCharge, setServiceCharge] = useState('0.00');
  const [pricesIncludeTax, setPricesIncludeTax] = useState(false);
  const [outstandingLimit, setOutstandingLimit] = useState('5000.00');
  const [waiterPriceOverrideLimit, setWaiterPriceOverrideLimit] = useState('0.00');

  // Policy switches
  const [allowMultiDevice, setAllowMultiDevice] = useState(true);
  const [allowCustomerCancel, setAllowCustomerCancel] = useState(false);
  const [allowKitchenToggle, setAllowKitchenToggle] = useState(true);
  const [limitIncludesTax, setLimitIncludesTax] = useState(false);
  const [requireConfirmation, setRequireConfirmation] = useState(true);
  const [confirmTimeout, setConfirmTimeout] = useState('180');
  const [maxPendingConfirmations, setMaxPendingConfirmations] = useState('15');

  const applySettings = (data: RestaurantSettings) => {
      setSettings(data);
      setRestaurantName(data.restaurant_name);
      setAddress(data.address || '');
      setPhone(data.phone || '');
      setGstin(data.gstin || '');
      setCgstPercentage(data.cgst_percentage);
      setSgstPercentage(data.sgst_percentage);
      setServiceCharge(data.service_charge_percentage);
      setPricesIncludeTax(data.prices_include_tax);
      setOutstandingLimit(data.default_session_outstanding_limit);
      setWaiterPriceOverrideLimit(data.waiter_max_price_override_percentage);
      setAllowMultiDevice(data.allow_multi_device_per_table);
      setAllowCustomerCancel(data.allow_customer_cancel_placed);
      setAllowKitchenToggle(data.kitchen_can_toggle_availability);
      setLimitIncludesTax(data.limit_includes_estimated_tax);
      setRequireConfirmation(data.require_waiter_confirmation_for_first_qr_order ?? true);
      setConfirmTimeout(String(data.qr_confirmation_timeout_seconds ?? 180));
      setMaxPendingConfirmations(String(data.max_pending_qr_confirmations ?? 15));
  };

  const fetchSettings = async () => {
    setIsLoading(true);
    try {
      applySettings(await settingsAuditApi.getSettings());
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to load restaurant settings');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setSuccessMessage(null);
    setError(null);

    const payload = {
      restaurant_name: restaurantName.trim(),
      address: address.trim() || null,
      phone: phone.trim() || null,
      gstin: gstin.trim() || null,
      cgst_percentage: cgstPercentage,
      sgst_percentage: sgstPercentage,
      service_charge_percentage: serviceCharge,
      prices_include_tax: pricesIncludeTax,
      default_session_outstanding_limit: outstandingLimit,
      waiter_max_price_override_percentage: waiterPriceOverrideLimit,
      allow_multi_device_per_table: allowMultiDevice,
      allow_customer_cancel_placed: allowCustomerCancel,
      kitchen_can_toggle_availability: allowKitchenToggle,
      limit_includes_estimated_tax: limitIncludesTax,
      require_waiter_confirmation_for_first_qr_order: requireConfirmation,
      qr_confirmation_timeout_seconds: Number(confirmTimeout),
      max_pending_qr_confirmations: Number(maxPendingConfirmations),
    };

    try {
      const updated = await settingsAuditApi.updateSettings(payload);
      applySettings(updated); // re-sync so the form shows exactly what the server stored
      setSuccessMessage('Configuration updated successfully and logged in audit trail.');
    } catch (err: any) {
      setError(err?.message || 'Failed to update settings');
    } finally {
      setIsSaving(false);
    }
  };

  const limitLabel = `₹${Number(outstandingLimit || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
  const gstinLooksValid = !gstin || /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(gstin);

  if (isLoading) {
    return <div className="p-12 text-center text-slate-500">Loading settings...</div>;
  }

  return (
    <div className="p-8 max-w-4xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black tracking-tight" style={{ color: heading }}>Restaurant Configuration & Policies</h1>
        <p className="text-sm mt-1" style={{ color: sub }}>
          Profile, GST tax rates, session limit protection, and operational switches
          {settings?.updated_at && ` • Last updated ${formatDateTimeIst(settings.updated_at)}`}
        </p>
      </div>

      {successMessage && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-8">
        {/* Section 1: Business Profile */}
        <div className="p-6 rounded-3xl shadow-sm space-y-5" style={card}>
          <div className="flex items-center gap-2 pb-3 border-b" style={{ borderBottomColor: border }}>
            <Building2 className="w-5 h-5 text-brand-600" />
            <h2 className="text-base font-bold" style={{ color: heading }}>Restaurant Profile</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Restaurant Legal Name</label>
              <input
                type="text"
                value={restaurantName}
                onChange={(e) => setRestaurantName(e.target.value)}
                required
                maxLength={120}
                className="w-full px-3.5 py-2.5 rounded-xl text-sm focus:outline-none"
                style={{
                  backgroundColor: L ? '#faf7f2' : '#0f172a',
                  border: `1.5px solid ${border}`,
                  color: heading,
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>GSTIN Number</label>
              <input
                type="text"
                value={gstin}
                onChange={(e) => setGstin(e.target.value.toUpperCase())}
                maxLength={15}
                placeholder="29AAAAA0000A1Z5"
                className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none"
                style={{
                  backgroundColor: L ? '#faf7f2' : '#0f172a',
                  border: `1.5px solid ${gstinLooksValid ? border : '#e11d48'}`,
                  color: heading,
                }}
              />
              {!gstinLooksValid && (
                <span className="text-[11px] mt-0.5 block font-medium text-rose-700">
                  Doesn't look like a valid 15-character GSTIN — check before printing bills.
                </span>
              )}
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Phone Number</label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                maxLength={20}
                placeholder="+91 98765 43210"
                className="w-full px-3.5 py-2.5 rounded-xl text-sm focus:outline-none"
                style={{
                  backgroundColor: L ? '#faf7f2' : '#0f172a',
                  border: `1.5px solid ${border}`,
                  color: heading,
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Physical Address</label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                maxLength={255}
                placeholder="123 Food Street, Indiranagar, Bengaluru"
                className="w-full px-3.5 py-2.5 rounded-xl text-sm focus:outline-none"
                style={{
                  backgroundColor: L ? '#faf7f2' : '#0f172a',
                  border: `1.5px solid ${border}`,
                  color: heading,
                }}
              />
            </div>
          </div>
        </div>

        {/* Section 2: Taxes & Exposure Limits */}
        <div className="p-6 rounded-3xl shadow-sm space-y-5" style={card}>
          <div className="flex items-center gap-2 pb-3 border-b" style={{ borderBottomColor: border }}>
            <Percent className="w-5 h-5 text-emerald-600" />
            <h2 className="text-base font-bold" style={{ color: heading }}>GST Rates & Exposure Protection</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>CGST Rate (%)</label>
              <input
                type="number"
                step="0.01"
                value={cgstPercentage}
                onChange={(e) => setCgstPercentage(e.target.value)}
                required
                min={0}
                max={28}
                className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none"
                style={{
                  backgroundColor: L ? '#faf7f2' : '#0f172a',
                  border: `1.5px solid ${border}`,
                  color: heading,
                }}
              />
              <span className="text-[11px] mt-0.5 block" style={{ color: muted }}>Default 2.50%</span>
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>SGST Rate (%)</label>
              <input
                type="number"
                step="0.01"
                value={sgstPercentage}
                onChange={(e) => setSgstPercentage(e.target.value)}
                required
                min={0}
                max={28}
                className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none"
                style={{
                  backgroundColor: L ? '#faf7f2' : '#0f172a',
                  border: `1.5px solid ${border}`,
                  color: heading,
                }}
              />
              <span className="text-[11px] mt-0.5 block" style={{ color: muted }}>Default 2.50%</span>
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Default Table Limit (₹)</label>
              <input
                type="number"
                step="100.00"
                value={outstandingLimit}
                onChange={(e) => setOutstandingLimit(e.target.value)}
                required
                min={100}
                max={100000}
                className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none"
                style={{
                  backgroundColor: L ? '#faf7f2' : '#0f172a',
                  border: `1.5px solid ${border}`,
                  color: heading,
                }}
              />
              <span className="text-[11px] mt-0.5 block" style={{ color: muted }}>
                Unpaid-order cap per table for customer (QR) orders only; waiters have no limit. Applies to new table sessions; tables already occupied keep their current limit.
              </span>
            </div>
          </div>
        </div>

        {/* Section 3: Operational Policy Switches (OD-01..OD-08) */}
        <div className="p-6 rounded-3xl shadow-sm space-y-4" style={card}>
          <div className="flex items-center gap-2 pb-3 border-b" style={{ borderBottomColor: border }}>
            <ShieldCheck className="w-5 h-5 text-brand-600" />
            <h2 className="text-base font-bold" style={{ color: heading }}>Operational Policy Controls</h2>
          </div>

          <div className="space-y-3">
            <div className="p-3.5 rounded-2xl" style={cardInner}>
              <label className="block text-sm font-semibold mb-1" style={{ color: heading }}>Waiter bill-time price adjustment limit (%)</label>
              <input
                type="number"
                min={0}
                max={100}
                step="0.01"
                value={waiterPriceOverrideLimit}
                onChange={(e) => setWaiterPriceOverrideLimit(e.target.value)}
                className="w-40 px-3 py-2 rounded-xl text-sm font-mono focus:outline-none"
                style={{ backgroundColor: L ? '#faf7f2' : '#0f172a', border: `1.5px solid ${border}`, color: heading }}
              />
              <span className="text-xs ml-3" style={{ color: sub }}>Waiters may move each billed line up or down by this percentage; Admin has no cap. Every adjustment needs a reason.</span>
            </div>
            <label className="flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition hover:opacity-90" style={cardInner}>
              <div>
                <span className="text-sm font-semibold block" style={{ color: heading }}>Multi-Device Ordering (OD-01)</span>
                <span className="text-xs" style={{ color: sub }}>Allow multiple customer phones at the same table to order. When off, a second phone is blocked once another phone has ordered.</span>
              </div>
              <input
                type="checkbox"
                checked={allowMultiDevice}
                onChange={(e) => setAllowMultiDevice(e.target.checked)}
                className="w-4 h-4 accent-brand-600 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition hover:opacity-90" style={cardInner}>
              <div>
                <span className="text-sm font-semibold block" style={{ color: heading }}>Customer Self-Cancel (OD-02)</span>
                <span className="text-xs" style={{ color: sub }}>Allow customer phone to cancel their own order before cooking starts (PLACED / ACCEPTED). When off, only staff can cancel.</span>
              </div>
              <input
                type="checkbox"
                checked={allowCustomerCancel}
                onChange={(e) => setAllowCustomerCancel(e.target.checked)}
                className="w-4 h-4 accent-brand-600 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition hover:opacity-90" style={cardInner}>
              <div>
                <span className="text-sm font-semibold block" style={{ color: heading }}>Waiter Confirms First QR Order (T-01)</span>
                <span className="text-xs" style={{ color: sub }}>A QR order on an empty table waits until a waiter confirms guests are seated, so a photographed QR cannot send fake orders to the kitchen. Turn off only for a quiet venue.</span>
              </div>
              <input
                type="checkbox"
                checked={requireConfirmation}
                onChange={(e) => setRequireConfirmation(e.target.checked)}
                className="w-4 h-4 accent-brand-600 rounded cursor-pointer"
              />
            </label>

            {requireConfirmation && (
              <div className="p-3.5 rounded-2xl grid grid-cols-1 sm:grid-cols-2 gap-4" style={cardInner}>
                <div>
                  <span className="text-sm font-semibold block mb-1" style={{ color: heading }}>Auto-cancel after (seconds)</span>
                  <input
                    type="number"
                    min={30}
                    max={1800}
                    step={10}
                    value={confirmTimeout}
                    onChange={(e) => setConfirmTimeout(e.target.value)}
                    className="w-32 px-3 py-2 rounded-xl text-sm font-mono focus:outline-none"
                    style={{ backgroundColor: L ? '#faf7f2' : '#0f172a', border: `1.5px solid ${border}`, color: heading }}
                  />
                  <span className="text-xs block mt-1" style={{ color: sub }}>30 to 1800. Unanswered requests are cancelled and the guest is told to ask a waiter.</span>
                </div>
                <div>
                  <span className="text-sm font-semibold block mb-1" style={{ color: heading }}>Max waiting requests</span>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    value={maxPendingConfirmations}
                    onChange={(e) => setMaxPendingConfirmations(e.target.value)}
                    className="w-32 px-3 py-2 rounded-xl text-sm font-mono focus:outline-none"
                    style={{ backgroundColor: L ? '#faf7f2' : '#0f172a', border: `1.5px solid ${border}`, color: heading }}
                  />
                  <span className="text-xs block mt-1" style={{ color: sub }}>Across the whole restaurant. Beyond this, guests are asked to call a waiter.</span>
                </div>
              </div>
            )}

            <label className="flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition hover:opacity-90" style={cardInner}>
              <div>
                <span className="text-sm font-semibold block" style={{ color: heading }}>Kitchen 86 Stock Toggle (OD-05)</span>
                <span className="text-xs" style={{ color: sub }}>Allow Kitchen KDS staff to mark dishes sold out. When off, only Admin can change availability.</span>
              </div>
              <input
                type="checkbox"
                checked={allowKitchenToggle}
                onChange={(e) => setAllowKitchenToggle(e.target.checked)}
                className="w-4 h-4 accent-brand-600 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition hover:opacity-90" style={cardInner}>
              <div>
                <span className="text-sm font-semibold block" style={{ color: heading }}>Include Tax in {limitLabel} Cap (OD-06)</span>
                <span className="text-xs" style={{ color: sub }}>Adds estimated CGST + SGST to the table total before checking the cap (customer orders only; waiters are never capped).</span>
              </div>
              <input
                type="checkbox"
                checked={limitIncludesTax}
                onChange={(e) => setLimitIncludesTax(e.target.checked)}
                className="w-4 h-4 accent-brand-600 rounded cursor-pointer"
              />
            </label>

          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white shadow-lg shadow-brand-600/30 transition cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>{isSaving ? 'Saving Changes...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
