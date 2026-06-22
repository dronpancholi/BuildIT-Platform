const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";
const API_PREFIX = "/api/v1";

export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_BASE_URL;
  const base = raw.replace(/\/+$/, "");

  try {
    const url = new URL(base);
    if (!url.pathname.endsWith(API_PREFIX)) {
      url.pathname = `${url.pathname.replace(/\/+$/, "")}${API_PREFIX}`;
    }
    return url.toString().replace(/\/+$/, "");
  } catch {
    if (base.endsWith(API_PREFIX)) return base;
    return `${base}${API_PREFIX}`;
  }
}
