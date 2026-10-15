/**
 * Finds the table QR token in the current page URL.
 *
 * Supported shapes (first match wins):
 *   /q/<token>            <- the normal QR link
 *   ?qr=<token> or ?token=<token>
 *   #/q/<token>
 *   /<token>              <- QR printed with a base URL that is missing "/q"
 *   //<token>, /q//<token> <- QR printed with a trailing slash on the base URL
 *
 * Tokens may contain letters, digits, "_", "-" and (legacy "T-01.secret" form) ".".
 */
const PENDING_KEY = 'hms_pending_qr_token';

// A single path segment that looks like a token (not "index.html", "favicon.ico", ...).
const BARE_TOKEN_PATH = /^\/+([A-Za-z0-9_-]{20,}(?:\.[A-Za-z0-9_-]+)?)\/*$/;

function clean(raw: string | null | undefined): string | null {
  if (!raw) return null;
  let value = raw.trim();
  try {
    value = decodeURIComponent(value);
  } catch {
    // keep raw value if it is not valid URI encoding
  }
  return value.length > 0 ? value : null;
}

export function extractQrTokenFromUrl(loc: Location = window.location): string | null {
  const viaPath = loc.pathname.match(/\/q\/+([^/?#]+)/i);
  if (viaPath?.[1]) return clean(viaPath[1]);

  const params = new URLSearchParams(loc.search);
  const viaQuery = params.get('qr') || params.get('token');
  if (viaQuery) return clean(viaQuery);

  const viaHash = loc.hash.match(/\/q\/+([^/?#]+)/i);
  if (viaHash?.[1]) return clean(viaHash[1]);

  const bare = loc.pathname.match(BARE_TOKEN_PATH);
  if (bare?.[1]) return clean(bare[1]);

  return null;
}

/** Token saved from an earlier scan in this tab that has not been resolved yet. */
export function readPendingQrToken(): string | null {
  try {
    return clean(sessionStorage.getItem(PENDING_KEY));
  } catch {
    return null;
  }
}

export function savePendingQrToken(token: string): void {
  try {
    sessionStorage.setItem(PENDING_KEY, token);
  } catch {
    // storage may be blocked (private mode / in-app browsers); URL still has the token
  }
}

export function clearPendingQrToken(): void {
  try {
    sessionStorage.removeItem(PENDING_KEY);
  } catch {
    // ignore
  }
}

/**
 * Token from the URL, or one saved from a scan that failed part-way (so a page reload
 * retries the same table instead of dropping to the generic "scan your QR" screen).
 */
export function extractQrToken(loc: Location = window.location): string | null {
  return extractQrTokenFromUrl(loc) ?? readPendingQrToken();
}

/** URL path with the secret token removed, safe to show in the address bar. */
export function stripQrTokenFromPath(pathname: string): string {
  const cleaned = pathname.replace(/\/q\/+[^/?#]+/i, '/').replace(BARE_TOKEN_PATH, '/');
  return cleaned || '/';
}
