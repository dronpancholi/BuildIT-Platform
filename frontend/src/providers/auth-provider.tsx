'use client';
import { createContext, useContext, ReactNode } from 'react';
import { useAuth } from '@/hooks/use-auth';

interface AuthContextValue {
  isLoading: boolean;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue>({ isLoading: true, isAuthenticated: false });

export function AuthProvider({ children }: { children: ReactNode }) {
  const { isLoading, isAuthenticated } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-surface-darker">
        <div className="flex flex-col items-center gap-4">
          <div className="w-8 h-8 border-2 border-platform-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-sm text-slate-500 font-mono">Authenticating...</p>
        </div>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ isLoading, isAuthenticated }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuthContext = () => useContext(AuthContext);
