export type Role = 'super_admin' | 'admin' | 'manager' | 'operator' | 'viewer';

export interface CurrentUser {
  id: string;
  tenant_id: string;
  email: string;
  name: string;
  role: Role;
  avatar_url?: string;
}

export interface AuthState {
  user: CurrentUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface Permission {
  resource: string;
  action: 'read' | 'write' | 'delete' | 'approve';
}
