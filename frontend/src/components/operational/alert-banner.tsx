"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, X, Shield, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { useState, useEffect } from "react";

interface DegradationData {
  status: string;
  affected_systems: string[];
  message?: string;
}

const BANNER_CONFIG: Record<string, { bg: string; border: string; text: string; icon: string; label: string }> = {
  emergency: {
    bg: "bg-red-500/10",
    border: "border-red-500/30",
    text: "text-red-400",
    icon: "bg-red-500",
    label: "EMERGENCY",
  },
  limited: {
    bg: "bg-orange-500/10",
    border: "border-orange-500/30",
    text: "text-orange-400",
    icon: "bg-orange-500",
    label: "LIMITED",
  },
  degraded: {
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    text: "text-amber-400",
    icon: "bg-amber-500",
    label: "DEGRADED",
  },
  fully_operational: {
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/30",
    text: "text-emerald-400",
    icon: "bg-emerald-500",
    label: "FULLY OPERATIONAL",
  },
};

export function AlertBanner() {
  const [dismissed, setDismissed] = useState(false);
  const [prevStatus, setPrevStatus] = useState<string | null>(null);

  const { data: degradation } = useQuery<DegradationData>({
    queryKey: ["degradation-banner"],
    queryFn: () => fetchApi("/distributed/degradation"),
    refetchInterval: 10000,
  });

  const status = degradation?.status || "fully_operational";
  const config = BANNER_CONFIG[status] || BANNER_CONFIG.fully_operational;
  const isDegraded = status !== "fully_operational";

  useEffect(() => {
    if (status !== prevStatus) {
      setPrevStatus(status);
      if (status === "fully_operational" && prevStatus !== null) {
        const timer = setTimeout(() => setDismissed(true), 5000);
        return () => clearTimeout(timer);
      }
      if (isDegraded) {
        setDismissed(false);
      }
    }
  }, [status, prevStatus, isDegraded]);

  if (dismissed || !degradation) return null;

  return (
    <AnimatePresence>
      {isDegraded && (
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: "auto", opacity: 1 }}
          exit={{ height: 0, opacity: 0 }}
          transition={{ duration: 0.2 }}
          className={`${config.bg} border-b ${config.border} overflow-hidden`}
        >
          <div className="flex items-center justify-between px-8 py-3 max-w-6xl mx-auto">
            <div className="flex items-center gap-3">
              <span className={`w-2.5 h-2.5 rounded-full ${config.icon} animate-pulse shadow-lg`} />
              <span className={`text-xs font-mono font-bold uppercase tracking-wider ${config.text}`}>
                SYSTEM_{config.label}
              </span>
              <span className="text-xs font-mono text-slate-400">
                {degradation.affected_systems?.length > 0
                  ? `Affected: ${degradation.affected_systems.join(", ")}`
                  : "All systems operational"}
              </span>
            </div>
            <div className="flex items-center gap-3">
              {degradation.message && (
                <span className="text-xs font-mono text-slate-400 hidden md:inline">{degradation.message}</span>
              )}
              <button
                onClick={() => setDismissed(true)}
                className="p-1 hover:bg-surface-border rounded transition-colors"
              >
                <X className="w-4 h-4 text-slate-500" />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
