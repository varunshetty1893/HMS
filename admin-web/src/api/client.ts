/**
 * Base HTTP client for Admin Web.
 * Enforces Bearer JWT injection, 401 refresh token rotation, and error standard handling.
 */

// In dev, go through the Vite proxy (/api -> backend) so CORS / port mismatches can't break requests.
const BASE_URL = import.meta.env.DEV ? '/api/v1' : (import.meta.env.VITE_API_BASE_URL || '/api/v1');

export class ApiError extends Error {
  code: string;
  status: number;
  details?: any;

  constructor(message: string, code: string = 'API_ERROR', status: number = 500, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
    this.details = details;
  }
}

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve();
    }
  });
  failedQueue = [];
};

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('hms_admin_access_token');
  const headers = new Headers(options.headers || {});

  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;

  let response: Response;
  try {
    response = await fetch(url, { ...options, headers });
  } catch (err: any) {
    throw new ApiError(
      'Cannot reach the server. Make sure the backend is running (port 8000) and the database is up.',
      'NETWORK_ERROR',
      0
    );
  }

  // Handle 401 Token Expiration -> Trigger Refresh
  if (response.status === 401 && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then(() => apiClient<T>(endpoint, options));
    }

    isRefreshing = true;
    const refreshToken = localStorage.getItem('hms_admin_refresh_token');

    if (refreshToken) {
      try {
        const refreshResp = await fetch(`${BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });

        if (refreshResp.ok) {
          const tokenData = await refreshResp.json();
          localStorage.setItem('hms_admin_access_token', tokenData.access_token);
          localStorage.setItem('hms_admin_refresh_token', tokenData.refresh_token);
          processQueue(null);
          isRefreshing = false;
          return apiClient<T>(endpoint, options);
        }
      } catch (refreshErr) {
        processQueue(refreshErr);
      }
    }

    // Refresh failed or no refresh token -> logout
    isRefreshing = false;
    processQueue(new Error('Session expired'));
    localStorage.removeItem('hms_admin_access_token');
    localStorage.removeItem('hms_admin_refresh_token');
    localStorage.removeItem('hms_admin_user');
    window.location.href = '/login';
    throw new ApiError('Session expired. Please log in again.', 'SESSION_EXPIRED', 401);
  }

  // Handle non-2xx responses
  if (!response.ok) {
    let errJson: any = null;
    try {
      errJson = await response.json();
    } catch {
      // not JSON
    }

    const code = errJson?.error?.code || `HTTP_${response.status}`;
    const message = errJson?.error?.message || `Request failed with status ${response.status}`;
    const details = errJson?.error?.details;

    throw new ApiError(message, code, response.status, details);
  }

  if (response.status === 204) {
    return {} as T;
  }

  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('text/csv')) {
    const textData = await response.text();
    return textData as unknown as T;
  }

  return response.json();
}
