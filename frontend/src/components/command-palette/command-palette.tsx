'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Command } from 'cmdk';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  BarChart3,
  Users,
  Target,
  CalendarCheck,
  ClipboardCheck,
  FileBarChart,
  Lightbulb,
  MapPin,
  Zap,
  Settings,
  Plus,
  FileText,
  Search,
  CornerDownLeft,
} from 'lucide-react';
import { useCommandPaletteStore } from '@/stores/command-palette-store';

const NAVIGATION_ITEMS = [
  { icon: LayoutDashboard, label: 'Command Center', href: '/dashboard' },
  { icon: BarChart3, label: 'Executive', href: '/dashboard/executive' },
  { icon: Users, label: 'Customers', href: '/dashboard/campaigns' },
  { icon: Target, label: 'Keywords', href: '/dashboard/keywords' },
  { icon: CalendarCheck, label: 'Plans', href: '/dashboard/plans' },
  { icon: ClipboardCheck, label: 'Approvals', href: '/dashboard/approvals' },
  { icon: FileBarChart, label: 'Reports', href: '/dashboard/reports' },
  { icon: Lightbulb, label: 'Recommendations', href: '/dashboard/recommendations' },
  { icon: MapPin, label: 'Local SEO', href: '/dashboard/local-seo' },
  { icon: Zap, label: 'Operations', href: '/dashboard/automation' },
  { icon: Settings, label: 'Settings', href: '/dashboard/settings' },
];

const ACTION_ITEMS = [
  { icon: Plus, label: 'Create Customer', shortcut: '⌘N' },
  { icon: Plus, label: 'Create Campaign', shortcut: '⌘⇧N' },
  { icon: FileText, label: 'Generate Report', shortcut: '⌘R' },
  { icon: Search, label: 'Research Keywords', shortcut: '⌘⇧K' },
];

export function CommandPalette() {
  const router = useRouter();
  const { isOpen, open, close } = useCommandPaletteStore();
  const [search, setSearch] = useState('');

  // Global keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) {
          close();
        } else {
          open();
        }
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, open, close]);

  const handleSelect = (href: string) => {
    router.push(href);
    close();
    setSearch('');
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={close}
          />

          {/* Dialog */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -10 }}
            transition={{ duration: 0.15 }}
            className="fixed top-[20%] left-1/2 -translate-x-1/2 z-50 w-full max-w-lg"
          >
            <Command
              className="rounded-xl border border-surface-border bg-surface-card shadow-2xl shadow-black/40 overflow-hidden"
              shouldFilter={true}
            >
              <div className="flex items-center gap-3 px-4 border-b border-surface-border">
                <Search className="w-4 h-4 text-slate-400 shrink-0" />
                <Command.Input
                  value={search}
                  onValueChange={setSearch}
                  placeholder="Type a command or search..."
                  className="flex-1 h-12 bg-transparent text-sm text-slate-200 placeholder:text-slate-500 outline-none"
                />
                <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-surface-dark text-[10px] text-slate-500 font-mono shrink-0">
                  ESC
                </kbd>
              </div>

              <Command.List className="max-h-80 overflow-auto p-2">
                <Command.Empty className="py-6 text-center text-sm text-slate-500">
                  No results found.
                </Command.Empty>

                <Command.Group heading="Navigation" className="px-1">
                  {NAVIGATION_ITEMS.map((item) => (
                    <Command.Item
                      key={item.href}
                      value={item.label}
                      onSelect={() => handleSelect(item.href)}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-300 cursor-pointer data-[selected=true]:bg-platform-600/10 data-[selected=true]:text-platform-400 transition-colors"
                    >
                      <item.icon className="w-4 h-4 shrink-0" />
                      <span>{item.label}</span>
                    </Command.Item>
                  ))}
                </Command.Group>

                <Command.Separator className="my-2 h-px bg-surface-border" />

                <Command.Group heading="Actions" className="px-1">
                  {ACTION_ITEMS.map((item) => (
                    <Command.Item
                      key={item.label}
                      value={item.label}
                      onSelect={() => close()}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-300 cursor-pointer data-[selected=true]:bg-platform-600/10 data-[selected=true]:text-platform-400 transition-colors"
                    >
                      <item.icon className="w-4 h-4 shrink-0" />
                      <span className="flex-1">{item.label}</span>
                      {item.shortcut && (
                        <kbd className="text-[10px] text-slate-500 font-mono">
                          {item.shortcut}
                        </kbd>
                      )}
                    </Command.Item>
                  ))}
                </Command.Group>
              </Command.List>

              <div className="flex items-center justify-between px-4 py-2 border-t border-surface-border text-[10px] text-slate-500">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <CornerDownLeft className="w-3 h-3" /> select
                  </span>
                  <span>↑↓ navigate</span>
                </div>
                <span>esc close</span>
              </div>
            </Command>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
