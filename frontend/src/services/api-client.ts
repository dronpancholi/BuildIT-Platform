import { API_BASE_URL } from '@/config/constants';
import { useTenantStore } from '@/stores/tenant-store';
import { useAuthStore } from '@/stores/auth-store';

export class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string,
    message: string,
    public retryable: boolean = false
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions extends Omit<RequestInit, 'method' | 'body'> {
  params?: Record<string, string | number | boolean | undefined>;
}

async function request<T>(
  endpoint: string,
  method: string,
  body?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  const { params, ...fetchOptions } = options;
  const authState = useAuthStore.getState();
  const tenantId = authState.user?.tenant_id || useTenantStore.getState().currentTenantId;

  const url = new URL(`${API_BASE_URL}${endpoint}`);
  url.searchParams.set('tenant_id', tenantId);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(fetchOptions.headers as Record<string, string>),
  };

  // Send the Bearer token obtained from /identity/dev/login (or future
  // Clerk JWT). Backend get_current_user resolves this and uses the
  // internal users row for tenant_id and role — we do NOT trust any
  // X-User-* headers.
  if (authState.token) {
    headers['Authorization'] = `Bearer ${authState.token}`;
  }

  const finalBody = (body && method !== 'GET')
    ? JSON.stringify({ ...(body as Record<string, unknown>), tenant_id: tenantId })
    : body
      ? JSON.stringify(body)
      : undefined;

  const response = await fetch(url.toString(), {
    method,
    headers,
    body: finalBody,
    ...fetchOptions,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = Array.isArray(data.detail)
      ? data.detail.map((e: Record<string, string>) => e.msg || e.message || JSON.stringify(e)).join('; ')
      : data.detail || data.error?.message || response.statusText;
    throw new ApiError(response.status, data.error?.error_code || 'UNKNOWN', detail, response.status >= 500);
  }

  return data.data !== undefined ? data.data : data;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) => request<T>(endpoint, 'GET', undefined, options),
  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) => request<T>(endpoint, 'POST', body, options),
  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) => request<T>(endpoint, 'PUT', body, options),
  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) => request<T>(endpoint, 'PATCH', body, options),
  delete: <T>(endpoint: string, options?: RequestOptions) => request<T>(endpoint, 'DELETE', undefined, options),
};
