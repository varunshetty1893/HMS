import React, { useEffect, useMemo, useState } from 'react';
import { menuApi } from '@/api/menuApi';
import { formatInr } from '@/utils/currency';
import {
  AlertCircle,
  ArrowDown,
  ArrowUp,
  Camera,
  Check,
  CheckCircle2,
  Eye,
  Flame,
  HelpCircle,
  ImagePlus,
  Layers,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  ToggleLeft,
  ToggleRight,
  Trash2,
  UtensilsCrossed,
  X,
} from 'lucide-react';
import {
  DietaryType,
  MenuCategory,
  MenuItem,
  PriceUnit,
  PricingStatus,
  PricingType,
  SpiceLevel,
} from '@/types/api';
import { usePageTheme } from '@/hooks/usePageTheme';
import { resolveMediaUrl } from '@/utils/env';

// ---------------------------------------------------------------------------
// Pricing Methods & Preset Configurations
// ---------------------------------------------------------------------------

export type PricingMethod = 'FIXED' | 'PORTIONS' | 'PIECES' | 'SIZES' | 'CUSTOM';

export interface PortionRowState {
  key: string;
  id?: string;
  name: string;
  quantity: string;
  unit: PriceUnit;
  price: string;
  code: string;
  isPortion: boolean;
  isActive: boolean;
  isDefault: boolean;
}

const UNIT_OPTIONS: { value: PriceUnit; label: string }[] = [
  { value: 'PORTION', label: 'portion' },
  { value: 'PIECE', label: 'pieces' },
  { value: 'PLATE', label: 'plate' },
  { value: 'BOWL', label: 'bowl' },
  { value: 'ML', label: 'ml' },
  { value: 'L', label: 'litre' },
  { value: 'GRAM', label: 'grams' },
  { value: 'KG', label: 'kg' },
];

const SPICE_OPTIONS: { value: SpiceLevel | ''; label: string; flames: number }[] = [
  { value: '', label: 'Not spicy / N/A', flames: 0 },
  { value: 'MILD', label: 'Mild', flames: 1 },
  { value: 'MEDIUM', label: 'Medium', flames: 2 },
  { value: 'HOT', label: 'Hot & Spicy', flames: 3 },
];

const DIET_OPTIONS: { value: DietaryType; label: string; dotColor: string; borderColor: string }[] = [
  { value: 'VEG', label: 'Vegetarian', dotColor: '#16a34a', borderColor: '#16a34a' },
  { value: 'NON_VEG', label: 'Non-Vegetarian', dotColor: '#dc2626', borderColor: '#dc2626' },
  { value: 'EGG', label: 'Contains Egg', dotColor: '#d97706', borderColor: '#d97706' },
];

let rowKeySeq = 0;
const createPortionRow = (patch: Partial<PortionRowState> = {}): PortionRowState => ({
  key: `p-row-${++rowKeySeq}`,
  name: '',
  quantity: '1',
  unit: 'PORTION',
  price: '',
  code: '',
  isPortion: false,
  isActive: true,
  isDefault: false,
  ...patch,
});

const METHOD_PRESETS: Record<PricingMethod, { title: string; subtitle: string; icon: string; rows: () => PortionRowState[] }> = {
  FIXED: {
    title: 'One Fixed Price',
    subtitle: 'Idli, Dosa, Meals, Naan, Individual Desserts',
    icon: '1️⃣',
    rows: () => [createPortionRow({ name: 'Standard', isPortion: false, isDefault: true })],
  },
  PORTIONS: {
    title: 'Named Portions',
    subtitle: 'Half / Full or Quarter / Half / Full',
    icon: '🍲',
    rows: () => [
      createPortionRow({ name: 'Half', quantity: '0.5', unit: 'PORTION', isPortion: true, isDefault: true }),
      createPortionRow({ name: 'Full', quantity: '1', unit: 'PORTION', isPortion: true, isDefault: false }),
    ],
  },
  PIECES: {
    title: 'Plate by Pieces',
    subtitle: 'Kebabs, Lollipops, Wings, Cutlets',
    icon: '🍗',
    rows: () => [
      createPortionRow({ name: '4 pieces', quantity: '4', unit: 'PIECE', isPortion: true, isDefault: true }),
      createPortionRow({ name: '8 pieces', quantity: '8', unit: 'PIECE', isPortion: true, isDefault: false }),
    ],
  },
  SIZES: {
    title: 'Named Sizes',
    subtitle: 'Fries, Milkshakes, Beverages, Pizzas',
    icon: '🥤',
    rows: () => [
      createPortionRow({ name: 'Regular', quantity: '1', unit: 'PORTION', isPortion: true, isDefault: true }),
      createPortionRow({ name: 'Large', quantity: '1.5', unit: 'PORTION', isPortion: true, isDefault: false }),
    ],
  },
  CUSTOM: {
    title: 'Custom Options',
    subtitle: 'Family Packs, Combos, Platters',
    icon: '🍱',
    rows: () => [
      createPortionRow({ name: 'Standard Pack', quantity: '1', unit: 'PORTION', isPortion: true, isDefault: true }),
      createPortionRow({ name: 'Family Pack', quantity: '2', unit: 'PORTION', isPortion: true, isDefault: false }),
    ],
  },
};

const suggestDishCode = (name: string): string => {
  const words = name.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return '';
  const letters =
    words.length === 1
      ? words[0].slice(0, 3)
      : words
          .map((w) => w[0])
          .join('')
          .slice(0, 4);
  return letters.toUpperCase().replace(/[^A-Z0-9]/g, '');
};

const suffixFromPortionName = (name: string, index: number): string => {
  const clean = name.replace(/\(.*?\)/g, '').trim();
  const digits = clean.match(/\d+/);
  if (digits) return digits[0];
  const words = clean.split(/\s+/).filter(Boolean);
  const first = words[0] || '';
  if (/^(half|full|small|medium|large|regular|single|mini|jumbo|quarter)$/i.test(first)) {
    return first[0].toUpperCase();
  }
  return first ? first.slice(0, 2).toUpperCase() : `P${index + 1}`;
};

const MAX_PHOTO_BYTES = 2 * 1024 * 1024;
const ALLOWED_PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

