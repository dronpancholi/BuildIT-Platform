'use client';
import { ReactNode } from 'react';
import { useRBAC } from '@/hooks/use-rbac';
import { Shield } from 'lucide-react';

interface ProtectedPageProps {
  permission: string;
  children: ReactNode;
}

export function ProtectedPage({ permission, children }: ProtectedPageProps) {
  const { can } = useRBAC();
  if (!can(permission)) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4">
        <Shield className="w-12 h-12 text-red-400" />
        <h2 className="text-lg font-semibold text-slate-200">Access Denied</h2>
        <p className="text-sm text-slate-500">You don&apos;t have permission to access this page.</p>
        <p className="text-xs text-slate-600 font-mono">Required: {permission}</p>
      </div>
    );
  }
  return <>{children}</>;
}
