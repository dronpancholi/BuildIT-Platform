'use client';


import {
  Bell,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Info,
  CheckCheck,
  Trash2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useNotificationStore } from '@/stores/notification-store';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';

const TYPE_ICONS = {
  success: CheckCircle2,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
} as const;

const TYPE_COLORS = {
  success: 'text-emerald-400',
  error: 'text-red-400',
  warning: 'text-amber-400',
  info: 'text-blue-400',
} as const;

function timeAgo(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface NotificationCenterProps {
  open: boolean;
  onClose: () => void;
}

export function NotificationCenter({ open, onClose }: NotificationCenterProps) {
  const { notifications, unreadCount, markAsRead, markAllAsRead, clearAll } =
    useNotificationStore();

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-40" onClick={onClose} />
      <div className="absolute right-0 top-full mt-2 w-96 z-50 rounded-xl border border-surface-border bg-surface-card shadow-xl shadow-black/30">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-200">Notifications</h3>
            {unreadCount > 0 && (
              <Badge variant="default" className="px-1.5 py-0 text-[10px]">
                {unreadCount}
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-1">
            {unreadCount > 0 && (
              <button
                onClick={markAllAsRead}
                className="p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-surface-card transition-colors"
                title="Mark all as read"
              >
                <CheckCheck className="w-4 h-4" />
              </button>
            )}
            {notifications.length > 0 && (
              <button
                onClick={clearAll}
                className="p-1.5 rounded-md text-slate-400 hover:text-red-400 hover:bg-surface-card transition-colors"
                title="Clear all"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Notification list */}
        {notifications.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-slate-500">
            <Bell className="w-8 h-8 mb-2 opacity-40" />
            <p className="text-sm">No notifications yet</p>
          </div>
        ) : (
          <ScrollArea className="max-h-80">
            <div className="divide-y divide-surface-border">
              {notifications.map((notification) => {
                const Icon = TYPE_ICONS[notification.type];
                const color = TYPE_COLORS[notification.type];
                return (
                  <button
                    key={notification.id}
                    onClick={() => markAsRead(notification.id)}
                    className={cn(
                      'w-full flex items-start gap-3 px-4 py-3 text-left hover:bg-surface-dark transition-colors',
                      !notification.read && 'bg-platform-600/5'
                    )}
                  >
                    <div className={cn('mt-0.5 shrink-0', color)}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p
                          className={cn(
                            'text-sm truncate',
                            notification.read ? 'text-slate-400' : 'text-slate-200 font-medium'
                          )}
                        >
                          {notification.title}
                        </p>
                        {!notification.read && (
                          <div className="w-1.5 h-1.5 rounded-full bg-platform-500 shrink-0" />
                        )}
                      </div>
                      {notification.message && (
                        <p className="text-xs text-slate-500 mt-0.5 truncate">
                          {notification.message}
                        </p>
                      )}
                      <p className="text-xs text-slate-600 mt-1">
                        {timeAgo(notification.timestamp)}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </div>
    </>
  );
}
