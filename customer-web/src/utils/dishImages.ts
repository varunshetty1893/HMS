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
 * Stable, dish-specific AI food photography fallback.  The fixed seed makes
 * each dish retain the same generated photo across menu refreshes.
 */
function onlineFoodPhoto(item: MenuItem): string {
  const prompt = `professional photorealistic food photography of ${item.name}, Indian restaurant menu dish, plated and appetising, natural warm light, no text, no logo, no people`;
  let seed = 0;
  for (const char of item.item_code) seed = (seed * 31 + char.charCodeAt(0)) >>> 0;
  return `https://image.pollinations.ai/prompt/${encodeURIComponent(prompt)}?width=640&height=480&nologo=true&seed=${seed}`;
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
