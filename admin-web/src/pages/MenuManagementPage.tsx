import React, { useEffect, useState } from 'react';
import { menuApi } from '@/api/menuApi';
import { formatInr } from '@/utils/currency';
import {
  Camera,
  FolderPlus,
  Plus,
  Search,
  ToggleLeft,
  ToggleRight,
  X,
} from 'lucide-react';
import { MenuCategory, MenuItem } from '@/types/api';
import { usePageTheme } from '@/hooks/usePageTheme';

export const MenuManagementPage: React.FC = () => {
  const { heading, sub } = usePageTheme();
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [categoryName, setCategoryName] = useState('');
  const [categoryDesc, setCategoryDesc] = useState('');

  const [isItemModalOpen, setIsItemModalOpen] = useState(false);
  const [newItemName, setNewItemName] = useState('');
  const [newItemCode, setNewItemCode] = useState('');
  const [newItemDesc, setNewItemDesc] = useState('');
  const [newItemCatId, setNewItemCatId] = useState('');
  const [newItemDiet, setNewItemDiet] = useState<'VEG' | 'NON_VEG' | 'EGG'>('VEG');
  const [newItemSpice, setNewItemSpice] = useState<'NONE' | 'MILD' | 'MEDIUM' | 'SPICY' | 'EXTRA_SPICY'>('NONE');
  const [variantName, setVariantName] = useState('Standard');
  const [variantCode, setVariantCode] = useState('');
  const [variantPrice, setVariantPrice] = useState('100.00');

  // Image Upload State
  const [uploadingItemId, setUploadingItemId] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [cats, dishList] = await Promise.all([
        menuApi.listCategories(false),
        menuApi.listItems(undefined, false),
      ]);
      setCategories(cats);
      setItems(dishList);
      if (cats.length > 0 && !newItemCatId) {
        setNewItemCatId(cats[0].id);
      }
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to load menu data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleToggleAvailability = async (item: MenuItem) => {
    try {
      const updated = await menuApi.setItemAvailability(
        item.id,
        !item.is_available,
        item.is_available ? '86d by Admin' : 'Back in stock'
      );
      setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, is_available: updated.is_available } : i)));
    } catch (err: any) {
      alert(err?.message || 'Failed to toggle availability');
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryName.trim()) return;
    try {
      await menuApi.createCategory({
        name: categoryName.trim(),
        description: categoryDesc.trim() || null,
        display_order: categories.length + 1,
        is_active: true,
      });
      setIsCategoryModalOpen(false);
      setCategoryName('');
      setCategoryDesc('');
      fetchData();
    } catch (err: any) {
      alert(err?.message || 'Failed to create category');
    }
  };

  const handleCreateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemName.trim() || !newItemCode.trim() || !newItemCatId) {
      alert('Please fill dish name, short code, and category');
      return;
    }
    try {
      await menuApi.createItem({
        category_id: newItemCatId,
        item_code: newItemCode.trim().toUpperCase(),
        name: newItemName.trim(),
        description: newItemDesc.trim() || null,
        dietary_type: newItemDiet,
        spice_level: newItemSpice,
        variants: [
          {
            variant_name: variantName.trim() || 'Standard',
            variant_code: variantCode.trim().toUpperCase() || `${newItemCode.trim().toUpperCase()}-STD`,
            price: parseFloat(variantPrice) || 100.0,
            is_active: true,
          },
        ],
      });
      setIsItemModalOpen(false);
      setNewItemName('');
      setNewItemCode('');
      setNewItemDesc('');
      setVariantCode('');
      setVariantPrice('100.00');
      fetchData();
    } catch (err: any) {
      alert(err?.message || 'Failed to create menu item');
    }
  };

  const handleImageFileChange = async (itemId: string, e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadingItemId(itemId);
    try {
      const updated = await menuApi.uploadImage(itemId, file);
      setItems((prev) => prev.map((i) => (i.id === itemId ? { ...i, image_url: updated.image_url } : i)));
    } catch (err: any) {
      alert(err?.message || 'Failed to upload photo');
    } finally {
      setUploadingItemId(null);
    }
  };

  const filteredItems = items.filter((item) => {
    const matchesCat = selectedCategory === 'ALL' || item.category_id === selectedCategory;
    const q = searchQuery.toLowerCase().trim();
    const matchesQuery =
      !q ||
      item.name.toLowerCase().includes(q) ||
      item.item_code.toLowerCase().includes(q) ||
      item.variants.some((v) => v.variant_code.toLowerCase().includes(q));
    return matchesCat && matchesQuery;
  });

  return (
    <div className="p-8 space-y-6">
      {/* Header & Primary Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight" style={{ color: heading }}>
            Menu & Catalog Manager
          </h1>
          <p className="text-sm mt-1" style={{ color: sub }}>
            Categories, dishes, price variants, short codes, and 86'd stock availability
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsCategoryModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-xs transition cursor-pointer"
          >
            <FolderPlus className="w-4 h-4 text-slate-500" />
            <span>New Category</span>
          </button>
          <button
            onClick={() => setIsItemModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-600/30 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add Dish</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-700">
          {error}
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Category Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 max-w-full">
          <button
            onClick={() => setSelectedCategory('ALL')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold shrink-0 transition cursor-pointer ${
              selectedCategory === 'ALL'
                ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
            }`}
          >
            All Items ({items.length})
          </button>
          {categories.map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedCategory(c.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold shrink-0 transition cursor-pointer ${
                selectedCategory === c.id
                  ? 'bg-brand-600 text-white shadow-md shadow-brand-600/30'
                  : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
              }`}
            >
              {c.name}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search dish or code (CB)..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-white border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-brand-500 shadow-xs"
          />
        </div>
      </div>

      {/* Dishes Grid */}
      {isLoading ? (
        <div className="p-12 text-center text-slate-400">Loading catalog...</div>
      ) : filteredItems.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-white border border-slate-200 text-slate-500 shadow-xs">
          No dishes match your filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredItems.map((item) => (
            <div
              key={item.id}
              className={`rounded-2xl border p-5 flex flex-col justify-between transition ${
                item.is_available
                  ? 'bg-white border-slate-200 shadow-xs hover:shadow-md'
                  : 'bg-slate-50/70 border-rose-200 opacity-80'
              }`}
            >
              {/* Top Details */}
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded font-mono font-bold text-xs bg-orange-50 text-orange-700 border border-orange-200">
                      {item.item_code}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-bold ${
                        item.dietary_type === 'VEG'
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                          : 'bg-rose-50 text-rose-700 border border-rose-200'
                      }`}
                    >
                      {item.dietary_type}
                    </span>
                  </div>

                  {/* 86'd Stock Toggle */}
                  <button
                    onClick={() => handleToggleAvailability(item)}
                    title={item.is_available ? 'Mark Sold Out (86)' : 'Mark In Stock'}
                    className="flex items-center gap-1.5 text-xs font-semibold cursor-pointer"
                  >
                    {item.is_available ? (
                      <span className="flex items-center gap-1 text-emerald-600 font-medium">
                        <ToggleRight className="w-5 h-5 text-emerald-500" />
                        <span>In Stock</span>
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-rose-600 font-medium">
                        <ToggleLeft className="w-5 h-5 text-rose-400" />
                        <span>Sold Out</span>
                      </span>
                    )}
                  </button>
                </div>

                <h3 className="text-base font-bold text-slate-900 mt-3">{item.name}</h3>
                {item.description && (
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">{item.description}</p>
                )}
              </div>

              {/* Price Variants */}
              <div className="mt-4 pt-3 border-t border-slate-100">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Portions & Prices
                </div>
                <div className="space-y-1.5">
                  {item.variants.map((v) => (
                    <div
                      key={v.id}
                      className="flex items-center justify-between text-xs px-2.5 py-1.5 rounded-xl bg-slate-50 border border-slate-200"
                    >
                      <div className="flex items-center gap-1.5">
                        <span className="font-mono text-slate-500 text-[10px]">{v.variant_code}</span>
                        <span className="font-medium text-slate-800">{v.variant_name}</span>
                      </div>
                      <span className="font-mono font-bold text-slate-900">{formatInr(v.price)}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Image & Action bar */}
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <label className="flex items-center gap-1.5 text-orange-600 hover:text-orange-700 cursor-pointer font-medium">
                  <Camera className="w-4 h-4" />
                  <span>{uploadingItemId === item.id ? 'Uploading...' : item.image_url ? 'Replace Photo' : 'Add Photo'}</span>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={(e) => handleImageFileChange(item.id, e)}
                    className="hidden"
                  />
                </label>
                {item.image_url && <span className="text-emerald-600 font-medium text-[11px]">✓ Photo attached</span>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New Category Modal */}
      {isCategoryModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-white border border-slate-200 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900">Create Menu Category</h3>
              <button onClick={() => setIsCategoryModalOpen(false)} className="text-slate-400 hover:text-slate-700 cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateCategory} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-600 mb-1">Category Name</label>
                <input
                  type="text"
                  value={categoryName}
                  onChange={(e) => setCategoryName(e.target.value)}
                  placeholder="Biriyani, Starters, Beverages..."
                  required
                  className="w-full px-4 py-2.5 rounded-xl bg-white border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase text-slate-600 mb-1">Description (Optional)</label>
                <input
                  type="text"
                  value={categoryDesc}
                  onChange={(e) => setCategoryDesc(e.target.value)}
                  placeholder="Traditional dum biriyanis cooked over coal..."
                  className="w-full px-4 py-2.5 rounded-xl bg-white border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                />
              </div>
              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsCategoryModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-xs cursor-pointer"
                >
                  Create Category
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* New Dish Modal */}
      {isItemModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl bg-white border border-slate-200 p-6 shadow-2xl my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900">Add New Dish</h3>
              <button onClick={() => setIsItemModalOpen(false)} className="text-slate-400 hover:text-slate-700 cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleCreateItem} className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase text-slate-600 mb-1">Dish Name</label>
                  <input
                    type="text"
                    value={newItemName}
                    onChange={(e) => setNewItemName(e.target.value)}
                    placeholder="Chicken Biryani"
                    required
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-slate-600 mb-1">
                    Short Code (1-16 chars)
                  </label>
                  <input
                    type="text"
                    value={newItemCode}
                    onChange={(e) => setNewItemCode(e.target.value.toUpperCase())}
                    placeholder="CB"
                    required
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-sm font-mono text-slate-900 focus:outline-none focus:border-brand-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-600 mb-1">Category</label>
                <select
                  value={newItemCatId}
                  onChange={(e) => setNewItemCatId(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                >
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase text-slate-600 mb-1">Dietary Tag</label>
                  <select
                    value={newItemDiet}
                    onChange={(e) => setNewItemDiet(e.target.value as any)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                  >
                    <option value="VEG">VEG</option>
                    <option value="NON_VEG">NON-VEG</option>
                    <option value="EGG">EGG</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase text-slate-600 mb-1">Spice Level</label>
                  <select
                    value={newItemSpice}
                    onChange={(e) => setNewItemSpice(e.target.value as any)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                  >
                    <option value="NONE">None</option>
                    <option value="MILD">Mild</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="SPICY">Spicy</option>
                    <option value="EXTRA_SPICY">Extra Spicy</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase text-slate-600 mb-1">Description</label>
                <textarea
                  value={newItemDesc}
                  onChange={(e) => setNewItemDesc(e.target.value)}
                  placeholder="Rich spices, long-grain basmati rice, tender chicken..."
                  rows={2}
                  className="w-full px-3.5 py-2 rounded-xl bg-white border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                />
              </div>

              {/* Initial Price Variant */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-orange-700">
                  Initial Portion & Price
                </span>
                <div className="grid grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] text-slate-500 mb-1">Portion Name</label>
                    <input
                      type="text"
                      value={variantName}
                      onChange={(e) => setVariantName(e.target.value)}
                      placeholder="Full / Half"
                      required
                      className="w-full px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs text-slate-900"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-500 mb-1">Variant Code</label>
                    <input
                      type="text"
                      value={variantCode}
                      onChange={(e) => setVariantCode(e.target.value.toUpperCase())}
                      placeholder="CB-F"
                      className="w-full px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-mono text-slate-900"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] text-slate-500 mb-1">Price (₹)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={variantPrice}
                      onChange={(e) => setVariantPrice(e.target.value)}
                      required
                      className="w-full px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs font-mono text-slate-900"
                    />
                  </div>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsItemModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-xs cursor-pointer"
                >
                  Save Dish
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
