'use client';
import { Toaster } from 'sonner';

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Toaster
        position="top-right"
        richColors
        closeButton
        theme="dark"
        toastOptions={{
          style: {
            background: '#16181d',
            border: '1px solid #23262e',
            color: '#e2e8f0',
          },
        }}
      />
    </>
  );
}
