'use client';
import { useEffect } from 'react';
import { useAuthStore } from '@/stores/auth-store';

export function useAuth() {
  const store = useAuthStore();

  useEffect(() => {
    if (store.isLoading && !store.isAuthenticated) {
      store.login();
    }
  }, []);

  return {
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    login: store.login,
    logout: store.logout,
    hasPermission: store.hasPermission,
    hasRole: store.hasRole,
    hasMinimumRole: store.hasMinimumRole,
  };
}
