"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { Activity, Cpu, Server, Database } from "lucide-react";

interface HealthComponent {
  name: string;
  status: string;
  latency_ms?: number;
}

interface HealthData {
  status: string;
  components: HealthComponent[];
}

const ICON_MAP: Record<string, React.ReactNode> = {
  postgresql: <Database className="w-4 h-4" />,
  redis: <Server className="w-4 h-4" />,
  temporal: <Activity className="w-4 h-4" />,
  kafka: <Cpu className="w-4 h-4" />,
};

const STATUS_LABELS: Record<string, string> = {
  healthy: "OK",
  degraded: "WARN",
  unhealthy: "DOWN",
  unknown: "N/A",
};

export function HealthIndicator() {
  const router = useRouter();
  const [showTooltip, setShowTooltip] = useState(false);
  const [prevStatus, setPrevStatus] = useState<string | null>(null);

  const { data } = useQuery<HealthData>({
    queryKey: ["health"],
    queryFn: () => fetchApi("/health"),
    refetchInterval: 10000,
  });

  const isHealthy = data?.status === "healthy";
  const isDegraded = data?.status === "degraded";

  const statusChanged = prevStatus !== null && prevStatus !== data?.status;
  if (data?.status && data.status !== prevStatus) {
    setPrevStatus(data.status);
  }

  const colorClass = isHealthy
    ? "bg-emerald-500 shadow-emerald-500/30"
    : isDegraded
      ? "bg-amber-500 shadow-amber-500/30"
      : "bg-red-500 shadow-red-500/30";

  return (
    <div className="relative">
      <button
        onClick={() => router.push("/dashboard/system")}
        onMouseEnter={() => setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        className="flex items-center gap-2 group cursor-pointer"
      >
        <motion.span
          key={data?.status || "unknown"}
          initial={statusChanged ? { scale: 1.5 } : false}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 300 }}
          className={`w-2.5 h-2.5 rounded-full ${colorClass} shadow-lg ${isHealthy ? "" : "animate-pulse"}`}
        />
        <span className={`text-xs font-medium tracking-wide hidden sm:inline ${
          isHealthy ? "text-emerald-400" : isDegraded ? "text-amber-400" : "text-red-400"
        }`}>
          {isHealthy ? "SYSTEM NOMINAL" : isDegraded ? "SYSTEM DEGRADED" : "SYSTEM UNHEALTHY"}
        </span>
      </button>

      <AnimatePresence>
        {showTooltip && data && (
          <motion.div
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 top-full mt-2 w-64 p-3 rounded-lg bg-surface-card border border-surface-border shadow-xl z-50"
          >
            <p className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">
              Per-Component Health
            </p>
            <div className="space-y-2">
              {data.components.map((comp) => (
                <div key={comp.name} className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">{ICON_MAP[comp.name] || <Activity className="w-4 h-4" />}</span>
                    <span className="text-slate-300 capitalize font-medium">
                      {comp.name.replace(/_/g, " ")}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {comp.latency_ms !== undefined && comp.latency_ms !== null && (
                      <span className="text-[10px] font-mono text-slate-500">{comp.latency_ms.toFixed(0)}ms</span>
                    )}
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-mono font-bold ${
                      comp.status === "healthy"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : comp.status === "degraded"
                          ? "bg-amber-500/10 text-amber-400"
                          : "bg-red-500/10 text-red-400"
                    }`}>
                      {STATUS_LABELS[comp.status] || comp.status.toUpperCase()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-3 pt-2 border-t border-surface-border">
              <p className="text-[10px] font-mono text-platform-400 text-center">
                Click to view full diagnostics
              </p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
