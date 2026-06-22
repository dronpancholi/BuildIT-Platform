'use client';

import { User, Settings, LogOut } from 'lucide-react';
import { useAuthStore } from '@/stores/auth-store';
import { useAuth } from '@/hooks/use-auth';
import { getInitials } from '@/lib/utils';

interface ProfileMenuProps {
  open: boolean;
  onClose: () => void;
}

export function ProfileMenu({ open, onClose }: ProfileMenuProps) {
  const user = useAuthStore((s) => s.user);
  const { logout } = useAuth();

  if (!open) return null;

  const handleLogout = () => {
    logout();
    onClose();
  };

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div className="absolute right-0 top-full mt-2 w-64 z-50 rounded-xl border border-surface-border bg-surface-card shadow-xl shadow-black/30 overflow-hidden">
        {/* User info */}
        <div className="px-4 py-3 border-b border-surface-border">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-platform-600/20 flex items-center justify-center text-xs font-medium text-platform-400">
              {user ? getInitials(user.name) : '?'}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-200 truncate">
                {user?.name ?? 'Unknown'}
              </p>
              <p className="text-xs text-slate-500 truncate">
                {user?.email ?? ''}
              </p>
            </div>
          </div>
        </div>

        {/* Menu items */}
        <div className="p-1.5">
          <button
            onClick={onClose}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-surface-dark hover:text-slate-100 transition-colors"
          >
            <User className="w-4 h-4" />
            Profile
          </button>
          <button
            onClick={onClose}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-300 hover:bg-surface-dark hover:text-slate-100 transition-colors"
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
        </div>

        <div className="border-t border-surface-border p-1.5">
          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </div>
    </>
  );
}
