'use client';
import { useEffect } from 'react';
import { useCommandPaletteStore } from '@/stores/command-palette-store';

export function KeyboardProvider({ children }: { children: React.ReactNode }) {
  const { toggle } = useCommandPaletteStore();

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [toggle]);

  return <>{children}</>;
}
