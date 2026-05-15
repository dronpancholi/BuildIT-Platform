"use client";

import { useRealtime } from "@/hooks/use-realtime";

export function SSEProvider({ children }: { children: React.ReactNode }) {
  useRealtime();
  return <>{children}</>;
}
