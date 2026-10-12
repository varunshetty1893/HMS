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

  // Policy switches
  const [allowMultiDevice, setAllowMultiDevice] = useState(true);
  const [allowCustomerCancel, setAllowCustomerCancel] = useState(false);
  const [allowKitchenToggle, setAllowKitchenToggle] = useState(true);
  const [limitIncludesTax, setLimitIncludesTax] = useState(false);
  const [limitAppliesToWaiter, setLimitAppliesToWaiter] = useState(false);

  const fetchSettings = async () => {
    setIsLoading(true);
    try {
      const data = await settingsAuditApi.getSettings();
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
      setAllowMultiDevice(data.allow_multi_device_per_table);
      setAllowCustomerCancel(data.allow_customer_cancel_placed);
      setAllowKitchenToggle(data.kitchen_can_toggle_availability);
      setLimitIncludesTax(data.limit_includes_estimated_tax);
      setLimitAppliesToWaiter(data.apply_outstanding_limit_to_waiter_orders);
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
      allow_multi_device_per_table: allowMultiDevice,
      allow_customer_cancel_placed: allowCustomerCancel,
      kitchen_can_toggle_availability: allowKitchenToggle,
      limit_includes_estimated_tax: limitIncludesTax,
      apply_outstanding_limit_to_waiter_orders: limitAppliesToWaiter,
    };

    try {
      const updated = await settingsAuditApi.updateSettings(payload);
      setSettings(updated);
      setSuccessMessage('Configuration updated successfully and logged in audit trail.');
    } catch (err: any) {
      setError(err?.message || 'Failed to update settings');
    } finally {
      setIsSaving(false);
    }
  };

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
                placeholder="29AAAAA0000A1Z5"
                className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none"
                style={{
                  backgroundColor: L ? '#faf7f2' : '#0f172a',
                  border: `1.5px solid ${border}`,
                  color: heading,
                }}
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase mb-1" style={{ color: sub }}>Phone Number</label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
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
                className="w-full px-3.5 py-2.5 rounded-xl text-sm font-mono focus:outline-none"
                style={{
                  backgroundColor: L ? '#faf7f2' : '#0f172a',
                  border: `1.5px solid ${border}`,
                  color: heading,
                }}
              />
              <span className="text-[11px] mt-0.5 block" style={{ color: muted }}>Default ₹5,000.00 cap per session</span>
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
            <label className="flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition hover:opacity-90" style={cardInner}>
              <div>
                <span className="text-sm font-semibold block" style={{ color: heading }}>Multi-Device Ordering (OD-01)</span>
                <span className="text-xs" style={{ color: sub }}>Allow multiple customer phones at the same table to order simultaneously.</span>
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
                <span className="text-xs" style={{ color: sub }}>Allow customer phone to cancel their order while still in PLACED status.</span>
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
                <span className="text-sm font-semibold block" style={{ color: heading }}>Kitchen 86 Stock Toggle (OD-05)</span>
                <span className="text-xs" style={{ color: sub }}>Allow Kitchen KDS display staff to mark dishes sold out directly.</span>
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
                <span className="text-sm font-semibold block" style={{ color: heading }}>Include Tax in ₹5,000 Cap (OD-06)</span>
                <span className="text-xs" style={{ color: sub }}>Calculates estimated GST before evaluating the session exposure limit.</span>
              </div>
              <input
                type="checkbox"
                checked={limitIncludesTax}
                onChange={(e) => setLimitIncludesTax(e.target.checked)}
                className="w-4 h-4 accent-brand-600 rounded cursor-pointer"
              />
            </label>

            <label className="flex items-center justify-between p-3.5 rounded-2xl cursor-pointer transition hover:opacity-90" style={cardInner}>
              <div>
                <span className="text-sm font-semibold block" style={{ color: heading }}>Apply Exposure Limit to Waiter Orders (OD-07)</span>
                <span className="text-xs" style={{ color: sub }}>Blocks waiter manual order entry if table session exceeds ₹5,000 cap.</span>
              </div>
              <input
                type="checkbox"
                checked={limitAppliesToWaiter}
                onChange={(e) => setLimitAppliesToWaiter(e.target.checked)}
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
