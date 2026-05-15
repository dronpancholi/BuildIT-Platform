"use client";

import { create } from "zustand";

export interface ClientInfo {
  id: string;
  name: string;
  domain: string;
  niche: string;
}

interface ClientStore {
  currentClient: ClientInfo;
  setClient: (client: ClientInfo) => void;
}

export const useClientStore = create<ClientStore>((set) => ({
  currentClient: {
    id: "00000000-0000-0000-0000-000000000001",
    name: "TechStart Inc.",
    domain: "techstart.io",
    niche: "B2B SaaS",
  },
  setClient: (client) => set({ currentClient: client }),
}));

export function useClient() {
  return useClientStore((s) => s.currentClient);
}
