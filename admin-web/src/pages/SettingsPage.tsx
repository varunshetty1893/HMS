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

export const SettingsPage: React.FC = () => {
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
        <h1 className="text-2xl font-black tracking-tight text-white">Restaurant Configuration & Policies</h1>
        <p className="text-sm text-slate-400 mt-1">
          Profile, GST tax rates, session limit protection, and operational switches
          {settings?.updated_at && ` • Last updated ${formatDateTimeIst(settings.updated_at)}`}
        </p>
      </div>

      {successMessage && (
        <div className="p-4 rounded-2xl bg-emerald-950/60 border border-emerald-800 text-xs font-semibold text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>{successMessage}</span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
          {error}
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-8">
        {/* Section 1: Business Profile */}
        <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-xl space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <Building2 className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Restaurant Profile</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Restaurant Legal Name</label>
              <input
                type="text"
                value={restaurantName}
                onChange={(e) => setRestaurantName(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-400 mb-1">GSTIN Number</label>
              <input
                type="text"
                value={gstin}
                onChange={(e) => setGstin(e.target.value.toUpperCase())}
                placeholder="29AAAAA0000A1Z5"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm font-mono text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Phone Number</label>
              <input
                type="text"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 98765 43210"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Physical Address</label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="123 Food Street, Indiranagar, Bengaluru"
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-white focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>
        </div>

        {/* Section 2: Taxes & Exposure Limits */}
        <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-xl space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <Percent className="w-5 h-5 text-emerald-400" />
            <h2 className="text-base font-bold text-white">GST Rates & Exposure Protection</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-bold uppercase text-slate-400 mb-1">CGST Rate (%)</label>
              <input
                type="number"
                step="0.01"
                value={cgstPercentage}
                onChange={(e) => setCgstPercentage(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm font-mono text-white"
              />
              <span className="text-[11px] text-slate-500 mt-0.5 block">Default 2.50%</span>
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-400 mb-1">SGST Rate (%)</label>
              <input
                type="number"
                step="0.01"
                value={sgstPercentage}
                onChange={(e) => setSgstPercentage(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm font-mono text-white"
              />
              <span className="text-[11px] text-slate-500 mt-0.5 block">Default 2.50%</span>
            </div>
            <div>
              <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Default Table Limit (₹)</label>
              <input
                type="number"
                step="100.00"
                value={outstandingLimit}
                onChange={(e) => setOutstandingLimit(e.target.value)}
                required
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm font-mono text-white"
              />
              <span className="text-[11px] text-slate-500 mt-0.5 block">Default ₹5,000.00 cap per session</span>
            </div>
          </div>
        </div>

        {/* Section 3: Operational Policy Switches (OD-01..OD-08) */}
        <div className="p-6 rounded-3xl bg-slate-900 border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Operational Policy Controls</h2>
          </div>

          <div className="space-y-3">
            <label className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-950/70 border border-slate-800 cursor-pointer">
              <div>
                <span className="text-sm font-semibold text-white block">Multi-Device Ordering (OD-01)</span>
                <span className="text-xs text-slate-400">Allow multiple customer phones at the same table to order simultaneously.</span>
              </div>
              <input
                type="checkbox"
                checked={allowMultiDevice}
                onChange={(e) => setAllowMultiDevice(e.target.checked)}
                className="w-4 h-4 accent-indigo-600 rounded"
              />
            </label>

            <label className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-950/70 border border-slate-800 cursor-pointer">
              <div>
                <span className="text-sm font-semibold text-white block">Customer Self-Cancel (OD-02)</span>
                <span className="text-xs text-slate-400">Allow customer phone to cancel their order while still in PLACED status.</span>
              </div>
              <input
                type="checkbox"
                checked={allowCustomerCancel}
                onChange={(e) => setAllowCustomerCancel(e.target.checked)}
                className="w-4 h-4 accent-indigo-600 rounded"
              />
            </label>

            <label className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-950/70 border border-slate-800 cursor-pointer">
              <div>
                <span className="text-sm font-semibold text-white block">Kitchen 86 Stock Toggle (OD-05)</span>
                <span className="text-xs text-slate-400">Allow Kitchen KDS display staff to mark dishes sold out directly.</span>
              </div>
              <input
                type="checkbox"
                checked={allowKitchenToggle}
                onChange={(e) => setAllowKitchenToggle(e.target.checked)}
                className="w-4 h-4 accent-indigo-600 rounded"
              />
            </label>

            <label className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-950/70 border border-slate-800 cursor-pointer">
              <div>
                <span className="text-sm font-semibold text-white block">Include Tax in ₹5,000 Cap (OD-06)</span>
                <span className="text-xs text-slate-400">Calculates estimated GST before evaluating the session exposure limit.</span>
              </div>
              <input
                type="checkbox"
                checked={limitIncludesTax}
                onChange={(e) => setLimitIncludesTax(e.target.checked)}
                className="w-4 h-4 accent-indigo-600 rounded"
              />
            </label>

            <label className="flex items-center justify-between p-3.5 rounded-2xl bg-slate-950/70 border border-slate-800 cursor-pointer">
              <div>
                <span className="text-sm font-semibold text-white block">Apply Exposure Limit to Waiter Orders (OD-07)</span>
                <span className="text-xs text-slate-400">Blocks waiter manual order entry if table session exceeds ₹5,000 cap.</span>
              </div>
              <input
                type="checkbox"
                checked={limitAppliesToWaiter}
                onChange={(e) => setLimitAppliesToWaiter(e.target.checked)}
                className="w-4 h-4 accent-indigo-600 rounded"
              />
            </label>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            type="submit"
            disabled={isSaving}
            className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white shadow-lg shadow-indigo-600/30 transition cursor-pointer"
          >
            <Save className="w-4 h-4" />
            <span>{isSaving ? 'Saving Changes...' : 'Save Configuration'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
