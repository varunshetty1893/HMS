import React, { useEffect, useMemo, useState } from 'react';
import { menuApi } from '@/api/menuApi';
import { formatInr } from '@/utils/currency';
import {
  Camera,
  FolderPlus,
  Pencil,
  Plus,
  Search,
  ToggleLeft,
  ToggleRight,
  Trash2,
  X,
} from 'lucide-react';
import { DietaryType, MenuCategory, MenuItem, MenuPriceVariant, PriceUnit, SpiceLevel } from '@/types/api';
import { usePageTheme } from '@/hooks/usePageTheme';

// ---------------------------------------------------------------------------
// Portion helpers (Half/Full, 6 pcs/12 pcs, 250 ml/500 ml ...)
// ---------------------------------------------------------------------------

interface PortionRow {
  key: string;
  name: string;
  quantity: string;
  unit: PriceUnit;
  price: string;
  code: string; // empty = auto-generate
}

const UNIT_OPTIONS: { value: PriceUnit; label: string }[] = [
  { value: 'PORTION', label: 'portion' },
  { value: 'PLATE', label: 'plate' },
  { value: 'BOWL', label: 'bowl' },
  { value: 'PIECE', label: 'pieces' },
  { value: 'ML', label: 'ml' },
  { value: 'L', label: 'litre' },
  { value: 'GRAM', label: 'grams' },
  { value: 'KG', label: 'kg' },
];

const UNIT_SHORT: Record<string, string> = {
  PORTION: '',
  PLATE: '',
  BOWL: '',
  PIECE: 'pcs',
  ML: 'ml',
  L: 'L',
  GRAM: 'g',
  KG: 'kg',
};

const SPICE_OPTIONS: { value: SpiceLevel | ''; label: string }[] = [
  { value: '', label: 'Not applicable' },
  { value: 'MILD', label: 'Mild' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'HOT', label: 'Hot' },
];

const DIET_OPTIONS: { value: DietaryType; label: string; cls: string }[] = [
  { value: 'VEG', label: 'Veg', cls: 'bg-emerald-600 text-white border-emerald-600' },
  { value: 'NON_VEG', label: 'Non-Veg', cls: 'bg-rose-600 text-white border-rose-600' },
  { value: 'EGG', label: 'Egg', cls: 'bg-amber-500 text-white border-amber-500' },
];

let rowCounter = 0;
const newRow = (p: Partial<PortionRow> = {}): PortionRow => ({
  key: `row-${++rowCounter}`,
  name: '',
  quantity: '1',
  unit: 'PORTION',
  price: '',
  code: '',
  ...p,
});

interface Preset {
  id: string;
  label: string;
  hint: string;
  rows: () => PortionRow[];
}

const PRESETS: Preset[] = [
  {
    id: 'single',
    label: 'One price',
    hint: 'Juice, naan, rice, dessert',
    rows: () => [newRow({ name: 'Regular' })],
  },
  {
    id: 'half-full',
    label: 'Half / Full',
    hint: 'Biryani, curry, fried rice',
    rows: () => [
      newRow({ name: 'Half', quantity: '0.5' }),
      newRow({ name: 'Full', quantity: '1' }),
    ],
  },
  {
    id: 'plate-pieces',
    label: 'Plate by pieces',
    hint: 'Kebab: half = 6 pcs, full = 12 pcs',
    rows: () => [
      newRow({ name: 'Half Plate (6 pcs)', quantity: '6', unit: 'PIECE' }),
      newRow({ name: 'Full Plate (12 pcs)', quantity: '12', unit: 'PIECE' }),
    ],
  },
  {
    id: 'sml',
    label: 'Small / Medium / Large',
    hint: 'Shakes, pizza, lassi',
    rows: () => [
      newRow({ name: 'Small' }),
      newRow({ name: 'Medium' }),
      newRow({ name: 'Large' }),
    ],
  },
  {
    id: 'ml',
    label: 'By volume (ml)',
    hint: 'Juices, soft drinks',
    rows: () => [
      newRow({ name: '250 ml', quantity: '250', unit: 'ML' }),
      newRow({ name: '500 ml', quantity: '500', unit: 'ML' }),
    ],
  },
  {
    id: 'custom',
    label: 'Custom',
    hint: 'Add your own portions',
    rows: () => [newRow(), newRow()],
  },
];

