import type { MenuCategory, MenuItem } from '../types';
import { resolveMediaUrl } from './env';

/** Dedicated illustration for a catalog item, keyed by its item code (public/dishes/<CODE>.svg). */
export function dishArtUrl(itemCode: string | null | undefined): string | null {
  const code = (itemCode ?? '').trim();
  return /^[A-Za-z0-9-]+$/.test(code) ? `/dishes/${code.toUpperCase()}.svg` : null;
}

/**
 * Old seeded stock-photo URLs (guessed, shared between dishes) and retired `/menu/` pictures are
 * ignored. Only a photo the restaurant uploaded (API `/static/...`, CDN or any other real URL) wins.
 */
function uploadedPhoto(item: MenuItem): string | null {
  const raw = item.image_url?.trim();
  if (!raw) return null;
  if (raw.startsWith('/menu/') || raw.startsWith('/dishes/')) return null;
  if (/^https?:\/\/images\.unsplash\.com\//i.test(raw)) return null;
  return resolveMediaUrl(raw);
}

/** Ordered list of images to try: real photo first, then the item's own illustration. */
export function dishImageCandidates(item: MenuItem): string[] {
  const out: string[] = [];
  const photo = uploadedPhoto(item);
  if (photo) out.push(photo);
  const art = dishArtUrl(item.item_code);
  if (art) out.push(art);
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
