'use client';
import { ReactNode } from 'react';
import { useRBAC } from '@/hooks/use-rbac';

interface ProtectedActionProps {
  permission: string;
  children: ReactNode;
  fallback?: ReactNode;
}

export function ProtectedAction({ permission, children, fallback = null }: ProtectedActionProps) {
  const { can } = useRBAC();
  if (!can(permission)) return <>{fallback}</>;
  return <>{children}</>;
}
