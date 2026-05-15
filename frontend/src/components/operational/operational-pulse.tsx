"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { useRealtimeStore } from "@/hooks/use-realtime";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import {
  Activity, GitBranch, Radio, Users, BarChart3, Zap,
  Loader2,
} from "lucide-react";

export function OperationalPulse() {
  const workflows = useRealtimeStore((s) => s.workflows);
  const queues = useRealtimeStore((s) => s.queues);
  const workers = useRealtimeStore((s) => s.workers);
  const isConnected = useRealtimeStore((s) => s.isConnected);

  const { data: overview } = useQuery({
    queryKey: ["bi-overview"],
    queryFn: () => fetchApi<any>("/business-intelligence/intelligence/overview"),
    refetchInterval: 30000,
  });

  const activeWorkflows = useMemo(() =>
    workflows.filter((w) => w.status === "running" || w.status === "active" || w.status === "started"),
    [workflows],
  );

  const totalQueueDepth = useMemo(() =>
    Object.values(queues).reduce((sum, d) => sum + (d as number), 0),
    [queues],
  );

  const activeWorkers = useMemo(() =>
    workers.filter((w) => w.status === "active"),
    [workers],
  );

  const intel = overview?.intelligence;
  const campaigns = overview?.campaigns;

  const items = [
    {
      label: "WORKFLOWS",
      value: activeWorkflows.length,
      icon: <Radio className="w-3.5 h-3.5" />,
      color: activeWorkflows.length > 0 ? "text-emerald-400" : "text-slate-500",
      pulse: activeWorkflows.length > 0,
    },
    {
      label: "QUEUE DEPTH",
      value: totalQueueDepth,
      icon: <BarChart3 className="w-3.5 h-3.5" />,
      color: totalQueueDepth > 0 ? "text-amber-400" : "text-slate-500",
      pulse: totalQueueDepth > 0,
    },
    {
      label: "WORKERS",
      value: activeWorkers.length,
      icon: <Users className="w-3.5 h-3.5" />,
      color: activeWorkers.length > 0 ? "text-platform-400" : "text-slate-500",
      pulse: activeWorkers.length > 0,
    },
    {
      label: "CAMPAIGNS",
      value: campaigns?.active ?? "—",
      icon: <GitBranch className="w-3.5 h-3.5" />,
      color: (campaigns?.active ?? 0) > 0 ? "text-indigo-400" : "text-slate-500",
      pulse: (campaigns?.active ?? 0) > 0,
    },
    {
      label: "EVENTS/24H",
      value: intel?.events_24h ?? "—",
      icon: <Activity className="w-3.5 h-3.5" />,
      color: (intel?.events_24h ?? 0) > 0 ? "text-purple-400" : "text-slate-500",
      pulse: (intel?.events_24h ?? 0) > 0,
    },
    {
      label: "ACTIONS",
      value: intel?.pending_actions ?? "—",
      icon: <Zap className="w-3.5 h-3.5" />,
      color: (intel?.pending_actions ?? 0) > 0 ? "text-rose-400" : "text-slate-500",
      pulse: (intel?.pending_actions ?? 0) > 0,
    },
  ];

  return (
    <div className="flex items-center gap-4">
      <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full border text-[10px] font-mono ${
        isConnected
          ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
          : "bg-red-500/10 border-red-500/20 text-red-400"
      }`}>
        <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-emerald-500 animate-pulse" : "bg-red-500"}`} />
        {isConnected ? "LIVE" : "OFF"}
      </div>
      <div className="flex items-center gap-3">
        {items.map((item) => (
          <motion.div
            key={item.label}
            animate={item.pulse ? { opacity: [0.7, 1, 0.7] } : {}}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-md bg-surface-darker/50 border border-surface-border/50 ${item.color}`}
          >
            {item.icon}
            <span className="text-[10px] font-mono font-bold">{item.value}</span>
            <span className="text-[8px] font-mono text-slate-600 uppercase tracking-wider hidden lg:inline">{item.label}</span>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
