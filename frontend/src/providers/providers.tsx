'use client';
import { ReactNode } from 'react';
import { QueryProvider } from './query-provider';
import { AuthProvider } from './auth-provider';
import { NotificationProvider } from './notification-provider';
import { KeyboardProvider } from './keyboard-provider';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <AuthProvider>
        <NotificationProvider>
          <KeyboardProvider>
            {children}
          </KeyboardProvider>
        </NotificationProvider>
      </AuthProvider>
    </QueryProvider>
  );
}
