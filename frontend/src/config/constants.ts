import { getApiBaseUrl } from '@/lib/api-url';

export const API_BASE_URL = getApiBaseUrl();
export const DEFAULT_TENANT_ID = '00000000-0000-0000-0000-000000000001';
export const QUERY_STALE_TIME = 60 * 1000;
export const QUERY_CACHE_TIME = 5 * 60 * 1000;
export const DEBOUNCE_DELAY = 300;
export const PAGE_SIZE = 50;
export const MAX_PAGE_SIZE = 200;

export const ROUTES = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  CLIENTS: '/dashboard/clients',
  CAMPAIGNS: '/dashboard/campaigns',
  KEYWORDS: '/dashboard/keywords',
  PLANS: '/dashboard/plans',
  APPROVALS: '/dashboard/approvals',
  REPORTS: '/dashboard/reports',
  SETTINGS: '/dashboard/settings',
  OPERATIONS: '/dashboard/operations',
} as const;

export const ROLE_HIERARCHY: Record<string, number> = {
  viewer: 0,
  operator: 1,
  manager: 2,
  admin: 3,
  super_admin: 4,
};
