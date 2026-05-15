export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function getTenantId(): string {
  if (typeof window === "undefined") return "00000000-0000-0000-0000-000000000001";
  try {
    const { useClientStore } = require("@/hooks/use-client");
    return useClientStore.getState().currentClient.id;
  } catch {
    return process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";
  }
}

export const MOCK_TENANT_ID = "00000000-0000-0000-0000-000000000001";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const tid = getTenantId();
  const sep = endpoint.includes("?") ? "&" : "?";
  const hasTenant = endpoint.includes("tenant_id=");
  const url = hasTenant
    ? `${API_BASE_URL}${endpoint}`
    : `${API_BASE_URL}${endpoint}${sep}tenant_id=${tid}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new ApiError(response.status, data.detail || response.statusText);
  }

  return data.data !== undefined ? data.data : data;
}