const suggestItemCode = (name: string): string => {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return '';
  const code =
    words.length === 1
      ? words[0].slice(0, 3)
      : words
          .map((w) => w[0])
          .join('')
          .slice(0, 4);
  return code.toUpperCase().replace(/[^A-Z0-9]/g, '');
};

const suffixFromName = (name: string, idx: number): string => {
  const digits = name.match(/\d+/);
  const words = name.replace(/\(.*?\)/g, '').trim().split(/\s+/).filter(Boolean);
  const first = words[0] || '';
  if (/^(half|full|small|medium|large|regular|single|mini|jumbo)$/i.test(first)) {
    return first[0].toUpperCase();
  }
  if (digits) return digits[0];
  return first ? first.slice(0, 2).toUpperCase() : `P${idx + 1}`;
};

const portionLabel = (v: MenuPriceVariant): string => {
  const unit = UNIT_SHORT[v.unit] ?? '';
  const qty = parseFloat(v.quantity_value);
  if (!unit || isNaN(qty)) return '';
  return `${qty} ${unit}`;
};

const fieldCls =
  'w-full px-3.5 py-2.5 rounded-xl bg-white border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500';
const smallFieldCls =
  'w-full px-3 py-2 rounded-lg bg-white border border-slate-200 text-xs text-slate-900 focus:outline-none focus:border-brand-500';
const labelCls = 'block text-xs font-bold uppercase text-slate-600 mb-1';

