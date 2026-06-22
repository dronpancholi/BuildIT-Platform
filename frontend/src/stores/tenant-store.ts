import { create } from 'zustand';
import { DEFAULT_TENANT_ID } from '@/config/constants';

interface TenantState {
  currentTenantId: string;
  setTenantId: (id: string) => void;
}

export const useTenantStore = create<TenantState>((set) => ({
  currentTenantId: DEFAULT_TENANT_ID,
  setTenantId: (id) => set({ currentTenantId: id }),
}));
