"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Database, Cpu, Network, HardDrive, Loader2, Server,
  Activity, Users, Clock, Layers,
  Radio, BarChart3, GitBranch,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { HealthResponse } from "@/types/api";
import { useRealtimeStore } from "@/hooks/use-realtime";
import { WorkflowVisualization } from "@/components/operational/workflow-visualization";

const INFRA_ICONS: Record<string, React.ReactNode> = {
  postgresql: <Database className="w-5 h-5 text-blue-400" />,
  redis: <Database className="w-5 h-5 text-red-400" />,
  temporal: <Server className="w-5 h-5 text-indigo-400" />,
  kafka: <Network className="w-5 h-5 text-amber-400" />,
  qdrant: <Database className="w-5 h-5 text-purple-400" />,
  minio: <HardDrive className="w-5 h-5 text-sky-400" />,
  nim: <Cpu className="w-5 h-5 text-emerald-400" />,
  playwright: <Activity className="w-5 h-5 text-rose-400" />,
};

export default function SystemPage() {
  const [selectedTab, setSelectedTab] = useState<"infra" | "queues" | "workflows">("infra");
  const queues = useRealtimeStore((s) => s.queues);
  const workers = useRealtimeStore((s) => s.workers);
  const infrastructure = useRealtimeStore((s) => s.infrastructure);
  const isConnected = useRealtimeStore((s) => s.isConnected);
  const lastHeartbeat = useRealtimeStore((s) => s.lastHeartbeat);
  const workflows = useRealtimeStore((s) => s.workflows);

  const { data: healthData, isLoading } = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: () => fetchApi("/health"),
    refetchInterval: 5000,
  });

  const { data: queueTelemetry } = useQuery<any>({
    queryKey: ["queue-telemetry"],
    queryFn: () => fetchApi("/queue-telemetry/queue-telemetry"),
    refetchInterval: 3000,
  });

  const { data: kafkaTelemetry } = useQuery<any>({
    queryKey: ["kafka-telemetry"],
    queryFn: () => fetchApi("/queue-telemetry/kafka-telemetry"),
    refetchInterval: 5000,
  });

  const { data: workerTelemetry } = useQuery<any>({
    queryKey: ["worker-telemetry"],
    queryFn: () => fetchApi("/queue-telemetry/worker-telemetry"),
    refetchInterval: 3000,
  });

  const infraServices = [
    { name: "PostgreSQL 16", key: "postgresql" },
    { name: "Redis Cluster", key: "redis" },
    { name: "Temporal Server", key: "temporal" },
    { name: "Kafka Broker", key: "kafka" },
    { name: "Qdrant Vector DB", key: "qdrant" },
    { name: "MinIO Object Store", key: "minio" },
    { name: "NVIDIA NIM", key: "nim" },
    { name: "Playwright", key: "playwright" },
  ];

  const getStatus = (key: string) => {
    const comp = healthData?.components.find((c) => c.name === key);
    return comp?.status || infrastructure[key] || "unknown";
  };

  const getLatency = (key: string) => {
    return healthData?.components.find((c) => c.name === key)?.latency_ms;
  };

  const activeWorkers = workers.filter((w) => w.status === "active");
  const statusCounts = {
    healthy: healthData?.components.filter((c) => c.status === "healthy").length ?? 0,
    degraded: healthData?.components.filter((c) => c.status === "degraded").length ?? 0,
    unhealthy: healthData?.components.filter((c) => c.status === "unhealthy").length ?? 0,
    total: healthData?.components.length ?? 0,
  };

  const queueEntries = Object.entries(queues);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">INFRA_COMMAND</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Live Infrastructure Command Center</p>
        </div>
        <div className="flex items-center gap-3">
          <div className={`px-3 py-1.5 rounded-md flex items-center gap-2 border text-[10px] font-mono ${
            isConnected
              ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
              : "bg-red-500/10 border-red-500/30 text-red-400"
          }`}>
            <span className={`w-2 h-2 rounded-full ${isConnected ? "bg-emerald-500 animate-pulse" : "bg-red-500"}`} />
            {isConnected ? "SSE LIVE" : "SSE OFF"}
          </div>
          {lastHeartbeat && (
            <span className="text-[10px] text-slate-600 font-mono">
              pulse: {new Date(lastHeartbeat).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {/* Status Summary Bar */}
      <motion.div
        initial={{ opacity: 0, y: -5 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-panel p-4 flex items-center gap-6 overflow-x-auto"
      >
        <div className="flex items-center gap-2 flex-shrink-0">
          <ShieldStatus
            label="Healthy"
            count={statusCounts.healthy}
            total={statusCounts.total}
            color="emerald"
          />
          <ShieldStatus
            label="Degraded"
            count={statusCounts.degraded}
            total={statusCounts.total}
            color="amber"
          />
          <ShieldStatus
            label="Unhealthy"
            count={statusCounts.unhealthy}
            total={statusCounts.total}
            color="red"
          />
        </div>
        <div className="w-px h-8 bg-surface-border" />
        <div className="flex items-center gap-3 text-[10px] font-mono">
          <span className="text-slate-500 flex items-center gap-1">
            <Users className="w-3 h-3" />
            Workers: <span className="text-emerald-400">{activeWorkers.length}</span>
          </span>
          <span className="text-slate-500 flex items-center gap-1">
            <GitBranch className="w-3 h-3" />
            Workflows: <span className="text-platform-400">{workflows.length}</span>
          </span>
          <span className="text-slate-500 flex items-center gap-1">
            <BarChart3 className="w-3 h-3" />
            Queues: <span className="text-amber-400">{queueEntries.length}</span>
          </span>
        </div>
      </motion.div>

      {/* Tab Selector */}
      <div className="flex items-center gap-1 bg-surface-darker rounded-lg border border-surface-border p-0.5 w-fit">
        {(["infra", "queues", "workflows"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setSelectedTab(tab)}
            className={`px-4 py-1.5 text-[11px] font-mono rounded-md transition-all uppercase tracking-wider ${
              selectedTab === tab
                ? "bg-platform-500/10 text-platform-400 border border-platform-500/20"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {selectedTab === "infra" && (
        <>
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {infraServices.map((svc, i) => {
                const status = getStatus(svc.key);
                const latency = getLatency(svc.key);
                const isHealthy = status === "healthy";
                const isDegraded = status === "degraded";
                return (
                  <motion.div
                    key={svc.key}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className={`glass-panel p-4 border-l-2 ${
                      isHealthy ? "border-l-emerald-500" :
                      isDegraded ? "border-l-amber-500" :
                      "border-l-red-500"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      {INFRA_ICONS[svc.key] || <Server className="w-5 h-5 text-slate-400" />}
                      <span className={`px-2 py-0.5 text-[9px] font-mono font-bold rounded border flex items-center gap-1 ${
                        isHealthy ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                        isDegraded ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                        status === "unhealthy" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                        "bg-slate-500/10 text-slate-400 border-slate-500/20"
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          isHealthy ? "bg-emerald-500" :
                          isDegraded ? "bg-amber-500" :
                          "bg-red-500"
                        } ${!isHealthy ? "animate-pulse" : ""}`} />
                        {status}
                      </span>
                    </div>
                    <h3 className="text-sm font-semibold text-slate-200">{svc.name}</h3>
                    {latency != null && (
                      <div className="flex items-center gap-2 mt-2">
                        <div className="flex-1 h-1 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            animate={{ width: `${Math.min(latency / 10, 100)}%` }}
                            className={`h-full rounded-full ${
                              latency < 50 ? "bg-emerald-500" :
                              latency < 200 ? "bg-amber-500" : "bg-red-500"
                            }`}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-slate-500">{latency.toFixed(0)}ms</span>
                      </div>
                    )}
                    {/* Live activity indicator */}
                    <motion.div
                      animate={isHealthy ? { opacity: [0.3, 1, 0.3] } : {}}
                      transition={{ duration: 3, repeat: Infinity }}
                      className="mt-2 flex items-center gap-1 text-[8px] font-mono text-slate-600"
                    >
                      <span className={`w-1 h-1 rounded-full ${isHealthy ? "bg-emerald-500" : "bg-slate-600"}`} />
                      {isHealthy ? "operational" : status}
                    </motion.div>
                  </motion.div>
                );
              })}
            </div>
          )}

          {/* Health Timeline */}
          <div className="glass-panel p-5">
            <h3 className="text-xs font-bold font-mono text-slate-200 mb-4 flex items-center gap-2 uppercase tracking-wider">
              <Clock className="w-4 h-4 text-platform-400" /> Component Latency
            </h3>
            <div className="space-y-2">
              {healthData?.components.map((comp) => (
                <div key={comp.name} className="flex items-center justify-between p-2 rounded bg-surface-darker/50 border border-surface-border/50">
                  <span className="text-[11px] font-mono text-slate-400 capitalize">{comp.name.replace(/_/g, " ")}</span>
                  <div className="flex items-center gap-3">
                    {comp.latency_ms != null && (
                      <div className="flex items-center gap-2">
                        <div className="w-24 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            animate={{ width: `${Math.min(comp.latency_ms / 5, 100)}%` }}
                            className={`h-full rounded-full ${
                              comp.latency_ms < 50 ? "bg-emerald-500" :
                              comp.latency_ms < 200 ? "bg-amber-500" : "bg-red-500"
                            }`}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-slate-600 w-14 text-right">
                          {comp.latency_ms.toFixed(0)}ms
                        </span>
                      </div>
                    )}
                    <span className={`w-2 h-2 rounded-full ${
                      comp.status === "healthy" ? "bg-emerald-500" :
                      comp.status === "degraded" ? "bg-amber-500" : "bg-red-500"
                    } ${comp.status !== "healthy" ? "animate-pulse" : ""}`} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {selectedTab === "queues" && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Kafka Consumer Lag */}
          <div className="glass-panel p-5">
            <h3 className="text-xs font-bold font-mono text-slate-200 mb-4 flex items-center gap-2 uppercase tracking-wider">
              <Layers className="w-4 h-4 text-amber-400" /> Kafka Consumer Lag
            </h3>
            <div className="space-y-2">
              {kafkaTelemetry?.topics ? (
                <>
                  {Object.entries(kafkaTelemetry.topics).map(([topic, data]: [string, any]) => (
                    <motion.div
                      key={topic}
                      animate={data.lag > 0 ? { opacity: [0.8, 1, 0.8] } : {}}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="flex items-center justify-between p-2 rounded bg-surface-darker/50 border border-surface-border/50"
                    >
                      <span className="text-[11px] font-mono text-slate-400">{topic.replace(/_/g, ".")}</span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            animate={{ width: `${Math.min(data.lag, 100)}%` }}
                            className={`h-full rounded-full ${
                              data.lag === 0 ? "bg-emerald-500" :
                              data.lag < 10 ? "bg-amber-500" : "bg-red-500"
                            }`}
                          />
                        </div>
                        <span className={`text-[11px] font-mono font-bold w-8 text-right ${
                          data.lag === 0 ? "text-emerald-400" :
                          data.lag < 10 ? "text-amber-400" : "text-red-400"
                        }`}>{data.lag}</span>
                      </div>
                    </motion.div>
                  ))}
                  {kafkaTelemetry.total_lag != null && (
                    <div className="mt-3 pt-3 border-t border-surface-border flex items-center justify-between text-[10px] font-mono">
                      <span className="text-slate-500">Total Lag</span>
                      <span className={`font-bold ${
                        kafkaTelemetry.total_lag === 0 ? "text-emerald-400" :
                        kafkaTelemetry.total_lag < 10 ? "text-amber-400" : "text-red-400"
                      }`}>{kafkaTelemetry.total_lag}</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-[11px] font-mono text-slate-600">Loading consumer lag...</div>
              )}
            </div>
          </div>

          {/* Temporal Queue Depths */}
          <div className="glass-panel p-5">
            <h3 className="text-xs font-bold font-mono text-slate-200 mb-4 flex items-center gap-2 uppercase tracking-wider">
              <Server className="w-4 h-4 text-indigo-400" /> Temporal Queue Depths
            </h3>
            <div className="space-y-2">
              {queueTelemetry?.queues ? (
                <>
                  {Object.entries(queueTelemetry.queues).map(([queue, data]: [string, any]) => (
                    <div key={queue} className="flex items-center justify-between p-2 rounded bg-surface-darker/50 border border-surface-border/50">
                      <span className="text-[11px] font-mono text-slate-400 uppercase">
                        {queue.replace("seo-platform-", "").replace(/_/g, " ")}
                      </span>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            animate={{ width: `${Math.min((data.active_workflows || 0) * 10, 100)}%` }}
                            className={`h-full rounded-full ${
                              (data.active_workflows || 0) === 0 ? "bg-emerald-500" :
                              (data.active_workflows || 0) < 5 ? "bg-amber-500" : "bg-red-500"
                            }`}
                          />
                        </div>
                        <span className={`text-[11px] font-mono font-bold ${
                          (data.active_workflows || 0) === 0 ? "text-emerald-400" : "text-amber-400"
                        }`}>{data.active_workflows || 0}</span>
                      </div>
                    </div>
                  ))}
                  {queueTelemetry.total_active_workflows != null && (
                    <div className="mt-3 pt-3 border-t border-surface-border flex items-center justify-between text-[10px] font-mono">
                      <span className="text-slate-500">Total Active</span>
                      <span className="font-bold text-indigo-400">{queueTelemetry.total_active_workflows}</span>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-8 text-[11px] font-mono text-slate-600">Loading queue data...</div>
              )}
            </div>
          </div>

          {/* Worker Pool */}
          <div className="glass-panel p-5">
            <h3 className="text-xs font-bold font-mono text-slate-200 mb-4 flex items-center gap-2 uppercase tracking-wider">
              <Users className="w-4 h-4 text-emerald-400" /> Worker Pool
            </h3>
            <div className="grid grid-cols-3 gap-3 mb-4">
              <WorkerMetric label="Running" count={workerTelemetry?.running_workflows ?? 0} color="emerald" />
              <WorkerMetric label="Completed" count={workerTelemetry?.completed_workflows ?? 0} color="slate" />
              <WorkerMetric label="Failed" count={workerTelemetry?.failed_workflows ?? 0} color="red" />
            </div>
            {workerTelemetry?.workflow_types && (
              <div className="space-y-1.5">
                {Object.entries(workerTelemetry.workflow_types).map(([type, count]: [string, any]) => (
                  <div key={type} className="flex items-center justify-between text-[10px] font-mono p-2 bg-surface-darker/50 rounded border border-surface-border/50">
                    <span className="text-slate-400 truncate max-w-[180px]">{type}</span>
                    <span className="text-emerald-400 font-bold">{count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* SSE Queue State */}
          <div className="glass-panel p-5">
            <h3 className="text-xs font-bold font-mono text-slate-200 mb-4 flex items-center gap-2 uppercase tracking-wider">
              <Radio className="w-4 h-4 text-platform-400" /> SSE Queue State
            </h3>
            {queueEntries.length > 0 ? (
              <div className="space-y-2">
                {queueEntries.map(([queue, depth]) => (
                  <motion.div
                    key={queue}
                    animate={depth > 0 ? { opacity: [0.8, 1, 0.8] } : {}}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="flex items-center justify-between p-2 rounded bg-surface-darker/50 border border-surface-border/50"
                  >
                    <span className="text-[11px] font-mono text-slate-400 uppercase">{queue.replace(/_/g, " ")}</span>
                    <span className={`text-[11px] font-mono font-bold ${
                      depth === 0 ? "text-emerald-400" :
                      depth < 5 ? "text-amber-400" : "text-red-400"
                    }`}>{depth as number}</span>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-[11px] font-mono text-slate-600">No queue state from SSE</div>
            )}
          </div>
        </div>
      )}

      {selectedTab === "workflows" && <WorkflowVisualization />}
    </div>
  );
}

function ShieldStatus({ label, count, total, color }: {
  label: string; count: number; total: number; color: "emerald" | "amber" | "red";
}) {
  const colors = { emerald: "text-emerald-400", amber: "text-amber-400", red: "text-red-400" };
  return (
    <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-darker/50 border border-surface-border/50">
      <span className={`text-xs font-mono font-bold ${colors[color]}`}>{count}</span>
      <span className="text-[9px] font-mono text-slate-500">{label}</span>
    </div>
  );
}

function WorkerMetric({ label, count, color }: {
  label: string; count: number; color: "emerald" | "slate" | "red";
}) {
  const colors = {
    emerald: "text-emerald-400 bg-emerald-500/5 border-emerald-500/20",
    slate: "text-slate-400 bg-surface-darker border-surface-border",
    red: "text-red-400 bg-red-500/5 border-red-500/20",
  };
  return (
    <div className={`p-3 rounded-lg border ${colors[color]} text-center`}>
      <p className={`text-xl font-bold font-mono ${colors[color].split(" ")[0]}`}>{count}</p>
      <p className="text-[9px] font-mono text-slate-500 mt-0.5">{label}</p>
    </div>
  );
}
