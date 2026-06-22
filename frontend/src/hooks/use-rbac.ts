'use client';
import { useAuthStore } from '@/stores/auth-store';
import { Role } from '@/types/auth';

export function useRBAC() {
  const { hasPermission, hasRole, hasMinimumRole, user } = useAuthStore();

  return {
    can: (permission: string) => hasPermission(permission),
    isRole: (role: Role) => hasRole(role),
    isAtLeast: (role: Role) => hasMinimumRole(role),
    role: user?.role,
    isViewer: user?.role === 'viewer',
    isOperator: hasMinimumRole('operator'),
    isManager: hasMinimumRole('manager'),
    isAdmin: hasMinimumRole('admin'),
    isSuperAdmin: user?.role === 'super_admin',
  };
}
