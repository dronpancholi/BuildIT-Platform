import { create } from 'zustand';
import { CurrentUser, Role } from '@/types/auth';
import { getApiBaseUrl } from '@/lib/api-url';

const STORAGE_KEY = 'buildit.auth';

interface PersistedAuth {
  token: string;
  user: CurrentUser;
}

function loadPersisted(): PersistedAuth | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as PersistedAuth;
  } catch {
    return null;
  }
}

function persistAuth(state: PersistedAuth | null): void {
  if (typeof window === 'undefined') return;
  try {
    if (state === null) {
      window.localStorage.removeItem(STORAGE_KEY);
    } else {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
  } catch {
    // Fail silently (private mode, quota, etc.)
  }
}

interface AuthState {
  user: CurrentUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  setUser: (user: CurrentUser | null) => void;
  login: (params?: { email?: string; user_id?: string; tenant_id?: string }) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  hasRole: (role: Role) => boolean;
  hasMinimumRole: (role: Role) => boolean;
}

const ROLE_HIERARCHY: Record<Role, number> = {
  viewer: 0,
  operator: 1,
  manager: 2,
  admin: 3,
  super_admin: 4,
};

const PERMISSIONS: Record<string, Role[]> = {
  'customers:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'customers:write': ['super_admin', 'admin', 'manager'],
  'customers:delete': ['super_admin', 'admin'],
  'campaigns:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'campaigns:write': ['super_admin', 'admin', 'manager'],
  'approvals:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'approvals:write': ['super_admin', 'admin', 'manager'],
  'approvals:approve': ['super_admin', 'admin', 'manager'],
  'reports:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'reports:write': ['super_admin', 'admin', 'manager'],
  'planning:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'planning:write': ['super_admin', 'admin', 'manager'],
  'planning:execute': ['super_admin', 'admin', 'manager'],
  'goal:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'goal:write': ['super_admin', 'admin', 'manager'],
  'system:read': ['super_admin', 'admin'],
  'system:write': ['super_admin'],
  'memory:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'memory:write': ['super_admin', 'admin', 'manager'],
  'agent:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'agent:write': ['super_admin', 'admin', 'manager'],
  'execution:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'execution:write': ['super_admin', 'admin', 'manager'],
  'action:read': ['super_admin', 'admin', 'manager', 'operator', 'viewer'],
  'action:write': ['super_admin', 'admin', 'manager'],
  'communications:read': ['super_admin', 'admin', 'manager', 'operator'],
  'communications:write': ['super_admin', 'admin', 'manager', 'operator'],
  'executive:read': ['super_admin', 'admin', 'manager', 'viewer'],
};

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,

  setUser: (user) => set({ user, isAuthenticated: !!user, isLoading: false }),

  login: async (params) => {
    set({ isLoading: true });

    // If we already have a persisted session, restore it and skip the
    // /dev/login call entirely. The backend's get_current_user will
    // re-validate the token on the next request, so an expired/missing
    // user row surfaces as a 401 from the API client.
    const persisted = loadPersisted();
    if (persisted && !params) {
      set({
        user: persisted.user,
        token: persisted.token,
        isAuthenticated: true,
        isLoading: false,
      });
      return;
    }

    // Otherwise, mint a fresh dev token from the backend. This endpoint
    // is gated server-side by APP_ENV=development AND DEV_AUTH_BYPASS=true.
    try {
      const res = await fetch(
        `${getApiBaseUrl()}/identity/dev/login`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(params ?? {}),
        }
      );
      if (!res.ok) {
        const detail = await res.text();
        throw new Error(`Dev login failed (${res.status}): ${detail}`);
      }
      const json = await res.json();
      const data = json.data ?? json;
      const token: string = data.access_token;
      const user: CurrentUser = {
        id: data.user_id,
        tenant_id: data.tenant_id,
        email: data.email,
        name: data.email,
        role: data.role,
      };
      persistAuth({ token, user });
      set({ user, token, isAuthenticated: true, isLoading: false });
    } catch (err) {
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
      throw err;
    }
  },

  logout: () => {
    persistAuth(null);
    set({ user: null, token: null, isAuthenticated: false, isLoading: false });
  },

  hasPermission: (permission: string) => {
    const { user } = get();
    if (!user) return false;
    const allowedRoles = PERMISSIONS[permission];
    if (!allowedRoles) return false;
    return allowedRoles.includes(user.role);
  },

  hasRole: (role: Role) => {
    const { user } = get();
    return user?.role === role;
  },

  hasMinimumRole: (role: Role) => {
    const { user } = get();
    if (!user) return false;
    return ROLE_HIERARCHY[user.role] >= ROLE_HIERARCHY[role];
  },
}));