const validatePhotoFile = (file: File): string | null => {
  if (!ALLOWED_PHOTO_TYPES.includes(file.type)) {
    return 'Photo must be JPG, PNG or WebP format.';
  }
  if (file.size > MAX_PHOTO_BYTES) {
    return 'Photo size cannot exceed 2 MB.';
  }
  return null;
};

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export const MenuManagementPage: React.FC = () => {
  const { heading, sub } = usePageTheme();

  // Primary data states
  const [categories, setCategories] = useState<MenuCategory[]>([]);
  const [items, setItems] = useState<MenuItem[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // -------------------------------------------------------------------------
  // Redesigned Dish Modal (Unified Add & Edit)
  // -------------------------------------------------------------------------
  const [isDishModalOpen, setIsDishModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<MenuItem | null>(null);

  // Section 1: Basic dish info
  const [dishName, setDishName] = useState('');
  const [dishCode, setDishCode] = useState('');
  const [dishCodeTouched, setDishCodeTouched] = useState(false);
  const [categoryId, setCategoryId] = useState('');
  const [dietaryType, setDietaryType] = useState<DietaryType>('VEG');
  const [spiceLevel, setSpiceLevel] = useState<SpiceLevel | ''>('');
  const [description, setDescription] = useState('');
  const [servingDescription, setServingDescription] = useState('');
  const [isAvailable, setIsAvailable] = useState(true);

  // Section 2: Pricing method & portions
  const [pricingMethod, setPricingMethod] = useState<PricingMethod>('FIXED');
  const [portionRows, setPortionRows] = useState<PortionRowState[]>(() => METHOD_PRESETS.FIXED.rows());

  // Section 3: Seasonal pricing
  const [pricingType, setPricingType] = useState<PricingType>('FIXED');
  const [isSeasonalUnpriced, setIsSeasonalUnpriced] = useState(false);

  // Section 4: Photo
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreviewUrl, setPhotoPreviewUrl] = useState<string | null>(null);
  const [existingImageUrl, setExistingImageUrl] = useState<string | null>(null);
  const [removeExistingPhoto, setRemoveExistingPhoto] = useState(false);

  // Modal lifecycle & validation
  const [modalError, setModalError] = useState<string | null>(null);
  const [isSavingDish, setIsSavingDish] = useState(false);

  // -------------------------------------------------------------------------
  // Category Manager Modal
  // -------------------------------------------------------------------------
  const [isCategoryManagerOpen, setIsCategoryManagerOpen] = useState(false);
  const [newCatName, setNewCatName] = useState('');
  const [newCatDesc, setNewCatDesc] = useState('');
  const [catActionError, setCatActionError] = useState<string | null>(null);
  const [isSavingCategory, setIsSavingCategory] = useState(false);
  const [editingCatId, setEditingCatId] = useState<string | null>(null);
  const [editingCatName, setEditingCatName] = useState('');

  // -------------------------------------------------------------------------
  // Data Fetching
  // -------------------------------------------------------------------------
  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [cats, dishList] = await Promise.all([
        menuApi.listCategories(false),
        menuApi.listItems(undefined, false),
      ]);
      setCategories(cats.sort((a, b) => a.display_order - b.display_order));
      setItems(dishList.sort((a, b) => a.display_order - b.display_order));
      setError(null);
    } catch (err: any) {
      setError(friendlyMenuError(err));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // -------------------------------------------------------------------------
  // Dish Form Actions & Helpers
  // -------------------------------------------------------------------------
  const openAddDishModal = () => {
    setEditingItem(null);
    setDishName('');
    setDishCode('');
    setDishCodeTouched(false);
    setCategoryId(selectedCategory !== 'ALL' ? selectedCategory : (categories[0]?.id || ''));
    setDietaryType('VEG');
    setSpiceLevel('');
    setDescription('');
    setServingDescription('');
    setIsAvailable(true);
    setPricingMethod('FIXED');
    setPortionRows(METHOD_PRESETS.FIXED.rows());
    setPricingType('FIXED');
    setIsSeasonalUnpriced(false);
    setPhotoFile(null);
    setPhotoPreviewUrl(null);
    setExistingImageUrl(null);
    setRemoveExistingPhoto(false);
    setModalError(null);
    setIsDishModalOpen(true);
  };

  const openEditDishModal = (item: MenuItem) => {
    setEditingItem(item);
    setDishName(item.name);
    setDishCode(item.item_code);
    setDishCodeTouched(true);
    setCategoryId(item.category_id);
    setDietaryType((item.dietary_type || 'VEG') as DietaryType);
    setSpiceLevel((item.spice_level || '') as SpiceLevel | '');
    setDescription(item.description || '');
    setServingDescription(item.serving_description || '');
    setIsAvailable(item.is_available);

    const isSeason = item.pricing_type === 'SEASONAL';
    setPricingType(isSeason ? 'SEASONAL' : 'FIXED');

    // Reconstruct portion rows from existing variants
    const activeVariants = (item.variants || []).filter((v) => v.is_active);
    const hasPortions = activeVariants.some((v) => v.is_portion) || activeVariants.length > 1;

    // Detect pricing method
    let detectedMethod: PricingMethod = 'FIXED';
    if (!hasPortions && activeVariants.length <= 1) {
      detectedMethod = 'FIXED';
    } else if (activeVariants.some((v) => v.unit === 'PIECE')) {
      detectedMethod = 'PIECES';
    } else if (activeVariants.some((v) => /regular|large|small|medium/i.test(v.variant_name))) {
      detectedMethod = 'SIZES';
    } else {
      detectedMethod = 'PORTIONS';
    }
    setPricingMethod(detectedMethod);

    const rows: PortionRowState[] = activeVariants.map((v, i) => ({
      key: `existing-${v.id}`,
      id: v.id,
      name: v.variant_name || (hasPortions ? `Portion ${i + 1}` : 'Standard'),
      quantity: String(parseFloat(v.quantity_value) || 1),
      unit: v.unit,
      price: v.price !== null ? String(parseFloat(v.price)) : '',
      code: v.variant_code || '',
      isPortion: Boolean(v.is_portion),
      isActive: v.is_active,
      isDefault: v.is_default || i === 0,
    }));

    setPortionRows(rows.length > 0 ? rows : METHOD_PRESETS.FIXED.rows());
    setIsSeasonalUnpriced(isSeason && activeVariants.some((v) => v.price === null || v.pricing_status === 'SEASONAL_UNPRICED'));

    setPhotoFile(null);
    setPhotoPreviewUrl(null);
    setExistingImageUrl(item.image_url);
    setRemoveExistingPhoto(false);
    setModalError(null);
    setIsDishModalOpen(true);
  };

  const handleDishNameChange = (name: string) => {
    setDishName(name);
    if (!dishCodeTouched && !editingItem) {
      setDishCode(suggestDishCode(name));
    }
  };

  const switchPricingMethod = (method: PricingMethod) => {
    setPricingMethod(method);
    const preset = METHOD_PRESETS[method];
    if (!preset) return;
    setPortionRows((prevRows) => {
      const fresh = preset.rows();
      // Preserve existing prices where row indices match
      return fresh.map((r, i) => ({
        ...r,
        price: prevRows[i]?.price || (method === 'FIXED' ? prevRows[0]?.price || '' : ''),
      }));
    });
  };

  const updatePortionRow = (key: string, patch: Partial<PortionRowState>) => {
    setPortionRows((prev) => prev.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  };

  const addPortionRow = () => {
    setPortionRows((prev) => [
      ...prev,
      createPortionRow({
        name: `Option ${prev.length + 1}`,
        isPortion: true,
        unit: prev[0]?.unit || 'PORTION',
      }),
    ]);
  };

  const removePortionRow = (key: string) => {
    setPortionRows((prev) => (prev.length > 1 ? prev.filter((r) => r.key !== key) : prev));
  };

  const movePortionRow = (index: number, direction: 'UP' | 'DOWN') => {
    const target = direction === 'UP' ? index - 1 : index + 1;
    if (target < 0 || target >= portionRows.length) return;
    setPortionRows((prev) => {
      const copy = [...prev];
      const temp = copy[index];
      copy[index] = copy[target];
      copy[target] = temp;
      return copy;
    });
  };

  // Generate smart waiter codes for portions preview
  const portionCodes = useMemo(() => {
    const baseCode = dishCode.trim().toUpperCase();
    const usedCodes = new Set<string>();
    return portionRows.map((r, i) => {
      if (r.code.trim()) {
        const custom = r.code.trim().toUpperCase();
        usedCodes.add(custom);
        return custom;
      }
      if (!baseCode) return '';
      if (!r.isPortion) return baseCode;
      let suffix = suffixFromPortionName(r.name, i);
      let cand = `${baseCode}-${suffix}`.slice(0, 24);
      let n = 2;
      while (usedCodes.has(cand)) {
        cand = `${baseCode}-${suffix}${n++}`.slice(0, 24);
      }
      usedCodes.add(cand);
      return cand;
    });
  }, [portionRows, dishCode]);

  // Photo handlers
  const handlePhotoSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    const err = validatePhotoFile(file);
    if (err) {
      setModalError(err);
      return;
    }
    setModalError(null);
    setPhotoFile(file);
    setRemoveExistingPhoto(false);
    setPhotoPreviewUrl((old) => {
      if (old) URL.revokeObjectURL(old);
      return URL.createObjectURL(file);
    });
  };

  const handlePhotoRemove = () => {
    setPhotoFile(null);
    if (photoPreviewUrl) {
      URL.revokeObjectURL(photoPreviewUrl);
      setPhotoPreviewUrl(null);
    }
    if (existingImageUrl) {
      setRemoveExistingPhoto(true);
    }
  };

  // Validation
  const validateDishForm = (): string | null => {
    if (!dishName.trim()) return 'Dish name is required.';
    if (!dishCode.trim()) return 'Short code is required (e.g. CB). Waiters use this to find the dish.';
    if (!categoryId) return 'Please select a menu category.';

    const isSeasonal = pricingType === 'SEASONAL';

    if (portionRows.length === 0) return 'At least one pricing option is required.';

    const names = new Set<string>();
    for (let i = 0; i < portionRows.length; i++) {
      const row = portionRows[i];
      const label = `Option ${i + 1}`;

      if (row.isPortion && !row.name.trim()) {
        return `${label}: please enter a portion name (e.g. Half, 4 pieces).`;
      }
      if (row.isPortion) {
        const lowerName = row.name.trim().toLowerCase();
        if (names.has(lowerName)) {
          return `Duplicate portion name "${row.name.trim()}". Each portion must have a unique name.`;
        }
        names.add(lowerName);
      }

      const q = parseFloat(row.quantity);
      if (isNaN(q) || q <= 0) return `${label}: quantity must be greater than 0.`;

      if (!isSeasonal || !isSeasonalUnpriced) {
        const p = parseFloat(row.price);
        if (row.price.trim() === '' || isNaN(p) || p < 0) {
          return `${label} (${row.name || 'Price'}): enter a valid price (₹).`;
        }
      }
    }
    return null;
  };

  // Dish save submission
  const handleSaveDish = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationErr = validateDishForm();
    if (validationErr) {
      setModalError(validationErr);
      return;
    }

    setIsSavingDish(true);
    setModalError(null);

    const isSeasonal = pricingType === 'SEASONAL';
    const isUnpriced = isSeasonal && isSeasonalUnpriced;

    try {
      const variantsPayload = portionRows.map((r, i) => {
        const parsedPrice = isUnpriced || !r.price.trim() ? null : parseFloat(r.price).toFixed(2);
        return {
          id: r.id || undefined,
          variant_name: r.isPortion ? r.name.trim() : null,
          is_portion: r.isPortion,
          variant_code: portionCodes[i] || null,
          quantity_value: String(parseFloat(r.quantity) || 1),
          unit: r.unit,
          price: parsedPrice,
          pricing_status: (isUnpriced ? 'SEASONAL_UNPRICED' : 'ACTIVE') as PricingStatus,
          is_default: r.isDefault || i === 0,
          is_available: r.isActive,
          display_order: i,
        };
      });

      const dishPayload: Record<string, unknown> = {
        name: dishName.trim(),
        item_code: dishCode.trim().toUpperCase(),
        category_id: categoryId,
        dietary_type: dietaryType,
        spice_level: spiceLevel || null,
        description: description.trim() || null,
        serving_description: servingDescription.trim() || null,
        pricing_type: pricingType,
        is_available: isAvailable,
        variants: variantsPayload,
      };

      let savedItemId: string;

      if (editingItem) {
        const updated = await menuApi.updateItem(editingItem.id, dishPayload);
        savedItemId = updated.id;

        if (removeExistingPhoto) {
          try {
            await menuApi.deleteImage(savedItemId);
          } catch {
            // non-fatal if already removed
          }
        }
      } else {
        const created = await menuApi.createItem(dishPayload);
        savedItemId = created.id;
      }

      // Handle photo upload if a new file was selected
      if (photoFile) {
        try {
          await menuApi.uploadImage(savedItemId, photoFile);
        } catch (photoErr: any) {
          setNotice(`Dish saved, but photo upload failed: ${friendlyMenuError(photoErr)}`);
        }
      }

      setIsDishModalOpen(false);
      setNotice(`"${dishName.trim()}" ${editingItem ? 'updated' : 'created'} successfully!`);
      fetchData();
    } catch (err: any) {
      setModalError(friendlyMenuError(err));
    } finally {
      setIsSavingDish(false);
    }
  };

  // Instant availability toggle
  const handleToggleAvailability = async (item: MenuItem) => {
    try {
      const updated = await menuApi.setItemAvailability(
        item.id,
        !item.is_available,
        item.is_available ? 'Marked 86 / Sold out by Admin' : 'Back in stock'
      );
      setItems((prev) => prev.map((i) => (i.id === item.id ? { ...i, is_available: updated.is_available } : i)));
    } catch (err: any) {
      setError(friendlyMenuError(err));
    }
  };

  // -------------------------------------------------------------------------
  // Category Management Handlers
  // -------------------------------------------------------------------------
  const handleCreateCategory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCatName.trim()) return;
    setIsSavingCategory(true);
    setCatActionError(null);
    try {
      await menuApi.createCategory({
        name: newCatName.trim(),
        description: newCatDesc.trim() || null,
        display_order: categories.length + 1,
        is_active: true,
      });
      setNewCatName('');
      setNewCatDesc('');
      fetchData();
    } catch (err: any) {
      setCatActionError(friendlyMenuError(err));
    } finally {
      setIsSavingCategory(false);
    }
  };

  const handleUpdateCategoryName = async (catId: string) => {
    if (!editingCatName.trim()) return;
    setIsSavingCategory(true);
    setCatActionError(null);
    try {
      await menuApi.updateCategory(catId, { name: editingCatName.trim() });
      setEditingCatId(null);
      setEditingCatName('');
      fetchData();
    } catch (err: any) {
      setCatActionError(friendlyMenuError(err));
    } finally {
      setIsSavingCategory(false);
    }
  };

  const handleToggleCategoryActive = async (cat: MenuCategory) => {
    setCatActionError(null);
    try {
      if (cat.is_active) {
        await menuApi.deleteCategory(cat.id);
      } else {
        await menuApi.updateCategory(cat.id, { is_active: true });
      }
      fetchData();
    } catch (err: any) {
      setCatActionError(friendlyMenuError(err));
    }
  };

  const handleMoveCategory = async (index: number, direction: 'UP' | 'DOWN') => {
    const targetIndex = direction === 'UP' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= categories.length) return;

    const reordered = [...categories];
    const temp = reordered[index];
    reordered[index] = reordered[targetIndex];
    reordered[targetIndex] = temp;

    // Immediately update local UI
    setCategories(reordered);

    try {
      await menuApi.reorderCategories(
        reordered.map((c, i) => ({ id: c.id, display_order: i }))
      );
    } catch (err: any) {
      fetchData();
      setError(friendlyMenuError(err));
    }
  };

  // Reorder dishes within category
  const handleMoveItem = async (categoryItems: MenuItem[], index: number, direction: 'UP' | 'DOWN') => {
    const targetIndex = direction === 'UP' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= categoryItems.length) return;

    const copy = [...categoryItems];
    const temp = copy[index];
    copy[index] = copy[targetIndex];
    copy[targetIndex] = temp;

    const reorderedList = copy.map((it, i) => ({ id: it.id, display_order: i }));
    try {
      await menuApi.reorderItems(reorderedList);
      fetchData();
    } catch (err: any) {
      setError(friendlyMenuError(err));
    }
  };

  // -------------------------------------------------------------------------
  // Filtering & Computed Views
  // -------------------------------------------------------------------------
  const categoryDishCountMap = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const it of items) {
      counts[it.category_id] = (counts[it.category_id] || 0) + 1;
    }
    return counts;
  }, [items]);

  const filteredItems = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    return items.filter((item) => {
      const matchesCat = selectedCategory === 'ALL' || item.category_id === selectedCategory;
      const matchesQuery =
        !q ||
        item.name.toLowerCase().includes(q) ||
        item.item_code.toLowerCase().includes(q) ||
        (item.serving_description || '').toLowerCase().includes(q) ||
        item.variants.some((v) => (v.variant_code || '').toLowerCase().includes(q));
      return matchesCat && matchesQuery;
    });
  }, [items, selectedCategory, searchQuery]);

  return (
    <div className="p-4 sm:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Page Title & Top Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black tracking-tight" style={{ color: heading }}>
              Menu Management
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-brand-50 text-brand-700 font-bold border border-brand-200">
              Spice Hub
            </span>
          </div>
          <p className="text-sm mt-1" style={{ color: sub }}>
            Configure dishes, flexible pricing options (fixed, portions, plate by pieces, sizes), seasonal rates, and categories.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              setCatActionError(null);
              setIsCategoryManagerOpen(true);
            }}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-xs transition cursor-pointer"
          >
            <Layers className="w-4 h-4 text-brand-600" />
            <span>Manage Categories</span>
          </button>
          <button
            onClick={openAddDishModal}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-600/30 transition cursor-pointer"
          >
            <Plus className="w-4 h-4" strokeWidth={2.5} />
            <span>Add New Dish</span>
          </button>
        </div>
      </div>

      {/* Notifications & Error Banners */}
      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-sm text-rose-700 flex items-start justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
      {notice && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-200 text-sm text-emerald-800 flex items-start justify-between gap-3 shadow-xs">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
            <span>{notice}</span>
          </div>
          <button onClick={() => setNotice(null)} className="cursor-pointer">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Filter Tabs & Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Category Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 max-w-full scrollbar-none">
          <button
            onClick={() => setSelectedCategory('ALL')}
            className={`px-3.5 py-1.5 rounded-xl text-xs font-bold shrink-0 transition cursor-pointer flex items-center gap-1.5 ${
              selectedCategory === 'ALL'
                ? 'bg-slate-900 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
            }`}
          >
            <span>All Categories</span>
            <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${selectedCategory === 'ALL' ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-600'}`}>
              {items.length}
            </span>
          </button>

          {categories.filter((c) => c.is_active).map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedCategory(c.id)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold shrink-0 transition cursor-pointer flex items-center gap-1.5 ${
                selectedCategory === c.id
                  ? 'bg-brand-600 text-white shadow-sm'
                  : 'bg-white text-slate-600 hover:text-slate-900 border border-slate-200'
              }`}
            >
              <span>{c.name}</span>
              <span className={`text-[10px] px-1.5 py-0.2 rounded-full ${selectedCategory === c.id ? 'bg-brand-700 text-white' : 'bg-slate-100 text-slate-500'}`}>
                {categoryDishCountMap[c.id] || 0}
              </span>
            </button>
          ))}
        </div>

        {/* Search Field */}
        <div className="relative w-full md:w-80 shrink-0">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search dish, code (CB), or portion..."
            className="w-full pl-10 pr-4 py-2 rounded-xl bg-white border border-slate-200 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 shadow-xs"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Dishes Catalog Grid */}
      {isLoading ? (
        <div className="p-16 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
          <RefreshCw className="w-6 h-6 animate-spin text-brand-500" />
          <span className="text-sm">Loading Spice Hub catalog...</span>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="p-16 text-center rounded-2xl bg-white border border-slate-200 text-slate-500 shadow-xs flex flex-col items-center gap-3">
          <UtensilsCrossed className="w-10 h-10 text-slate-300" />
          <div>
            <p className="font-semibold text-slate-700">No dishes found</p>
            <p className="text-xs text-slate-400 mt-0.5">Try adjusting your category filter or search query</p>
          </div>
          <button
            onClick={openAddDishModal}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-brand-600 hover:bg-brand-500 text-white transition"
          >
            Add First Dish
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredItems.map((item, index) => {
            const activeVariants = item.variants.filter((v) => v.is_active);
            const isSeasonal = item.pricing_type === 'SEASONAL';
            const hasPortions = activeVariants.length > 1 || activeVariants.some((v) => v.is_portion);
            const cat = categories.find((c) => c.id === item.category_id);

            return (
              <div
                key={item.id}
                className={`rounded-2xl border p-4.5 flex flex-col justify-between transition-all relative ${
                  item.is_available
                    ? 'bg-white border-slate-200/90 hover:border-slate-300 hover:shadow-md'
                    : 'bg-slate-50/80 border-slate-200 opacity-75'
                }`}
              >
                <div>
                  {/* Top Bar: Short code, dietary badge, spice level, 86 toggle */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="px-2 py-0.5 rounded font-mono font-black text-xs bg-orange-50 text-orange-700 border border-orange-200/80">
                        {item.item_code}
                      </span>
                      {item.dietary_type && (
                        <span
                          className={`text-[10px] font-bold px-2 py-0.5 rounded-full border flex items-center gap-1 ${
                            item.dietary_type === 'VEG'
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : item.dietary_type === 'EGG'
                              ? 'bg-amber-50 text-amber-700 border-amber-200'
                              : 'bg-rose-50 text-rose-700 border-rose-200'
                          }`}
                        >
                          <span
                            className="w-1.5 h-1.5 rounded-full"
                            style={{
                              background:
                                item.dietary_type === 'VEG'
                                  ? '#16a34a'
                                  : item.dietary_type === 'EGG'
                                  ? '#d97706'
                                  : '#dc2626',
                            }}
                          />
                          {item.dietary_type === 'NON_VEG' ? 'Non-Veg' : item.dietary_type === 'VEG' ? 'Veg' : 'Egg'}
                        </span>
                      )}
                      {item.spice_level && (
                        <span className="flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded-full bg-orange-50 text-orange-700 border border-orange-200">
                          <Flame size={10} className="text-orange-600" />
                          <span>{item.spice_level}</span>
                        </span>
                      )}
                      {isSeasonal && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                          Seasonal
                        </span>
                      )}
                    </div>

                    {/* Stock availability toggle */}
                    <button
                      onClick={() => handleToggleAvailability(item)}
                      title={item.is_available ? 'Mark Sold Out (86)' : 'Mark In Stock'}
                      className="cursor-pointer"
                    >
                      {item.is_available ? (
                        <span className="flex items-center gap-1 text-emerald-600 font-semibold text-xs">
                          <ToggleRight className="w-5 h-5 text-emerald-500" />
                          <span>In Stock</span>
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-rose-600 font-semibold text-xs">
                          <ToggleLeft className="w-5 h-5 text-rose-400" />
                          <span>Sold Out</span>
                        </span>
                      )}
                    </button>
                  </div>

                  {/* Dish Title & Photo */}
                  <div className="flex items-start gap-3 mt-3">
                    {item.image_url && resolveMediaUrl(item.image_url) ? (
                      <img
                        src={resolveMediaUrl(item.image_url)!}
                        alt={item.name}
                        className="w-16 h-16 rounded-xl object-cover border border-slate-200 shrink-0 bg-slate-50"
                        loading="lazy"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    ) : (
                      <div className="w-16 h-16 rounded-xl border border-dashed border-slate-200 bg-slate-50 flex items-center justify-center shrink-0 text-slate-300">
                        <UtensilsCrossed size={20} />
                      </div>
                    )}

                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="text-base font-bold text-slate-900 leading-snug line-clamp-1">{item.name}</h3>
                        <button
                          onClick={() => openEditDishModal(item)}
                          title="Edit complete dish (name, pricing, portions, photo)"
                          className="p-1 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-slate-100 transition cursor-pointer"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                      </div>
                      <div className="text-[11px] font-medium text-slate-400 mt-0.5">
                        {cat?.name || 'Unassigned Category'}
                      </div>
                    </div>
                  </div>

                  {/* Serving Description if present */}
                  {item.serving_description && (
                    <div className="mt-2.5">
                      <span className="text-[11px] font-medium text-emerald-800 bg-emerald-50/90 px-2.5 py-1 rounded-lg inline-block border border-emerald-100">
                        💡 {item.serving_description}
                      </span>
                    </div>
                  )}

                  {/* Customer Description */}
                  {item.description && (
                    <p className="text-xs text-slate-500 mt-2 line-clamp-2 leading-relaxed">
                      {item.description}
                    </p>
                  )}
                </div>

                {/* Bottom: Pricing Options / Portions display */}
                <div className="mt-4 pt-3 border-t border-slate-100">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-medium">
                    <span>{hasPortions ? `${activeVariants.length} Portions` : 'Single Price'}</span>
                    {selectedCategory !== 'ALL' && (
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleMoveItem(filteredItems, index, 'UP')}
                          disabled={index === 0}
                          title="Move Dish Up"
                          className="p-0.5 hover:text-slate-800 disabled:opacity-20 cursor-pointer"
                        >
                          <ArrowUp size={13} />
                        </button>
                        <button
                          onClick={() => handleMoveItem(filteredItems, index, 'DOWN')}
                          disabled={index === filteredItems.length - 1}
                          title="Move Dish Down"
                          className="p-0.5 hover:text-slate-800 disabled:opacity-20 cursor-pointer"
                        >
                          <ArrowDown size={13} />
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    {activeVariants.map((v) => {
                      const isUnpriced = v.pricing_status === 'SEASONAL_UNPRICED' || v.price === null;
                      return (
                        <div
                          key={v.id}
                          className="flex items-center justify-between py-1 px-2.5 rounded-lg bg-slate-50 border border-slate-100 text-xs font-mono"
                        >
                          <div className="flex items-center gap-1.5 font-sans font-medium text-slate-700 min-w-0">
                            <span className="truncate">{v.is_portion ? v.variant_name : 'Fixed Price'}</span>
                            {v.variant_code && (
                              <span className="text-[10px] font-mono px-1 py-0.2 bg-white text-slate-400 rounded border border-slate-200">
                                {v.variant_code}
                              </span>
                            )}
                          </div>
                          <div className="font-bold text-slate-900 shrink-0">
                            {isUnpriced ? (
                              <span className="text-[11px] font-semibold text-blue-600 bg-blue-50 px-1.5 py-0.5 rounded">
                                Seasonal
                              </span>
                            ) : (
                              formatInr(v.price)
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* REDESIGNED UNIFIED ADD & EDIT DISH MODAL (Desktop Side-by-Side) */}
      {/* ------------------------------------------------------------------- */}
      {isDishModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/60 backdrop-blur-xs animate-fade-in">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden animate-scale-in">
            {/* Modal Header */}
            <div className="px-6 py-4.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-brand-100 text-brand-700 flex items-center justify-center">
                  <UtensilsCrossed size={18} />
                </div>
                <div>
                  <h2 className="text-lg font-black text-slate-900">
                    {editingItem ? `Edit Dish: ${editingItem.name}` : 'Add New Dish'}
                  </h2>
                  <p className="text-xs text-slate-500">
                    Configure dish name, short code, pricing model, portions, prices, and photo.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsDishModalOpen(false)}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 transition cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Error Banner inside modal */}
            {modalError && (
              <div className="px-6 py-3 bg-rose-50 border-b border-rose-200 text-xs font-medium text-rose-700 flex items-center gap-2">
                <AlertCircle size={15} className="shrink-0 text-rose-600" />
                <span>{modalError}</span>
              </div>
            )}

            {/* Main Modal Body: 2 Columns on Desktop */}
            <form onSubmit={handleSaveDish} className="flex-1 overflow-hidden flex flex-col md:flex-row">
              {/* Left Column: Form Controls (Scrollable) */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6 md:border-r border-slate-200">
                {/* SECTION 1: Basic Information */}
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <span className="w-5 h-5 rounded-full bg-slate-900 text-white text-[11px] font-bold flex items-center justify-center">
                      1
                    </span>
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                      Basic Dish Information
                    </h3>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {/* Dish Name */}
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Dish Name <span className="text-rose-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={dishName}
                        onChange={(e) => handleDishNameChange(e.target.value)}
                        placeholder="e.g. Chicken Biryani, Butter Naan, Chicken Kebab"
                        className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm font-medium text-slate-900 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                      />
                    </div>

                    {/* Short Code */}
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs font-bold text-slate-700">
                          Short Code <span className="text-rose-500">*</span>
                        </label>
                        <span className="text-[10px] text-slate-400">Waiters type this (e.g. CB)</span>
                      </div>
                      <input
                        type="text"
                        value={dishCode}
                        onChange={(e) => {
                          setDishCodeTouched(true);
                          setDishCode(e.target.value.toUpperCase());
                        }}
                        placeholder="e.g. CB"
                        maxLength={16}
                        className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 font-mono text-sm font-bold uppercase text-slate-900 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                      />
                    </div>

                    {/* Category */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Category <span className="text-rose-500">*</span>
                      </label>
                      <select
                        value={categoryId}
                        onChange={(e) => setCategoryId(e.target.value)}
                        className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm font-medium text-slate-900 bg-white focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                      >
                        <option value="">-- Choose Category --</option>
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name} {!c.is_active ? '(Inactive)' : ''}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Food Type */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Dietary Type</label>
                      <div className="grid grid-cols-3 gap-1.5">
                        {DIET_OPTIONS.map((opt) => (
                          <button
                            key={opt.value}
                            type="button"
                            onClick={() => setDietaryType(opt.value)}
                            className={`py-2 px-2 rounded-xl text-xs font-bold border transition flex items-center justify-center gap-1.5 cursor-pointer ${
                              dietaryType === opt.value
                                ? 'bg-slate-900 text-white border-slate-900 shadow-sm'
                                : 'bg-white text-slate-700 border-slate-200 hover:bg-slate-50'
                            }`}
                          >
                            <span
                              className="w-2 h-2 rounded-full shrink-0"
                              style={{ background: opt.dotColor }}
                            />
                            <span>{opt.label.split('-')[0]}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Spice Level */}
                    <div>
                      <label className="block text-xs font-bold text-slate-700 mb-1">Spice Level</label>
                      <select
                        value={spiceLevel}
                        onChange={(e) => setSpiceLevel(e.target.value as SpiceLevel | '')}
                        className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm font-medium text-slate-900 bg-white focus:outline-none focus:border-brand-500"
                      >
                        {SPICE_OPTIONS.map((s) => (
                          <option key={s.value} value={s.value}>
                            {s.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Serving Description */}
                    <div className="sm:col-span-2">
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs font-bold text-slate-700">
                          Customer-Facing Serving Description <span className="text-slate-400 font-normal">(optional)</span>
                        </label>
                        <span className="text-[10px] text-slate-400">e.g. 2 pieces served with sambar & chutney</span>
                      </div>
                      <input
                        type="text"
                        value={servingDescription}
                        onChange={(e) => setServingDescription(e.target.value)}
                        placeholder="e.g. 2 pieces with sambar and chutney, or Served with fragrant basmati rice"
                        maxLength={255}
                        className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm text-slate-900 focus:outline-none focus:border-brand-500"
                      />
                    </div>

                    {/* Customer-Facing Long Description */}
                    <div className="sm:col-span-2">
                      <label className="block text-xs font-bold text-slate-700 mb-1">
                        Description for Menu <span className="text-slate-400 font-normal">(optional)</span>
                      </label>
                      <textarea
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        rows={2}
                        placeholder="Mouth-watering dish details, marinades, preparation styles..."
                        className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 focus:outline-none focus:border-brand-500"
                      />
                    </div>
                  </div>
                </div>

                {/* SECTION 2: How is this dish sold? (Pricing Methods) */}
                <div className="pt-4 border-t border-slate-200">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="w-5 h-5 rounded-full bg-slate-900 text-white text-[11px] font-bold flex items-center justify-center">
                        2
                      </span>
                      <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                        How is this dish sold?
                      </h3>
                    </div>
                    <span className="text-xs text-slate-400 font-medium">Select pricing format</span>
                  </div>

                  {/* Pricing Method Selector Pills */}
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-4">
                    {(Object.keys(METHOD_PRESETS) as PricingMethod[]).map((m) => {
                      const info = METHOD_PRESETS[m];
                      const active = pricingMethod === m;
                      return (
                        <button
                          key={m}
                          type="button"
                          onClick={() => switchPricingMethod(m)}
                          className={`p-2.5 rounded-xl border text-left transition cursor-pointer flex flex-col justify-between ${
                            active
                              ? 'bg-brand-50/80 border-brand-500 ring-1 ring-brand-500'
                              : 'bg-white border-slate-200 hover:bg-slate-50'
                          }`}
                        >
                          <div>
                            <span className="text-lg mb-1 block">{info.icon}</span>
                            <div className={`text-xs font-bold leading-tight ${active ? 'text-brand-900' : 'text-slate-800'}`}>
                              {info.title}
                            </div>
                          </div>
                          <div className="text-[10px] text-slate-400 mt-1 line-clamp-1">
                            {info.subtitle}
                          </div>
                        </button>
                      );
                    })}
                  </div>

                  {/* Method Helper Notice */}
                  <div className="p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs text-slate-600 mb-4 flex items-center gap-2">
                    <HelpCircle size={15} className="text-brand-600 shrink-0" />
                    <span>
                      {pricingMethod === 'FIXED'
                        ? 'Fixed price: one clean price without portion dropdowns shown to the customer.'
                        : pricingMethod === 'PIECES'
                        ? 'Plate by pieces: define piece counts (e.g. 4 pcs, 8 pcs) for kebabs and snacks.'
                        : pricingMethod === 'SIZES'
                        ? 'Sizes: define cup or portion sizes (Regular, Large, Jumbo) for shakes and snacks.'
                        : pricingMethod === 'PORTIONS'
                        ? 'Named portions: traditional Half / Full plates with individual prices.'
                        : 'Custom options: define unique packages, family combos or platters.'}
                    </span>
                  </div>

                  {/* Portion Rows Table / Builder */}
                  <div className="space-y-3">
                    {portionRows.map((row, i) => (
                      <div
                        key={row.key}
                        className="p-3 rounded-xl border border-slate-200 bg-white hover:border-slate-300 transition shadow-2xs space-y-2.5"
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                            <span className="w-4 h-4 rounded-full bg-slate-100 text-slate-700 text-[10px] font-bold flex items-center justify-center">
                              {i + 1}
                            </span>
                            {row.isPortion ? row.name || `Option ${i + 1}` : 'Single Fixed Price'}
                          </span>

                          <div className="flex items-center gap-1">
                            {portionRows.length > 1 && (
                              <>
                                <button
                                  type="button"
                                  onClick={() => movePortionRow(i, 'UP')}
                                  disabled={i === 0}
                                  title="Move Up"
                                  className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-20 cursor-pointer"
                                >
                                  <ArrowUp size={13} />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => movePortionRow(i, 'DOWN')}
                                  disabled={i === portionRows.length - 1}
                                  title="Move Down"
                                  className="p-1 text-slate-400 hover:text-slate-700 disabled:opacity-20 cursor-pointer"
                                >
                                  <ArrowDown size={13} />
                                </button>
                                <button
                                  type="button"
                                  onClick={() => removePortionRow(row.key)}
                                  title="Remove Option"
                                  className="p-1 text-slate-400 hover:text-rose-600 transition cursor-pointer"
                                >
                                  <Trash2 size={13} />
                                </button>
                              </>
                            )}
                          </div>
                        </div>

                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                          {/* Portion Name (hidden for fixed price) */}
                          {row.isPortion && (
                            <div className="col-span-2 sm:col-span-1">
                              <label className="block text-[10px] font-bold uppercase text-slate-500 mb-0.5">
                                Option Name
                              </label>
                              <input
                                type="text"
                                value={row.name}
                                onChange={(e) => updatePortionRow(row.key, { name: e.target.value })}
                                placeholder="e.g. Half, 4 pcs"
                                className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs font-semibold text-slate-900 focus:outline-none focus:border-brand-500"
                              />
                            </div>
                          )}

                          {/* Price */}
                          <div className={row.isPortion ? 'col-span-1' : 'col-span-2'}>
                            <label className="block text-[10px] font-bold uppercase text-slate-500 mb-0.5">
                              Price (₹) {isSeasonalUnpriced ? '(Seasonal)' : '*'}
                            </label>
                            <input
                              type="number"
                              step="0.01"
                              min="0"
                              disabled={isSeasonalUnpriced}
                              value={row.price}
                              onChange={(e) => updatePortionRow(row.key, { price: e.target.value })}
                              placeholder={isSeasonalUnpriced ? 'Market Rate' : '0.00'}
                              className={`w-full px-2.5 py-1.5 rounded-lg border font-mono text-xs font-bold focus:outline-none ${
                                isSeasonalUnpriced
                                  ? 'bg-slate-100 text-slate-400 border-slate-200 cursor-not-allowed'
                                  : 'bg-white text-slate-900 border-slate-200 focus:border-brand-500'
                              }`}
                            />
                          </div>

                          {/* Internal kitchen quantity & unit */}
                          <div className={row.isPortion ? 'col-span-1' : 'col-span-1'}>
                            <label className="block text-[10px] font-bold uppercase text-slate-500 mb-0.5">
                              Kitchen Unit
                            </label>
                            <div className="flex gap-1">
                              <input
                                type="number"
                                step="any"
                                min="0.1"
                                value={row.quantity}
                                onChange={(e) => updatePortionRow(row.key, { quantity: e.target.value })}
                                className="w-14 px-2 py-1.5 rounded-lg border border-slate-200 text-xs font-mono text-slate-900 focus:outline-none"
                              />
                              <select
                                value={row.unit}
                                onChange={(e) => updatePortionRow(row.key, { unit: e.target.value as PriceUnit })}
                                className="flex-1 px-1.5 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-900 bg-white focus:outline-none"
                              >
                                {UNIT_OPTIONS.map((u) => (
                                  <option key={u.value} value={u.value}>
                                    {u.label}
                                  </option>
                                ))}
                              </select>
                            </div>
                          </div>

                          {/* Waiter Short Code */}
                          <div className={row.isPortion ? 'col-span-2 sm:col-span-1' : 'col-span-1'}>
                            <div className="flex items-center justify-between mb-0.5">
                              <label className="text-[10px] font-bold uppercase text-slate-500">
                                Waiter Code
                              </label>
                              <span className="text-[9px] text-slate-400">POS search</span>
                            </div>
                            <input
                              type="text"
                              value={row.code || portionCodes[i] || ''}
                              onChange={(e) => updatePortionRow(row.key, { code: e.target.value.toUpperCase() })}
                              placeholder={portionCodes[i] || 'AUTO'}
                              maxLength={24}
                              className="w-full px-2.5 py-1.5 rounded-lg border border-slate-200 font-mono text-xs font-bold uppercase text-slate-800 bg-slate-50/70 focus:outline-none focus:border-brand-500"
                            />
                          </div>
                        </div>
                      </div>
                    ))}

                    {/* Add Portion Button */}
                    {pricingMethod !== 'FIXED' && (
                      <button
                        type="button"
                        onClick={addPortionRow}
                        className="w-full py-2.5 rounded-xl border-2 border-dashed border-slate-200 hover:border-brand-500 hover:bg-brand-50/30 text-xs font-bold text-slate-600 hover:text-brand-600 transition flex items-center justify-center gap-1.5 cursor-pointer"
                      >
                        <Plus size={14} />
                        <span>Add Another Portion / Serving Option</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* SECTION 3: Seasonal / Market Pricing */}
                <div className="pt-4 border-t border-slate-200">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="w-5 h-5 rounded-full bg-slate-900 text-white text-[11px] font-bold flex items-center justify-center">
                      3
                    </span>
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                      Seasonal & Market Pricing
                    </h3>
                  </div>

                  <div className="p-3.5 rounded-2xl border border-slate-200 bg-slate-50/60 space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-xs font-bold text-slate-900">Seasonal / Market Rate Item</div>
                        <div className="text-[11px] text-slate-500">
                          For fresh seafood, crab, or rare cuts whose prices fluctuate daily.
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          const next = pricingType === 'SEASONAL' ? 'FIXED' : 'SEASONAL';
                          setPricingType(next);
                          if (next === 'FIXED') setIsSeasonalUnpriced(false);
                        }}
                        className="cursor-pointer"
                      >
                        {pricingType === 'SEASONAL' ? (
                          <ToggleRight size={28} className="text-blue-600" />
                        ) : (
                          <ToggleLeft size={28} className="text-slate-300" />
                        )}
                      </button>
                    </div>

                    {pricingType === 'SEASONAL' && (
                      <div className="pt-3 border-t border-slate-200 space-y-2">
                        <label className="flex items-center gap-2 text-xs font-semibold text-slate-700 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={isSeasonalUnpriced}
                            onChange={(e) => setIsSeasonalUnpriced(e.target.checked)}
                            className="w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-slate-300"
                          />
                          <span>Price currently unconfirmed (display "Seasonal Price — Ask Waiter")</span>
                        </label>
                        <p className="text-[11px] text-blue-700 bg-blue-50 p-2.5 rounded-xl border border-blue-200 leading-relaxed">
                          🛡️ <strong>Checkout Protection:</strong> When price is unconfirmed, customers will see "Seasonal Price" and online checkout for this dish is safely blocked. A waiter or cashier will confirm today's market rate.
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                {/* SECTION 4: Photograph */}
                <div className="pt-4 border-t border-slate-200">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="w-5 h-5 rounded-full bg-slate-900 text-white text-[11px] font-bold flex items-center justify-center">
                      4
                    </span>
                    <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900">
                      Dish Photograph
                    </h3>
                  </div>

                  <div className="flex items-start gap-4">
                    {/* Photo Preview Thumbnail */}
                    <div className="relative w-24 h-24 rounded-2xl border border-slate-200 bg-slate-50 overflow-hidden shrink-0 flex items-center justify-center shadow-xs">
                      {photoPreviewUrl ? (
                        <img src={photoPreviewUrl} alt="Preview" className="w-full h-full object-cover" />
                      ) : existingImageUrl && !removeExistingPhoto ? (
                        <img
                          src={resolveMediaUrl(existingImageUrl)!}
                          alt="Current"
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="text-slate-300 flex flex-col items-center gap-1">
                          <Camera size={22} />
                          <span className="text-[9px] font-medium text-slate-400">No Photo</span>
                        </div>
                      )}
                    </div>

                    {/* Upload / Replace Controls */}
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2 flex-wrap">
                        <label className="px-3.5 py-1.5 rounded-xl text-xs font-bold bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-xs cursor-pointer flex items-center gap-1.5 transition">
                          <ImagePlus size={14} className="text-brand-600" />
                          <span>{photoPreviewUrl || (existingImageUrl && !removeExistingPhoto) ? 'Replace Photo' : 'Upload Photo'}</span>
                          <input
                            type="file"
                            accept="image/jpeg,image/png,image/webp"
                            onChange={handlePhotoSelect}
                            className="hidden"
                          />
                        </label>

                        {(photoPreviewUrl || (existingImageUrl && !removeExistingPhoto)) && (
                          <button
                            type="button"
                            onClick={handlePhotoRemove}
                            className="px-3 py-1.5 rounded-xl text-xs font-semibold text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-200 transition cursor-pointer"
                          >
                            Remove
                          </button>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 leading-relaxed">
                        JPG, PNG or WebP up to 2 MB. Use high-quality photos of the actual prepared dish. Cartoon or placeholder images are strongly discouraged.
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Right Column: Real-Time Live Customer Menu Preview */}
              <div className="w-full md:w-80 bg-slate-50/70 p-6 flex flex-col justify-between overflow-y-auto border-t md:border-t-0 border-slate-200">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-black uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                      <Eye size={14} className="text-brand-600" />
                      <span>Customer Preview</span>
                    </span>
                    <span className="text-[10px] font-bold text-emerald-700 bg-emerald-100/70 px-2 py-0.5 rounded-full">
                      Live
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mb-4">
                    This reflects how guests see this dish on their phones via QR code:
                  </p>

                  {/* Customer Card Mockup */}
                  <div className="bg-white rounded-2xl border border-slate-200/90 shadow-md p-3.5 space-y-3">
                    {/* Mock Image */}
                    <div className="relative w-full aspect-[4/3] rounded-xl overflow-hidden bg-slate-100 flex items-center justify-center border border-slate-100">
                      {photoPreviewUrl ? (
                        <img src={photoPreviewUrl} alt="Preview" className="w-full h-full object-cover" />
                      ) : existingImageUrl && !removeExistingPhoto ? (
                        <img src={resolveMediaUrl(existingImageUrl)!} alt="Preview" className="w-full h-full object-cover" />
                      ) : (
                        <UtensilsCrossed size={28} className="text-slate-300" />
                      )}

                      {/* Dietary dot badge */}
                      <div className="absolute top-2 left-2 bg-white/95 rounded-md p-1 shadow-xs border border-slate-100">
                        <div
                          className="w-2.5 h-2.5 rounded-full"
                          style={{
                            background:
                              dietaryType === 'VEG'
                                ? '#16a34a'
                                : dietaryType === 'EGG'
                                ? '#d97706'
                                : '#dc2626',
                          }}
                        />
                      </div>

                      {/* Spice indicator */}
                      {spiceLevel && (
                        <div className="absolute top-2 right-2 bg-white/95 rounded-md px-1.5 py-0.5 shadow-xs border border-slate-100 flex items-center gap-0.5 text-[10px] font-bold text-orange-600">
                          <Flame size={11} />
                          <span>{spiceLevel}</span>
                        </div>
                      )}
                    </div>

                    {/* Dish title & short code */}
                    <div>
                      <div className="flex items-center gap-1.5 mb-1">
                        <span className="text-[10px] font-mono font-bold text-orange-700 bg-orange-50 px-1.5 py-0.2 rounded border border-orange-200">
                          {dishCode || 'CODE'}
                        </span>
                        <span className="text-[10px] text-slate-400">
                          {categories.find((c) => c.id === categoryId)?.name || 'Category'}
                        </span>
                      </div>
                      <h4 className="font-bold text-sm text-slate-900 leading-snug">
                        {dishName || 'Dish Name'}
                      </h4>
                    </div>

                    {/* Serving description pill */}
                    {servingDescription ? (
                      <div className="text-[11px] font-medium text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md inline-block border border-emerald-100">
                        {servingDescription}
                      </div>
                    ) : null}

                    {/* Description */}
                    {description && (
                      <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                        {description}
                      </p>
                    )}

                    {/* Price and Add button */}
                    <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                      <div>
                        {pricingType === 'SEASONAL' && isSeasonalUnpriced ? (
                          <span className="text-xs font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-200">
                            Seasonal Price
                          </span>
                        ) : (
                          <div>
                            <span className="font-black text-sm font-mono text-slate-900">
                              {portionRows[0]?.price ? formatInr(portionRows[0].price) : '₹ --'}
                            </span>
                            {portionRows.length > 1 && (
                              <span className="text-[10px] text-slate-400 ml-1">onwards</span>
                            )}
                          </div>
                        )}
                      </div>

                      <button
                        type="button"
                        disabled={pricingType === 'SEASONAL' && isSeasonalUnpriced}
                        className={`px-3 py-1.5 rounded-xl font-bold text-xs flex items-center gap-1 transition ${
                          pricingType === 'SEASONAL' && isSeasonalUnpriced
                            ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                            : 'bg-brand-600 text-white shadow-xs'
                        }`}
                      >
                        <Plus size={12} strokeWidth={3} />
                        <span>Add</span>
                      </button>
                    </div>

                    {/* Portions preview chips */}
                    {portionRows.length > 1 && (
                      <div className="flex gap-1 flex-wrap pt-1">
                        {portionRows.map((r, i) => (
                          <span
                            key={r.key}
                            className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-slate-50 text-slate-600 border border-slate-200"
                          >
                            {r.name || `Option ${i + 1}`}
                            {r.price && !isSeasonalUnpriced ? ` • ${formatInr(r.price)}` : ''}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Modal Footer Controls */}
                <div className="mt-6 pt-4 border-t border-slate-200 space-y-2">
                  <button
                    type="submit"
                    disabled={isSavingDish}
                    className="w-full py-3 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-bold text-sm shadow-md shadow-brand-600/30 transition flex items-center justify-center gap-2 cursor-pointer"
                  >
                    {isSavingDish ? (
                      <>
                        <RefreshCw size={15} className="animate-spin" />
                        <span>Saving Dish...</span>
                      </>
                    ) : (
                      <>
                        <Check size={16} strokeWidth={2.5} />
                        <span>{editingItem ? 'Save All Changes' : 'Create Dish'}</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => setIsDishModalOpen(false)}
                    className="w-full py-2.5 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-100 transition cursor-pointer"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------------- */}
      {/* CATEGORY MANAGER MODAL (Phase 3: Reorder, Rename, Deactivate) */}
      {/* ------------------------------------------------------------------- */}
      {isCategoryManagerOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-fade-in">
          <div className="bg-white rounded-3xl shadow-2xl border border-slate-200 w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-scale-in">
            {/* Header */}
            <div className="px-6 py-4.5 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-brand-100 text-brand-700 flex items-center justify-center">
                  <Layers size={18} />
                </div>
                <div>
                  <h2 className="text-lg font-black text-slate-900">Category Management</h2>
                  <p className="text-xs text-slate-500">
                    Reorder display order, rename categories, or safely deactivate without breaking order history.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsCategoryManagerOpen(false)}
                className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 transition cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Error Banner */}
            {catActionError && (
              <div className="px-6 py-3 bg-rose-50 border-b border-rose-200 text-xs font-medium text-rose-700 flex items-center gap-2">
                <AlertCircle size={15} className="shrink-0 text-rose-600" />
                <span>{catActionError}</span>
              </div>
            )}

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Add New Category Card */}
              <form onSubmit={handleCreateCategory} className="p-4 rounded-2xl bg-brand-50/40 border border-brand-100 space-y-3">
                <h4 className="text-xs font-bold uppercase tracking-wider text-brand-900 flex items-center gap-1.5">
                  <Plus size={14} className="text-brand-600" />
                  <span>Create New Category</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <input
                      type="text"
                      value={newCatName}
                      onChange={(e) => setNewCatName(e.target.value)}
                      placeholder="Category name (e.g. Biryani, Mandi)"
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-medium text-slate-900 bg-white focus:outline-none focus:border-brand-500"
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      value={newCatDesc}
                      onChange={(e) => setNewCatDesc(e.target.value)}
                      placeholder="Optional description"
                      className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-900 bg-white focus:outline-none focus:border-brand-500"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={isSavingCategory || !newCatName.trim()}
                    className="px-4 py-2 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-bold text-xs shadow-xs transition cursor-pointer"
                  >
                    Add Category
                  </button>
                </div>
              </form>

              {/* Categories Reorder Table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs font-bold text-slate-500 uppercase tracking-wider px-2">
                  <span>Category & Items</span>
                  <span>Order & Actions</span>
                </div>

                {categories.map((cat, idx) => (
                  <div
                    key={cat.id}
                    className={`p-3.5 rounded-2xl border transition flex items-center justify-between gap-3 ${
                      cat.is_active
                        ? 'bg-white border-slate-200 shadow-2xs'
                        : 'bg-slate-50/70 border-slate-200 opacity-60'
                    }`}
                  >
                    {/* Category details & inline rename */}
                    <div className="flex-1 min-w-0">
                      {editingCatId === cat.id ? (
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={editingCatName}
                            onChange={(e) => setEditingCatName(e.target.value)}
                            className="px-2.5 py-1 rounded-lg border border-brand-500 text-xs font-bold text-slate-900 focus:outline-none"
                            autoFocus
                          />
                          <button
                            type="button"
                            onClick={() => handleUpdateCategoryName(cat.id)}
                            className="p-1 rounded-lg bg-brand-600 text-white text-xs font-bold"
                          >
                            <Check size={14} />
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingCatId(null)}
                            className="p-1 text-slate-400 hover:text-slate-600 text-xs"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      ) : (
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-slate-900">{cat.name}</span>
                          <button
                            onClick={() => {
                              setEditingCatId(cat.id);
                              setEditingCatName(cat.name);
                            }}
                            title="Rename Category"
                            className="text-slate-400 hover:text-brand-600 transition p-1"
                          >
                            <Pencil size={12} />
                          </button>
                        </div>
                      )}

                      <div className="flex items-center gap-2 text-xs text-slate-400 mt-0.5">
                        <span>{categoryDishCountMap[cat.id] || 0} dishes</span>
                        <span>•</span>
                        <span className={cat.is_active ? 'text-emerald-600 font-medium' : 'text-slate-400'}>
                          {cat.is_active ? 'Active on menu' : 'Deactivated'}
                        </span>
                      </div>
                    </div>

                    {/* Actions: Move Up / Down & Safe Toggle */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        onClick={() => handleMoveCategory(idx, 'UP')}
                        disabled={idx === 0}
                        title="Move Up"
                        className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-20 cursor-pointer"
                      >
                        <ArrowUp size={14} />
                      </button>
                      <button
                        onClick={() => handleMoveCategory(idx, 'DOWN')}
                        disabled={idx === categories.length - 1}
                        title="Move Down"
                        className="p-1.5 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-20 cursor-pointer"
                      >
                        <ArrowDown size={14} />
                      </button>

                      <button
                        onClick={() => handleToggleCategoryActive(cat)}
                        title={cat.is_active ? 'Safely deactivate category' : 'Reactivate category'}
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold transition cursor-pointer ${
                          cat.is_active
                            ? 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200'
                            : 'bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200'
                        }`}
                      >
                        {cat.is_active ? 'Deactivate' : 'Reactivate'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Footer */}
            <div className="px-6 py-4 border-t border-slate-200 bg-slate-50/70 flex justify-end">
              <button
                onClick={() => setIsCategoryManagerOpen(false)}
                className="px-5 py-2 rounded-xl text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white transition cursor-pointer"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

/** Convert backend error responses into actionable, plain-language text. */
function friendlyMenuError(err: any): string {
  switch (err?.code) {
    case 'ITEM_CODE_ALREADY_EXISTS':
      return 'This short code is already in use by another dish. Please choose a unique short code.';
    case 'VARIANT_CODE_ALREADY_EXISTS':
      return 'One of the waiter codes is already in use. Please modify the waiter code under that portion.';
    case 'VARIANT_NAME_ALREADY_EXISTS':
      return 'This dish already has a portion with that name.';
    case 'ITEM_NOT_FOUND':
      return 'Dish was not found or has been deactivated.';
    case 'SEASONAL_PRICE_UNAVAILABLE':
      return 'This dish has seasonal pricing with no price confirmed. Orders cannot be accepted until a confirmed price is set.';
    default:
      return err?.message || 'Something went wrong. Please check the values and try again.';
  }
}