export const MenuManagementPage: React.FC = () => {
  const { heading, sub } = usePageTheme();
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Category modal
  const [isCategoryModalOpen, setIsCategoryModalOpen] = useState(false);
  const [categoryName, setCategoryName] = useState('');
  const [categoryDesc, setCategoryDesc] = useState('');
  const [categoryError, setCategoryError] = useState<string | null>(null);

  // Dish modal
  const [isItemModalOpen, setIsItemModalOpen] = useState(false);
  const [newItemName, setNewItemName] = useState('');
  const [newItemCode, setNewItemCode] = useState('');
  const [codeTouched, setCodeTouched] = useState(false);
  const [newItemDesc, setNewItemDesc] = useState('');
  const [newItemCatId, setNewItemCatId] = useState('');
  const [newItemDiet, setNewItemDiet] = useState<DietaryType>('VEG');
  const [newItemSpice, setNewItemSpice] = useState<SpiceLevel | ''>('');
  const [presetId, setPresetId] = useState<string>('half-full');
  const [rows, setRows] = useState<PortionRow[]>(() => PRESETS[1].rows());
  const [itemError, setItemError] = useState<string | null>(null);
  const [isSavingItem, setIsSavingItem] = useState(false);

  // Add / edit single portion on an existing dish
  const [portionItem, setPortionItem] = useState<MenuItem | null>(null);
  const [editingVariant, setEditingVariant] = useState<MenuPriceVariant | null>(null);
  const [pRow, setPRow] = useState<PortionRow>(() => newRow());
  const [portionError, setPortionError] = useState<string | null>(null);
  const [isSavingPortion, setIsSavingPortion] = useState(false);

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
      if (cats.length > 0 && !newItemCatId) setNewItemCatId(cats[0].id);
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to load menu data');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ----- dish form helpers -----
  const resetItemForm = () => {
    setNewItemName('');
    setNewItemCode('');
    setCodeTouched(false);
    setNewItemDesc('');
    setNewItemDiet('VEG');
    setNewItemSpice('');
    setPresetId('half-full');
    setRows(PRESETS[1].rows());
    setItemError(null);
  };

  const openItemModal = () => {
    resetItemForm();
    if (categories.length > 0 && !newItemCatId) setNewItemCatId(categories[0].id);
    setIsItemModalOpen(true);
  };

  const onNameChange = (v: string) => {
    setNewItemName(v);
    if (!codeTouched) setNewItemCode(suggestItemCode(v));
  };

  const applyPreset = (p: Preset) => {
    setPresetId(p.id);
    // keep any prices already typed when switching to a preset with the same row count
    setRows((prev) => {
      const fresh = p.rows();
      return fresh.map((r, i) => ({ ...r, price: prev[i]?.price ?? '' }));
    });
  };

  const updateRow = (key: string, patch: Partial<PortionRow>) =>
    setRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  const removeRow = (key: string) => setRows((prev) => (prev.length > 1 ? prev.filter((r) => r.key !== key) : prev));

  const addRow = () => {
    setPresetId('custom');
    setRows((prev) => [...prev, newRow()]);
  };

  const autoCodes = useMemo(() => {
    const base = newItemCode.trim().toUpperCase();
    const used = new Set<string>();
    return rows.map((r, i) => {
      if (r.code.trim()) {
        used.add(r.code.trim().toUpperCase());
        return r.code.trim().toUpperCase();
      }
      if (!base) return '';
      let c = `${base}-${suffixFromName(r.name, i)}`.slice(0, 24);
      let n = 2;
      while (used.has(c)) c = `${base}-${suffixFromName(r.name, i)}${n++}`.slice(0, 24);
      used.add(c);
      return c;
    });
  }, [rows, newItemCode]);

  const validateRows = (list: PortionRow[]): string | null => {
    const seen = new Set<string>();
    for (let i = 0; i < list.length; i++) {
      const r = list[i];
      const label = `Portion ${i + 1}`;
      if (!r.name.trim()) return `${label}: give it a name (e.g. Half, Full, 6 pcs).`;
      const key = r.name.trim().toLowerCase();
      if (seen.has(key)) return `Two portions are named "${r.name.trim()}". Use different names.`;
      seen.add(key);
      const q = parseFloat(r.quantity);
      if (isNaN(q) || q <= 0) return `${label}: quantity must be more than 0.`;
      const p = parseFloat(r.price);
      if (r.price.trim() === '' || isNaN(p) || p < 0) return `${label} (${r.name.trim()}): enter a price.`;
    }
    return null;
  };

  const handleCreateItem = async (e: React.FormEvent) => {
    e.preventDefault();
    setItemError(null);
    if (!newItemName.trim()) return setItemError('Enter the dish name.');
    if (!newItemCode.trim()) return setItemError('Enter a short code (e.g. CB). Waiters type this to find the dish.');
    if (!newItemCatId) return setItemError('Pick a category. Create one first if the list is empty.');
    const rowsError = validateRows(rows);
    if (rowsError) return setItemError(rowsError);

    setIsSavingItem(true);
    try {
      const payload: Record<string, unknown> = {
        category_id: newItemCatId,
        item_code: newItemCode.trim().toUpperCase(),
        name: newItemName.trim(),
        description: newItemDesc.trim() || null,
        dietary_type: newItemDiet,
        variants: rows.map((r, i) => ({
          variant_name: r.name.trim(),
          variant_code: autoCodes[i] || null,
          quantity_value: String(parseFloat(r.quantity)),
          unit: r.unit,
          price: parseFloat(r.price).toFixed(2),
          is_default: i === 0,
          display_order: i,
        })),
      };
      if (newItemSpice) payload.spice_level = newItemSpice; // optional: leave out when not applicable
      await menuApi.createItem(payload);
      setIsItemModalOpen(false);
      setNotice(`"${newItemName.trim()}" added with ${rows.length} portion${rows.length > 1 ? 's' : ''}.`);
      fetchData();
    } catch (err: any) {
      setItemError(friendlyMenuError(err));
    } finally {
      setIsSavingItem(false);
    }
  };

  // ----- single portion (add / edit) -----
  const openAddPortion = (item: MenuItem) => {
    setPortionItem(item);
    setEditingVariant(null);
    setPRow(newRow());
    setPortionError(null);
  };

  const openEditPortion = (item: MenuItem, v: MenuPriceVariant) => {
    setPortionItem(item);
    setEditingVariant(v);
    setPRow(
      newRow({
        name: v.variant_name,
        quantity: String(parseFloat(v.quantity_value)),
        unit: v.unit,
        price: String(parseFloat(v.price)),
        code: v.variant_code || '',
      })
    );
    setPortionError(null);
  };

  const handleSavePortion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!portionItem) return;
    const msg = validateRows([pRow]);
    if (msg) return setPortionError(msg.replace(/^Portion 1( \(.*?\))?: /, ''));
    setIsSavingPortion(true);
    setPortionError(null);
    try {
      const body: Record<string, unknown> = {
        variant_name: pRow.name.trim(),
        quantity_value: String(parseFloat(pRow.quantity)),
        unit: pRow.unit,
        price: parseFloat(pRow.price).toFixed(2),
      };
      if (pRow.code.trim()) body.variant_code = pRow.code.trim().toUpperCase();
      if (editingVariant) {
        await menuApi.updateVariant(editingVariant.id, body);
      } else {
        if (!pRow.code.trim()) {
          body.variant_code = `${portionItem.item_code}-${suffixFromName(pRow.name, portionItem.variants.length)}`.slice(0, 24);
        }
        body.display_order = portionItem.variants.length;
        await menuApi.createVariant(portionItem.id, body);
      }
      setPortionItem(null);
      setEditingVariant(null);
      fetchData();
    } catch (err: any) {
      setPortionError(friendlyMenuError(err));
    } finally {
      setIsSavingPortion(false);
    }
  };

  const handleHidePortion = async (v: MenuPriceVariant) => {
    try {
      await menuApi.updateVariant(v.id, { is_active: false });
      fetchData();
    } catch (err: any) {
      setNotice(null);
      setError(friendlyMenuError(err));
    }
  };

  // ----- other actions -----
  const handleToggleAvailability = async (item: MenuItem) => {
    try {
      const updated = await menuApi.setItemAvailability(
        item.id,
        !item.is_available,
        item.is_available ? '86d by Admin' : 'Back in stock'
      );
      setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, is_available: updated.is_available } : i)));
    } catch (err: any) {
      setError(friendlyMenuError(err));
    }
  };

  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!categoryName.trim()) return;
    setCategoryError(null);
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
      setCategoryError(friendlyMenuError(err));
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
      setError(friendlyMenuError(err));
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
      item.variants.some((v) => (v.variant_code || '').toLowerCase().includes(q));
    return matchesCat && matchesQuery;
  });

  const dietBadge = (d: DietaryType | null) =>
    d === 'VEG'
      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
      : d === 'EGG'
        ? 'bg-amber-50 text-amber-700 border border-amber-200'
        : 'bg-rose-50 text-rose-700 border border-rose-200';

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black tracking-tight" style={{ color: heading }}>
            Menu & Catalog Manager
          </h1>
          <p className="text-sm mt-1" style={{ color: sub }}>
            Categories, dishes, portions (half / full / pieces / ml), prices and sold-out status
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
            onClick={openItemModal}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-600/30 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" />
            <span>Add Dish</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-xs text-rose-700 flex items-start justify-between gap-3 whitespace-pre-line">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="cursor-pointer shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      {notice && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-700 flex items-start justify-between gap-3">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} className="cursor-pointer shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
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
          {filteredItems.map((item) => {
            const activeVariants = item.variants.filter((v) => v.is_active);
            return (
              <div
                key={item.id}
                className={`rounded-2xl border p-5 flex flex-col justify-between transition ${
                  item.is_available
                    ? 'bg-white border-slate-200 shadow-xs hover:shadow-md'
                    : 'bg-slate-50/70 border-rose-200 opacity-80'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded font-mono font-bold text-xs bg-orange-50 text-orange-700 border border-orange-200">
                        {item.item_code}
                      </span>
                      {item.dietary_type && (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${dietBadge(item.dietary_type)}`}>
                          {item.dietary_type.replace('_', '-')}
                        </span>
                      )}
                      {item.spice_level && (
                        <span className="text-xs px-2 py-0.5 rounded-full font-semibold bg-orange-50 text-orange-700 border border-orange-200">
                          {item.spice_level === 'HOT' ? 'Hot' : item.spice_level === 'MEDIUM' ? 'Medium' : 'Mild'}
                        </span>
                      )}
                    </div>

                    <button
                      onClick={() => handleToggleAvailability(item)}
                      title={item.is_available ? 'Mark Sold Out (86)' : 'Mark In Stock'}
                      className="flex items-center gap-1.5 text-xs font-semibold cursor-pointer shrink-0"
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
                  {item.description && <p className="text-xs text-slate-500 mt-1 line-clamp-2">{item.description}</p>}
                </div>

                {/* Portions */}
                <div className="mt-4 pt-3 border-t border-slate-100">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400">
                      Portions & Prices
                    </div>
                    <button
                      onClick={() => openAddPortion(item)}
                      className="flex items-center gap-1 text-[11px] font-semibold text-orange-600 hover:text-orange-700 cursor-pointer"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Add portion</span>
                    </button>
                  </div>
                  <div className="space-y-1.5">
                    {activeVariants.map((v) => (
                      <div
                        key={v.id}
                        className="group flex items-center justify-between text-xs px-2.5 py-1.5 rounded-xl bg-slate-50 border border-slate-200"
                      >
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className="font-mono text-slate-500 text-[10px] shrink-0">{v.variant_code}</span>
                          <span className="font-medium text-slate-800 truncate">{v.variant_name}</span>
                          {portionLabel(v) && !v.variant_name.toLowerCase().includes(portionLabel(v).split(' ')[0]) && (
                            <span className="text-[10px] text-slate-400 shrink-0">· {portionLabel(v)}</span>
                          )}
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className="font-mono font-bold text-slate-900">{formatInr(v.price)}</span>
                          <button
                            onClick={() => openEditPortion(item, v)}
                            title="Edit portion / price"
                            className="text-slate-400 hover:text-orange-600 cursor-pointer"
                          >
                            <Pencil className="w-3.5 h-3.5" />
                          </button>
                          {activeVariants.length > 1 && (
                            <button
                              onClick={() => handleHidePortion(v)}
                              title="Remove this portion from the menu"
                              className="text-slate-400 hover:text-rose-600 cursor-pointer"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

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
            );
          })}
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
                <label className={labelCls}>Category Name</label>
                <input
                  type="text"
                  value={categoryName}
                  onChange={(e) => setCategoryName(e.target.value)}
                  placeholder="Biriyani, Starters, Beverages..."
                  required
                  className={fieldCls}
                />
              </div>
              <div>
                <label className={labelCls}>Description (Optional)</label>
                <input
                  type="text"
                  value={categoryDesc}
                  onChange={(e) => setCategoryDesc(e.target.value)}
                  placeholder="Traditional dum biriyanis cooked over coal..."
                  className={fieldCls}
                />
              </div>
              {categoryError && <p className="text-xs text-rose-600 whitespace-pre-line">{categoryError}</p>}
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
        <div className="fixed inset-0 z-50 flex items-start justify-center p-4 bg-slate-900/40 backdrop-blur-xs overflow-y-auto">
          <div className="w-full max-w-2xl rounded-2xl bg-white border border-slate-200 p-6 shadow-2xl my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900">Add New Dish</h3>
              <button onClick={() => setIsItemModalOpen(false)} className="text-slate-400 hover:text-slate-700 cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateItem} className="mt-4 space-y-5">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="sm:col-span-2">
                  <label className={labelCls}>Dish Name</label>
                  <input
                    type="text"
                    value={newItemName}
                    onChange={(e) => onNameChange(e.target.value)}
                    placeholder="Chicken Biryani"
                    className={fieldCls}
                  />
                </div>
                <div>
                  <label className={labelCls}>Short Code</label>
                  <input
                    type="text"
                    maxLength={16}
                    value={newItemCode}
                    onChange={(e) => {
                      setCodeTouched(true);
                      setNewItemCode(e.target.value.toUpperCase());
                    }}
                    placeholder="CB"
                    className={`${fieldCls} font-mono`}
                  />
                </div>
              </div>
              <p className="-mt-3 text-[11px] text-slate-400">
                Short code = quick search for waiters (type "CB" to find Chicken Biryani). Filled automatically, you can change it.
              </p>

              <div>
                <label className={labelCls}>Category</label>
                {categories.length === 0 ? (
                  <p className="text-xs text-rose-600">No categories yet. Close this and click "New Category" first.</p>
                ) : (
                  <select value={newItemCatId} onChange={(e) => setNewItemCatId(e.target.value)} className={fieldCls}>
                    {categories.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Veg / Non-Veg</label>
                  <div className="flex gap-2">
                    {DIET_OPTIONS.map((d) => (
                      <button
                        key={d.value}
                        type="button"
                        onClick={() => setNewItemDiet(d.value)}
                        className={`flex-1 px-3 py-2 rounded-xl text-xs font-bold border transition cursor-pointer ${
                          newItemDiet === d.value ? d.cls : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300'
                        }`}
                      >
                        {d.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className={labelCls}>
                    Spice Level <span className="normal-case font-normal text-slate-400">(optional)</span>
                  </label>
                  <select
                    value={newItemSpice}
                    onChange={(e) => setNewItemSpice(e.target.value as SpiceLevel | '')}
                    className={fieldCls}
                  >
                    {SPICE_OPTIONS.map((s) => (
                      <option key={s.value} value={s.value}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className={labelCls}>
                  Description <span className="normal-case font-normal text-slate-400">(optional)</span>
                </label>
                <textarea
                  value={newItemDesc}
                  onChange={(e) => setNewItemDesc(e.target.value)}
                  placeholder="Rich spices, long-grain basmati rice, tender chicken..."
                  rows={2}
                  className={fieldCls}
                />
              </div>

              {/* Portions builder */}
              <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-4">
                <div>
                  <span className="text-xs font-bold uppercase tracking-wider text-orange-700">
                    How is this dish sold?
                  </span>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    Pick a style, then set the price for each portion. You can rename or add more.
                  </p>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {PRESETS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => applyPreset(p)}
                      className={`text-left px-3 py-2 rounded-xl border transition cursor-pointer ${
                        presetId === p.id
                          ? 'border-brand-500 bg-orange-50 ring-1 ring-brand-500'
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      }`}
                    >
                      <div className="text-xs font-bold text-slate-800">{p.label}</div>
                      <div className="text-[10px] text-slate-500 leading-snug">{p.hint}</div>
                    </button>
                  ))}
                </div>

                <div className="space-y-2.5">
                  <div className="hidden sm:grid grid-cols-[1.6fr_0.7fr_0.9fr_0.9fr_auto] gap-2 text-[10px] font-bold uppercase text-slate-400 px-1">
                    <span>Portion name</span>
                    <span>Qty</span>
                    <span>Unit</span>
                    <span>Price (₹)</span>
                    <span className="w-6" />
                  </div>
                  {rows.map((r, i) => (
                    <div key={r.key} className="space-y-1">
                      <div className="grid grid-cols-2 sm:grid-cols-[1.6fr_0.7fr_0.9fr_0.9fr_auto] gap-2 items-center">
                        <input
                          type="text"
                          value={r.name}
                          onChange={(e) => updateRow(r.key, { name: e.target.value })}
                          placeholder="Half / Full / 6 pcs"
                          className={`${smallFieldCls} col-span-2 sm:col-span-1`}
                        />
                        <input
                          type="number"
                          step="any"
                          min="0"
                          value={r.quantity}
                          onChange={(e) => updateRow(r.key, { quantity: e.target.value })}
                          className={`${smallFieldCls} font-mono`}
                        />
                        <select
                          value={r.unit}
                          onChange={(e) => updateRow(r.key, { unit: e.target.value as PriceUnit })}
                          className={smallFieldCls}
                        >
                          {UNIT_OPTIONS.map((u) => (
                            <option key={u.value} value={u.value}>
                              {u.label}
                            </option>
                          ))}
                        </select>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          value={r.price}
                          onChange={(e) => updateRow(r.key, { price: e.target.value })}
                          placeholder="0.00"
                          className={`${smallFieldCls} font-mono`}
                        />
                        <button
                          type="button"
                          onClick={() => removeRow(r.key)}
                          disabled={rows.length <= 1}
                          title="Remove portion"
                          className="w-6 text-slate-400 hover:text-rose-600 disabled:opacity-30 cursor-pointer"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="flex items-center gap-2 pl-1">
                        <span className="text-[10px] text-slate-400">Waiter code:</span>
                        <input
                          type="text"
                          maxLength={24}
                          value={r.code}
                          onChange={(e) => updateRow(r.key, { code: e.target.value.toUpperCase() })}
                          placeholder={autoCodes[i] || 'auto'}
                          className="w-28 px-2 py-0.5 rounded-md bg-white border border-slate-200 text-[11px] font-mono text-slate-700 focus:outline-none focus:border-brand-500"
                        />
                        {i === 0 && <span className="text-[10px] text-emerald-600 font-semibold">default portion</span>}
                      </div>
                    </div>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={addRow}
                  className="flex items-center gap-1.5 text-xs font-semibold text-orange-600 hover:text-orange-700 cursor-pointer"
                >
                  <Plus className="w-4 h-4" />
                  <span>Add another portion</span>
                </button>
              </div>

              {itemError && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 whitespace-pre-line">
                  {itemError}
                </div>
              )}

              <div className="pt-1 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsItemModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingItem}
                  className="px-4 py-2 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-xs cursor-pointer disabled:opacity-60"
                >
                  {isSavingItem ? 'Saving...' : 'Save Dish'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add / Edit one portion modal */}
      {portionItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-white border border-slate-200 p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900">
                {editingVariant ? 'Edit portion' : 'Add portion'} · {portionItem.name}
              </h3>
              <button onClick={() => setPortionItem(null)} className="text-slate-400 hover:text-slate-700 cursor-pointer">
                <X className="w-5 h-5" />
              </button>
            </div>
            <form onSubmit={handleSavePortion} className="mt-4 space-y-4">
              <div>
                <label className={labelCls}>Portion name</label>
                <input
                  type="text"
                  value={pRow.name}
                  onChange={(e) => setPRow({ ...pRow, name: e.target.value })}
                  placeholder="Half / Full / Family Pack"
                  className={fieldCls}
                />
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className={labelCls}>Qty</label>
                  <input
                    type="number"
                    step="any"
                    min="0"
                    value={pRow.quantity}
                    onChange={(e) => setPRow({ ...pRow, quantity: e.target.value })}
                    className={`${fieldCls} font-mono`}
                  />
                </div>
                <div>
                  <label className={labelCls}>Unit</label>
                  <select value={pRow.unit} onChange={(e) => setPRow({ ...pRow, unit: e.target.value as PriceUnit })} className={fieldCls}>
                    {UNIT_OPTIONS.map((u) => (
                      <option key={u.value} value={u.value}>
                        {u.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Price (₹)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={pRow.price}
                    onChange={(e) => setPRow({ ...pRow, price: e.target.value })}
                    className={`${fieldCls} font-mono`}
                  />
                </div>
              </div>
              <div>
                <label className={labelCls}>
                  Waiter code <span className="normal-case font-normal text-slate-400">(optional, auto if empty)</span>
                </label>
                <input
                  type="text"
                  maxLength={24}
                  value={pRow.code}
                  onChange={(e) => setPRow({ ...pRow, code: e.target.value.toUpperCase() })}
                  placeholder={`${portionItem.item_code}-H`}
                  className={`${fieldCls} font-mono`}
                />
              </div>
              {editingVariant && (
                <p className="text-[11px] text-slate-400">
                  Price changes apply to new orders only. Old orders and bills keep the price they were billed at.
                </p>
              )}
              {portionError && (
                <div className="p-3 rounded-xl bg-rose-50 border border-rose-200 text-xs text-rose-700 whitespace-pre-line">
                  {portionError}
                </div>
              )}
              <div className="pt-1 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setPortionItem(null)}
                  className="px-4 py-2 rounded-xl text-sm font-medium text-slate-600 hover:bg-slate-100 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingPortion}
                  className="px-4 py-2 rounded-xl text-sm font-semibold bg-brand-600 hover:bg-brand-500 text-white shadow-xs cursor-pointer disabled:opacity-60"
                >
                  {isSavingPortion ? 'Saving...' : editingVariant ? 'Save changes' : 'Add portion'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

/** Server codes -> plain-language messages. */
function friendlyMenuError(err: any): string {
  switch (err?.code) {
    case 'ITEM_CODE_ALREADY_EXISTS':
      return 'This short code is already used by another dish. Try a different one (e.g. CB2).';
    case 'VARIANT_CODE_ALREADY_EXISTS':
      return 'A portion code is already used by another dish. Change the "Waiter code" under that portion.';
    case 'VARIANT_NAME_ALREADY_EXISTS':
      return 'This dish already has a portion with that name.';
    default:
      return err?.message || 'Something went wrong. Please try again.';
  }
}
