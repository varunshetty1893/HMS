import type { MenuCategory, MenuItem } from '../types';
import { resolveMediaUrl } from './env';

/** A photo uploaded by the restaurant always takes precedence. */
function uploadedPhoto(item: MenuItem): string | null {
  const raw = item.image_url?.trim();
  if (!raw) return null;
  if (raw.startsWith('/menu/') || raw.startsWith('/dishes/')) return null;
  return resolveMediaUrl(raw);
}

/**
 * Stable real-food photo fallback.  These CDN photos do not have the daily
 * generation quota that caused the previous "free limit reached" placeholders.
 */
function onlineFoodPhoto(item: MenuItem): string {
  const photos = [
    'https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=640&h=480&q=80',
    'https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=640&h=480&q=80',
    'https://images.unsplash.com/photo-1596797038530-2c107229654b?auto=format&fit=crop&w=640&h=480&q=80',
    'https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=640&h=480&q=80',
  ];
  let hash = 0;
  for (const char of item.item_code) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return photos[hash % photos.length];
}

/** Ordered list of images to try: restaurant photo first, then a real-food photo. */
export function dishImageCandidates(item: MenuItem): string[] {
  const out: string[] = [];
  const photo = uploadedPhoto(item);
  if (photo) out.push(photo);
  out.push(onlineFoodPhoto(item));
  return out;
}

/** Representative picture for a category tile. */
const CATEGORY_COVER: [RegExp, string][] = [
  [/biryani/i, 'CB'],
  [/bread/i, 'BR-BN'],
  [/mandi|grilled/i, 'MD-GC'],
  [/cold & hot|hot drinks/i, 'BD-TEA'],
  [/milkshake|lassi/i, 'BM-CHK'],
  [/juice/i, 'BJ-ORG'],
  [/ice cream|dessert/i, 'DS-BRW'],
  [/rolls|quick bites/i, 'RK-CSH'],
  [/chinese/i, 'CH-CHN'],
  [/fish|seafood/i, 'SF-PRF'],
  [/snacks.*chicken/i, 'SC-C65'],
  [/snacks.*veg/i, 'SV-GM'],
  [/non-veg/i, 'NC-BC'],
  [/veg curries/i, 'VC-PBM'],
  [/meals/i, 'LM-VM'],
  [/rice|pulao/i, 'LR-VP'],
  [/soup/i, 'SP-TOM'],
  [/breakfast/i, 'BF-IDL'],
];

export function categoryCoverItem(category: MenuCategory): MenuItem | null {
  const match = CATEGORY_COVER.find(([re]) => re.test(category.name));
  if (match) {
    const hit = category.items.find((i) => i.item_code.toUpperCase() === match[1]);
    if (hit) return hit;
  }
  return category.items[0] ?? null;
}
