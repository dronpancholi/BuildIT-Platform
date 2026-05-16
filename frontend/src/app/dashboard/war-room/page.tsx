"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  Radio, AlertTriangle, Activity, Cpu, Gauge, Shield,
  Server, Database, Network, Loader2, Zap, Clock, BrainCircuit,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { useMemo } from "react";
import { useRealtime, useRealtimeStore } from "@/hooks/use-realtime";

interface InfraTopology {
  nodes: { id: string; name: string; type: string; status: string }[];
  edges: { source: string; target: string; latency_ms: number; dependency_health: string }[];
}

interface QueuePressureEntry {
  queue_name: string;
  depth: number;
  pressure_score: number;
  level: string;
}

interface WorkerSaturationEntry {
  worker_id: string;
  task_queue: string;
  active_tasks: number;
  max_concurrent: number;
  saturation_pct: number;
}

interface PressureTelemetry {
  overall_pressure: number;
  level: string;
  queue_pressures: { queue: string; score: number }[];
}

interface SaturationAlert {
  type: string;
  severity: string;
  component: string;
  message: string;
  timestamp: string;
}

interface EventThroughput {
  time_window_minutes: number;
  events_per_second: number;
  events_per_minute: number;
  events_per_topic: Record<string, number>;
  average_event_size_bytes: number;
  peak_throughput: number;
}

interface PredictiveAlert {
  id: string;
  type: string;
  severity: string;
  component: string;
  message: string;
  probability: number;
  predicted_at: string;
}

interface PredictiveDashboard {
  predicted_anomalies: PredictiveAlert[];
}

interface OperationalPressureEntry {
  component: string;
  pressure_score: number;
  level: string;
}

interface WorkerImbalanceEntry {
  worker_a: string;
  worker_b: string;
  imbalance_score: number;
  affected_queue: string;
}

interface CrossSystemAwareness {
  system_states: { system: string; status: string; load: number }[];
  critical_path: { step: string; system: string; risk: string }[];
}

const LEVEL_COLORS: Record<string, string> = {
  critical: "text-red-400 bg-red-500/10 border-red-500/20",
  high: "text-orange-400 bg-orange-500/10 border-orange-500/20",
  moderate: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  low: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
  none: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
};

const STATUS_DOT: Record<string, string> = {
  healthy: "bg-emerald-500",
  degraded: "bg-amber-500",
  unhealthy: "bg-red-500",
  unknown: "bg-slate-500",
};

