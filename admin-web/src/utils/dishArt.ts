import type { MenuItem } from '@/types/api';
import { resolveMediaUrl } from './env';

/** Real uploaded photo only; local cartoon art and guessed stock URLs are ignored. */
export function uploadedPhotoUrl(item: Pick<MenuItem, 'image_url'>): string | null {
  const raw = item.image_url?.trim();
  if (!raw) return null;
  if (raw.startsWith('/menu/') || raw.startsWith('/dishes/')) return null;
  if (/^https?:\/\/images\.unsplash\.com\//i.test(raw)) return null;
  return resolveMediaUrl(raw);
}

export function dishImageCandidates(item: Pick<MenuItem, 'image_url' | 'item_code'>): string[] {
  const photo = uploadedPhotoUrl(item);
  return photo ? [photo] : [];
}
