import { Role } from '@/types/auth';

export const PERMISSIONS: Record<string, Role[]> = {
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

export function hasPermission(role: Role, permission: string): boolean {
  const allowed = PERMISSIONS[permission];
  if (!allowed) return false;
  return allowed.includes(role);
}
