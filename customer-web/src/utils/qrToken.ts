/**
 * Finds the table QR token in the current page URL.
 *
 * Supported shapes (first match wins):
 *   /q/<token>            <- the normal QR link
 *   ?qr=<token> or ?token=<token>
 *   #/q/<token>
 *   /<token>              <- QR printed with a base URL that is missing "/q"
 *                            (tokens are 32 URL-safe characters)
 */
const BARE_TOKEN_PATH = /^\/([A-Za-z0-9_-]{32})\/?$/;

export function extractQrToken(loc: Location = window.location): string | null {
  const viaPath = loc.pathname.match(/\/q\/([^/?#]+)/);
  if (viaPath?.[1]) return viaPath[1];

  const params = new URLSearchParams(loc.search);
  const viaQuery = params.get('qr') || params.get('token');
  if (viaQuery) return viaQuery;

  const viaHash = loc.hash.match(/\/q\/([^/?#]+)/);
  if (viaHash?.[1]) return viaHash[1];

  const bare = loc.pathname.match(BARE_TOKEN_PATH);
  if (bare?.[1]) return bare[1];

  return null;
}

/** URL path with the secret token removed, safe to show in the address bar. */
export function stripQrTokenFromPath(pathname: string): string {
  const cleaned = pathname.replace(/\/q\/[^/?#]+/, '/').replace(BARE_TOKEN_PATH, '/');
  return cleaned || '/';
}
