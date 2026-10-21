import type { MenuCategory, MenuItem } from '../types';
import { resolveMediaUrl } from './env';

/** A photo uploaded by the restaurant always takes precedence. */
function uploadedPhoto(item: MenuItem): string | null {
  const raw = item.image_url?.trim();
  if (!raw) return null;
  if (raw.startsWith('/menu/') || raw.startsWith('/dishes/')) return null;
  // These were the previous guessed stock URLs. They were not one-to-one
  // dish photos, so never allow an old value to reintroduce a mismatch.
  if (/^https?:\/\/images\.unsplash\.com\//i.test(raw)) return null;
  return resolveMediaUrl(raw);
}

/**
 * Never substitute an unrelated stock photo. A photo is shown only when it
 * belongs to this dish (uploaded by the restaurant or explicitly saved on the
 * menu item). This prevents mistakes such as samosas shown for Plain Dosa.
 */
export function dishImageCandidates(item: MenuItem): string[] {
  const photo = uploadedPhoto(item);
  return photo ? [photo] : [];
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