export default function WarRoomPage() {
  useRealtime();

  const isConnected = useRealtimeStore((state) => state.isConnected);
  const sseQueues = useRealtimeStore((state) => state.queues);
  const sseWorkers = useRealtimeStore((state) => state.workers);
  const sseInfra = useRealtimeStore((state) => state.infrastructure);

  const { data: topology, isLoading: loadingTopology } = useQuery<InfraTopology>({
    queryKey: ["sre-topology"],
    queryFn: () => fetchApi("/sre/topology"),
    refetchInterval: 10000,
  });

  const { data: queuePressure } = useQuery<{ entries: QueuePressureEntry[] }>({
    queryKey: ["sre-queue-pressure"],
    queryFn: () => fetchApi("/sre/queue-pressure"),
    refetchInterval: 10000,
  });

  const { data: workerSaturation, isLoading: loadingWorkers } = useQuery<{ entries: WorkerSaturationEntry[] }>({
    queryKey: ["sre-worker-saturation"],
    queryFn: () => fetchApi("/sre/worker-saturation"),
    refetchInterval: 10000,
  });

  const { data: pressure } = useQuery<PressureTelemetry>({
    queryKey: ["overload-pressure"],
    queryFn: () => fetchApi("/overload/pressure"),
    refetchInterval: 10000,
  });

  const { data: alerts } = useQuery<SaturationAlert[]>({
    queryKey: ["overload-saturation-alerts"],
    queryFn: () => fetchApi("/overload/saturation-alerts"),
    refetchInterval: 10000,
  });

  const { data: throughput } = useQuery<EventThroughput>({
    queryKey: ["event-throughput"],
    queryFn: () => fetchApi("/event-infrastructure/throughput"),
    refetchInterval: 10000,
  });

  const { data: anomalyDashboard } = useQuery<PredictiveDashboard>({
    queryKey: ["anomaly-prediction"],
    queryFn: () => fetchApi("/anomaly-prediction/dashboard"),
    refetchInterval: 10000,
  });

  const { data: pressureData } = useQuery<OperationalPressureEntry[]>({
    queryKey: ["operational-pressure"],
    queryFn: () => fetchApi("/infra-self-analysis/pressure"),
    refetchInterval: 10000,
  });

  const { data: imbalanceData } = useQuery<WorkerImbalanceEntry[]>({
    queryKey: ["worker-imbalance"],
    queryFn: () => fetchApi("/infra-self-analysis/worker-imbalance"),
    refetchInterval: 10000,
  });

  const { data: crossSystemData } = useQuery<CrossSystemAwareness>({
    queryKey: ["cross-system-awareness"],
    queryFn: () => fetchApi("/orchestration-intelligence/cross-system-awareness"),
    refetchInterval: 10000,
  });

  const pressureEntries = useMemo(() => {
    const base = queuePressure?.entries || [];
    if (!sseQueues || Object.keys(sseQueues).length === 0) return base;
    return base.map((q) => ({
      ...q,
      depth: sseQueues[q.queue_name] !== undefined ? sseQueues[q.queue_name] : q.depth,
    }));
  }, [queuePressure, sseQueues]);

  const workerEntries = useMemo(() => {
    const base = workerSaturation?.entries || workerSaturation as unknown as WorkerSaturationEntry[];
    if (!sseWorkers || sseWorkers.length === 0) return base;
    return base.map((w) => ({
      ...w,
      active_tasks: sseWorkers.find((sw) => sw.task_queue === w.task_queue)?.worker_id ? w.active_tasks + 1 : w.active_tasks,
      saturation_pct: sseWorkers.find((sw) => sw.task_queue === w.task_queue)
        ? Math.min(w.saturation_pct + 5, 100)
        : w.saturation_pct,
    }));
  }, [workerSaturation, sseWorkers]);

  const alertList = alerts || [];

  const nodes = useMemo(() => {
    const base = topology?.nodes || [];
    if (!sseInfra || Object.keys(sseInfra).length === 0) return base;
    return base.map((n) => ({
      ...n,
      status: sseInfra[n.id] || sseInfra[n.name.toLowerCase()] || n.status,
    }));
  }, [topology, sseInfra]);

  const edges = topology?.edges || [];

  const criticalAlerts = alertList.filter(a => a.severity === "critical").length;
  const highAlerts = alertList.filter(a => a.severity === "high").length;

  const healthyNodes = nodes.filter(n => n.status === "healthy").length;
  const totalNodes = nodes.length;

  const avgSaturation = useMemo(() => {
    if (!workerEntries || workerEntries.length === 0) return 0;
    return workerEntries.reduce((s, w) => s + (w.saturation_pct || 0), 0) / workerEntries.length;
  }, [workerEntries]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">WAR_ROOM</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Enterprise Operational Command</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-md bg-red-500/5 border border-red-500/20 text-xs font-mono text-red-400 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            {criticalAlerts > 0 ? `${criticalAlerts} CRITICAL` : "NOMINAL"}
          </div>
          <div className={`px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 ${
            isConnected
              ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-400"
              : "bg-amber-500/10 border-amber-500/20 text-amber-400"
          }`}>
            <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`} />
            <Radio className="w-3.5 h-3.5" />
            {isConnected ? "LIVE (SSE)" : "POLLING"}
          </div>
        </div>
      </div>

      {loadingTopology && pressureEntries.length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : (
        <>
          {/* KPI Row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="glass-panel p-5">
              <div className="flex items-center gap-2 mb-2">
                <Server className="w-4 h-4 text-platform-400" />
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Infra Health</span>
              </div>
              <span className="text-2xl font-bold font-mono text-slate-100">{healthyNodes}/{totalNodes}</span>
              <p className="text-[10px] font-mono text-slate-600 mt-1">Components healthy</p>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="glass-panel p-5">
              <div className="flex items-center gap-2 mb-2">
                <Gauge className="w-4 h-4 text-amber-400" />
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Pressure</span>
              </div>
              <span className={`text-2xl font-bold font-mono ${pressure?.overall_pressure && pressure.overall_pressure > 70 ? "text-red-400" : "text-slate-100"}`}>
                {pressure ? `${Math.round(pressure.overall_pressure)}%` : "—"}
              </span>
              <p className="text-[10px] font-mono text-slate-600 mt-1 capitalize">{pressure?.level || "unknown"}</p>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-panel p-5">
              <div className="flex items-center gap-2 mb-2">
                <Cpu className="w-4 h-4 text-emerald-400" />
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Worker Sat.</span>
              </div>
              <span className={`text-2xl font-bold font-mono ${avgSaturation > 80 ? "text-red-400" : avgSaturation > 50 ? "text-amber-400" : "text-slate-100"}`}>
                {avgSaturation > 0 ? `${Math.round(avgSaturation)}%` : "—"}
              </span>
              <p className="text-[10px] font-mono text-slate-600 mt-1">Average saturation</p>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="glass-panel p-5">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-4 h-4 text-indigo-400" />
                <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">Throughput</span>
              </div>
              <span className="text-2xl font-bold font-mono text-slate-100">
                {throughput ? `${throughput.events_per_second.toFixed(1)}/s` : "—"}
              </span>
              <p className="text-[10px] font-mono text-slate-600 mt-1">Event rate</p>
            </motion.div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Topology Overview */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Network className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">TOPOLOGY_OVERVIEW</h3>
              </div>
              <div className="space-y-2">
                {nodes.length === 0 ? (
                  <div className="text-sm text-slate-500 font-mono py-8 text-center">No topology data</div>
                ) : (
                  nodes.map((node, i) => (
                    <motion.div
                      key={node.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="flex items-center justify-between p-2.5 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${STATUS_DOT[node.status] || STATUS_DOT.unknown} ${node.status === "healthy" ? "" : "animate-pulse"}`} />
                        <span className="text-xs font-mono text-slate-300">{node.name}</span>
                      </div>
                      <span className="text-[10px] font-mono text-slate-500 uppercase">{node.status}</span>
                    </motion.div>
                  ))
                )}
              </div>
              {edges.length > 0 && (
                <div className="mt-4 pt-4 border-t border-surface-border">
                  <p className="text-[10px] font-mono text-slate-600">{edges.length} connections monitored</p>
                </div>
              )}
            </div>

            {/* Queue Pressure */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Gauge className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">QUEUE_PRESSURE</h3>
              </div>
              <div className="space-y-3">
                {pressureEntries.length === 0 ? (
                  <div className="text-sm text-slate-500 font-mono py-8 text-center">No queue pressure data</div>
                ) : (
                  pressureEntries.map((q, i) => {
                    const pct = Math.min(q.pressure_score || q.depth * 5, 100);
                    const barColor = pct > 80 ? "bg-red-500" : pct > 50 ? "bg-amber-500" : "bg-emerald-500";
                    return (
                      <motion.div
                        key={q.queue_name}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-mono text-slate-300 uppercase">{q.queue_name.replace(/_/g, " ")}</span>
                          <span className={`text-[10px] font-mono ${pct > 50 ? "text-amber-400" : "text-slate-500"}`}>{Math.round(pct)}%</span>
                        </div>
                        <div className="w-full h-2.5 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${pct}%` }}
                            className={`h-full rounded-full ${barColor}`}
                            transition={{ duration: 0.5, delay: i * 0.05 }}
                          />
                        </div>
                        <div className="flex justify-between text-[10px] font-mono text-slate-600 mt-0.5">
                          <span>Depth: {q.depth}</span>
                          <span className="capitalize">{q.level}</span>
                        </div>
                      </motion.div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Worker Saturation */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Cpu className="w-5 h-5 text-emerald-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">WORKER_SATURATION</h3>
              </div>
              <div className="space-y-3">
                {!workerEntries || workerEntries.length === 0 ? (
                  <div className="text-sm text-slate-500 font-mono py-8 text-center">No worker saturation data</div>
                ) : (
                  workerEntries.slice(0, 8).map((w, i) => {
                    const pct = w.saturation_pct || 0;
                    const barColor = pct > 80 ? "bg-red-500" : pct > 50 ? "bg-amber-500" : "bg-emerald-500";
                    return (
                      <motion.div
                        key={w.worker_id || i}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03 }}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-mono text-slate-300 truncate max-w-[140px]">
                            {(w.task_queue || w.worker_id || "").slice(0, 20)}
                          </span>
                          <span className={`text-[10px] font-mono ${pct > 50 ? "text-amber-400" : "text-slate-500"}`}>{Math.round(pct)}%</span>
                        </div>
                        <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${pct}%` }}
                            className={`h-full rounded-full ${barColor}`}
                            transition={{ duration: 0.5 }}
                          />
                        </div>
                      </motion.div>
                    );
                  })
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Pressure Telemetry */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">PRESSURE_TELEMETRY</h3>
              </div>
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="flex-1">
                    <div className="flex justify-between text-xs font-mono text-slate-400 mb-1">
                      <span>System Pressure</span>
                      <span>{pressure ? `${Math.round(pressure.overall_pressure)}%` : "—"}</span>
                    </div>
                    <div className="w-full h-4 bg-surface-darker rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pressure?.overall_pressure || 0}%` }}
                        className={`h-full rounded-full ${(pressure?.overall_pressure || 0) > 70 ? "bg-red-500" : (pressure?.overall_pressure || 0) > 40 ? "bg-amber-500" : "bg-emerald-500"}`}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                  </div>
                  <span className={`px-3 py-1.5 rounded text-xs font-mono font-bold border ${LEVEL_COLORS[pressure?.level || "none"] || LEVEL_COLORS.none}`}>
                    {(pressure?.level || "none").toUpperCase()}
                  </span>
                </div>
                {(pressure?.queue_pressures || []).map((qp, i) => (
                  <div key={qp.queue} className="flex items-center gap-3">
                    <span className="text-xs font-mono text-slate-400 w-32 truncate uppercase">{qp.queue.replace(/_/g, " ")}</span>
                    <div className="flex-1 h-2 bg-surface-darker rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${qp.score}%` }}
                        className={`h-full rounded-full ${qp.score > 70 ? "bg-red-500" : qp.score > 40 ? "bg-amber-500" : "bg-emerald-500"}`}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 w-10 text-right">{Math.round(qp.score)}%</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Active Alerts */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">ACTIVE_ALERTS</h3>
                {criticalAlerts > 0 && (
                  <span className="ml-auto px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-xs font-mono text-red-400">
                    {criticalAlerts} CRITICAL
                  </span>
                )}
              </div>
              <div className="space-y-2 max-h-[300px] overflow-auto custom-scrollbar">
                {alertList.length === 0 ? (
                  <div className="text-sm text-slate-500 font-mono py-8 text-center flex flex-col items-center">
                    <Shield className="w-8 h-8 text-emerald-500 mb-2" />
                    <span>ALL_SYSTEMS_NOMINAL</span>
                  </div>
                ) : (
                  alertList.map((a, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -5 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className={`p-3 rounded-md border font-mono text-xs ${
                        a.severity === "critical"
                          ? "bg-red-500/5 border-red-500/20"
                          : a.severity === "high"
                            ? "bg-orange-500/5 border-orange-500/20"
                            : "bg-amber-500/5 border-amber-500/20"
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full mt-1 flex-shrink-0 ${
                          a.severity === "critical" ? "bg-red-500 animate-pulse" : a.severity === "high" ? "bg-orange-500" : "bg-amber-500"
                        }`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${
                              a.severity === "critical" ? "bg-red-500/10 text-red-400" : a.severity === "high" ? "bg-orange-500/10 text-orange-400" : "bg-amber-500/10 text-amber-400"
                            }`}>&gt;_{a.severity}</span>
                            <span className="text-[9px] text-slate-600">{a.component}</span>
                          </div>
                          <p className="text-slate-300 mt-0.5">{a.message}</p>
                          <p className="text-[9px] text-slate-600 mt-1">
                            {new Date(a.timestamp).toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Infra Health */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Server className="w-5 h-5 text-emerald-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">INFRA_HEALTH</h3>
              </div>
              <div className="grid grid-cols-2 gap-3">
                {["postgresql", "redis", "temporal", "kafka", "qdrant", "minio", "nim", "playwright"].map((svc) => {
                  const node = nodes.find(n => n.id === svc || n.name === svc);
                  const sseStatus = sseInfra[svc];
                  const status = sseStatus || node?.status || "unknown";
                  return (
                    <div key={svc} className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono text-slate-400 uppercase">{svc}</span>
                        <span className={`w-2 h-2 rounded-full ${STATUS_DOT[status]}`} />
                      </div>
                      <span className="text-[10px] font-mono text-slate-500 uppercase">{status}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* AI Status */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <BrainCircuit className="w-5 h-5 text-purple-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">AI_STATUS</h3>
              </div>
              <div className="space-y-3">
                <div className="flex items-center justify-between p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <span className="text-xs font-mono text-slate-400">NIM Gateway</span>
                  <span className={`flex items-center gap-1.5 text-xs font-mono ${sseInfra["nim"] === "healthy" || !sseInfra["nim"] ? "text-emerald-400" : "text-red-400"}`}>
                    <span className={`w-2 h-2 rounded-full ${sseInfra["nim"] === "healthy" || !sseInfra["nim"] ? "bg-emerald-500" : "bg-red-500 animate-pulse"}`} />
                    {(sseInfra["nim"] || "HEALTHY").toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <span className="text-xs font-mono text-slate-400">Circuit Breaker</span>
                  <span className={`text-xs font-mono ${sseInfra["circuit_breaker"] === "open" ? "text-red-400" : "text-emerald-400"}`}>
                    {(sseInfra["circuit_breaker"] || "CLOSED").toUpperCase()}
                  </span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <span className="text-xs font-mono text-slate-400">Inference Rate</span>
                  <span className="text-xs font-mono text-slate-300">{sseInfra["inference_rate"] || "—"}/min</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <span className="text-xs font-mono text-slate-400">Model</span>
                  <span className="text-xs font-mono text-slate-300">{sseInfra["model"] || "llama-3-70b"}</span>
                </div>
              </div>
            </div>

            {/* Event Throughput */}
            <div className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-indigo-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">EVENT_THROUGHPUT</h3>
              </div>
              <div className="flex items-center justify-center py-4">
                <div className="text-center">
                  <span className="text-4xl font-bold font-mono text-slate-100">
                    {throughput ? throughput.events_per_second.toFixed(1) : "—"}
                  </span>
                  <p className="text-xs font-mono text-slate-500 mt-1">events/sec</p>
                </div>
              </div>
              {throughput?.events_per_topic && Object.keys(throughput.events_per_topic).length > 0 && (
                <div className="mt-4 pt-4 border-t border-surface-border space-y-2">
                  {Object.entries(throughput.events_per_topic).map(([topic, rate]) => (
                    <div key={topic} className="flex items-center justify-between text-xs font-mono">
                      <span className="text-slate-400 truncate max-w-[200px]">{topic}</span>
                      <span className="text-slate-500">{rate.toFixed(1)}/s</span>
                    </div>
                  ))}
                </div>
              )}
              {throughput?.peak_throughput ? (
                <div className="mt-4 pt-4 border-t border-surface-border flex items-center justify-between text-[10px] font-mono text-slate-600">
                  <span>PEAK</span>
                  <span>{throughput.peak_throughput.toFixed(1)}/s</span>
                </div>
              ) : null}
            </div>
          </div>

          {/* Anomaly Prediction Panel */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-panel p-6"
          >
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              <h3 className="text-lg font-medium text-slate-200 font-mono">ANOMALY_PREDICTION</h3>
              {anomalyDashboard && anomalyDashboard.predicted_anomalies.filter(a => a.severity === "critical").length > 0 && (
                <span className="ml-auto px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-xs font-mono text-red-400">
                  {anomalyDashboard.predicted_anomalies.filter(a => a.severity === "critical").length} CRITICAL
                </span>
              )}
            </div>
            {!anomalyDashboard ? (
              <div className="text-sm text-slate-500 font-mono py-8 text-center">Loading predictions...</div>
            ) : anomalyDashboard.predicted_anomalies.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8">
                <Shield className="w-8 h-8 text-emerald-500 mb-2" />
                <span className="text-sm font-mono text-slate-500">NO_PREDICTED_ANOMALIES</span>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {anomalyDashboard.predicted_anomalies.map((a, i) => (
                  <motion.div
                    key={a.id || i}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-bold ${
                        a.severity === "critical" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                        a.severity === "high" ? "bg-orange-500/10 text-orange-400 border-orange-500/20" :
                        "bg-amber-500/10 text-amber-400 border-amber-500/20"
                      }`}>{a.severity.toUpperCase()}</span>
                      <span className="text-[10px] font-mono text-slate-500 uppercase">{a.component}</span>
                    </div>
                    <div className="text-xs font-mono text-slate-300 mb-1">{a.type}</div>
                    <p className="text-[10px] font-mono text-slate-400 mb-2">{a.message}</p>
                    <div className="flex items-center justify-between text-[10px] font-mono mb-1">
                      <span className="text-slate-500">Probability</span>
                      <span className={`font-bold ${
                        a.probability >= 0.7 ? "text-emerald-400" : a.probability >= 0.4 ? "text-amber-400" : "text-red-400"
                      }`}>{Math.round(a.probability * 100)}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${a.probability * 100}%` }}
                        className={`h-full rounded-full ${
                          a.probability >= 0.7 ? "bg-emerald-500" : a.probability >= 0.4 ? "bg-amber-500" : "bg-red-500"
                        }`}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </motion.div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Operational Pressure Analysis */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className="glass-panel p-6"
            >
              <div className="flex items-center gap-2 mb-4">
                <Gauge className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">PRESSURE_ANALYSIS</h3>
              </div>
              {!pressureData ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">Loading pressure data...</div>
              ) : pressureData.length === 0 ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No pressure data</div>
              ) : (
                <div className="space-y-3">
                  {pressureData.map((p, i) => (
                    <div key={p.component || i}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-slate-300 uppercase">{p.component}</span>
                        <span className={`text-[10px] font-mono ${p.pressure_score > 70 ? "text-red-400" : p.pressure_score > 40 ? "text-amber-400" : "text-slate-500"}`}>
                          {Math.round(p.pressure_score)}%
                        </span>
                      </div>
                      <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${p.pressure_score}%` }}
                          className={`h-full rounded-full ${p.pressure_score > 70 ? "bg-red-500" : p.pressure_score > 40 ? "bg-amber-500" : "bg-emerald-500"}`}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                      <div className="text-[10px] font-mono text-slate-600 mt-0.5 capitalize">{p.level}</div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Worker Imbalance */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="glass-panel p-6"
            >
              <div className="flex items-center gap-2 mb-4">
                <Activity className="w-5 h-5 text-red-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">WORKER_IMBALANCE</h3>
              </div>
              {!imbalanceData ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">Loading imbalance data...</div>
              ) : imbalanceData.length === 0 ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No imbalance detected</div>
              ) : (
                <div className="space-y-3">
                  {imbalanceData.map((im, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-slate-300">{im.worker_a} ↔ {im.worker_b}</span>
                        <span className={`text-[10px] font-mono font-bold ${im.imbalance_score > 50 ? "text-red-400" : im.imbalance_score > 25 ? "text-amber-400" : "text-slate-500"}`}>
                          {Math.round(im.imbalance_score)}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${im.imbalance_score}%` }}
                          className={`h-full rounded-full ${im.imbalance_score > 50 ? "bg-red-500" : im.imbalance_score > 25 ? "bg-amber-500" : "bg-emerald-500"}`}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                      <div className="text-[10px] font-mono text-slate-600 mt-1">{im.affected_queue}</div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Cross-System Awareness */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="glass-panel p-6"
            >
              <div className="flex items-center gap-2 mb-4">
                <Network className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">CROSS_SYSTEM_AWARENESS</h3>
              </div>
              {!crossSystemData ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">Loading cross-system data...</div>
              ) : (
                <div className="space-y-4">
                  {crossSystemData.system_states && crossSystemData.system_states.length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">System States</p>
                      <div className="space-y-2">
                        {crossSystemData.system_states.map((s, i) => (
                          <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/30 border border-surface-border/30">
                            <div className="flex items-center gap-2">
                              <span className={`w-2 h-2 rounded-full ${s.status === "healthy" ? "bg-emerald-500" : s.status === "degraded" ? "bg-amber-500" : "bg-red-500"}`} />
                              <span className="text-xs font-mono text-slate-300">{s.system}</span>
                            </div>
                            <span className="text-[10px] font-mono text-slate-500">{Math.round(s.load)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {crossSystemData.critical_path && crossSystemData.critical_path.length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-red-400 uppercase mb-2">Critical Path</p>
                      <div className="space-y-1">
                        {crossSystemData.critical_path.map((c, i) => (
                          <div key={i} className="flex items-center gap-2 text-xs font-mono">
                            <span className={`w-1.5 h-1.5 rounded-full ${c.risk === "high" ? "bg-red-500" : c.risk === "medium" ? "bg-amber-500" : "bg-emerald-500"}`} />
                            <span className="text-slate-300">{c.step}</span>
                            <span className="text-slate-500">→ {c.system}</span>
                            <span className={`text-[10px] ml-auto ${c.risk === "high" ? "text-red-400" : c.risk === "medium" ? "text-amber-400" : "text-emerald-400"}`}>{c.risk.toUpperCase()}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          </div>
        </>
      )}
    </div>
  );
}
