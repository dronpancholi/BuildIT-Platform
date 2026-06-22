'use client';

import { useState } from 'react';
import { Search, Bell } from 'lucide-react';
import { useCommandPaletteStore } from '@/stores/command-palette-store';
import { useNotificationStore } from '@/stores/notification-store';
import { Breadcrumbs } from './breadcrumbs';
import { NotificationCenter } from './notification-center';
import { ProfileMenu } from './profile-menu';

export function TopNav() {
  const openPalette = useCommandPaletteStore((s) => s.open);
  const unreadCount = useNotificationStore((s) => s.unreadCount);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="h-14 border-b border-surface-border bg-surface-card/50 backdrop-blur-sm sticky top-0 z-10 flex items-center justify-between px-6">
      {/* Left */}
      <div className="flex items-center gap-4">
        <Breadcrumbs />
      </div>

      {/* Right */}
      <div className="flex items-center gap-2">
        {/* Search / CMD+K */}
        <button
          onClick={openPalette}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-surface-border bg-surface-card text-sm text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-colors"
        >
          <Search className="w-4 h-4" />
          <span className="hidden sm:inline">Search</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface-dark text-[10px] text-slate-500 font-mono">
            <span className="text-xs">⌘</span>K
          </kbd>
        </button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => {
              setNotificationsOpen(!notificationsOpen);
              setProfileOpen(false);
            }}
            className="relative p-2 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-surface-card transition-colors"
          >
            <Bell className="w-5 h-5" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 w-4 h-4 rounded-full bg-platform-500 text-[10px] font-bold text-white flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>
          <NotificationCenter
            open={notificationsOpen}
            onClose={() => setNotificationsOpen(false)}
          />
        </div>

        {/* Profile */}
        <div className="relative">
          <button
            onClick={() => {
              setProfileOpen(!profileOpen);
              setNotificationsOpen(false);
            }}
            className="flex items-center gap-2 p-1.5 rounded-lg hover:bg-surface-card transition-colors"
          >
            <div className="w-7 h-7 rounded-full bg-platform-600/20 flex items-center justify-center text-[11px] font-medium text-platform-400">
              A
            </div>
          </button>
          <ProfileMenu
            open={profileOpen}
            onClose={() => setProfileOpen(false)}
          />
        </div>
      </div>
    </header>
  );
}
