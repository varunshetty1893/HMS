import type { MenuItem } from '@/types/api';
import { resolveMediaUrl } from './env';

/** Dedicated illustration per catalog item code (public/dishes/<ITEM_CODE>.svg). */
export function dishArtUrl(itemCode: string | null | undefined): string | null {
  const code = (itemCode ?? '').trim();
  return /^[A-Za-z0-9-]+$/.test(code) ? `/dishes/${code.toUpperCase()}.svg` : null;
}

/** Real uploaded photo first; old seeded stock-photo URLs and local art paths are ignored. */
export function uploadedPhotoUrl(item: Pick<MenuItem, 'image_url'>): string | null {
  const raw = item.image_url?.trim();
  if (!raw) return null;
  if (raw.startsWith('/menu/') || raw.startsWith('/dishes/')) return null;
  if (/^https?:\/\/images\.unsplash\.com\//i.test(raw)) return null;
  return resolveMediaUrl(raw);
}

export function dishImageCandidates(item: Pick<MenuItem, 'image_url' | 'item_code'>): string[] {
  const out: string[] = [];
  const photo = uploadedPhotoUrl(item);
  if (photo) out.push(photo);
  const art = dishArtUrl(item.item_code);
  if (art) out.push(art);
  return out;
}
