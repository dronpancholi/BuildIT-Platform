"use client";

import { motion } from "framer-motion";
import {
  Share2, GitFork, Server, BarChart3, Activity, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface OrchestrationFederationPlan {
  region: string;
  federation_topology: { peer: string; connection_type: string; latency_ms: number }[];
  consistency_model: string;
  recommended: boolean;
}

interface WorkflowShardConfig {
  workflow_type: string;
  total_shards: number;
  recommended_shards: number;
  estimated_throughput: number;
}

interface DistributedExecutionAnalysis {
  distribution_efficiency: number;
  execution_nodes: { node: string; tasks: number; load_pct: number }[];
  skew_detected: boolean;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function ExtremeScaleOrchestrationPage() {
  const { data: federation, isLoading: loadingFed } = useQuery<OrchestrationFederationPlan>({
    queryKey: ["federation"],
    queryFn: () => fetchApi("/extreme-scale-orchestration/orchestration-federation?region=us-east-1"),
  });

  const { data: sharding, isLoading: loadingShard } = useQuery<WorkflowShardConfig>({
    queryKey: ["sharding"],
    queryFn: () => fetchApi("/extreme-scale-orchestration/workflow-sharding?workflow_type=data_processing"),
  });

  const { data: execution, isLoading: loadingExec } = useQuery<DistributedExecutionAnalysis>({
    queryKey: ["execution-analysis"],
    queryFn: () => fetchApi("/extreme-scale-orchestration/distributed-execution-analysis?workflow_id=wf-extreme-001"),
  });

  if (loadingFed || loadingShard || loadingExec) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-platform-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <motion.div {...slideUp}>
        <h1 className="text-3xl font-bold text-slate-100">Extreme-Scale Orchestration</h1>
        <p className="text-slate-400 mt-1">Ultra-scale queue partitioning, federation, sharding, and distributed execution</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Share2 className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Federation</h2>
          </div>
          {federation && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg font-bold text-slate-200">{federation.region}</span>
                {federation.recommended ? (
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium border bg-green-500/10 text-green-400 border-green-500/20">
                    recommended
                  </span>
                ) : (
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium border bg-amber-500/10 text-amber-400 border-amber-500/20">
                    review needed
                  </span>
                )}
              </div>
              <div className="text-xs text-slate-500 mb-2">Consistency: {federation.consistency_model}</div>
              {federation.federation_topology.map((p, i) => (
                <div key={i} className="flex items-center justify-between text-xs p-2 rounded bg-slate-800/30">
                  <span className="text-slate-300">{p.peer}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-500">{p.connection_type}</span>
                    <span className="text-slate-400">{p.latency_ms}ms</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <GitFork className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Workflow Sharding</h2>
          </div>
          {sharding && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-amber-400">{sharding.recommended_shards}</span>
                <span className="text-sm text-slate-400">recommended shards</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-slate-400">Current: <span className="text-slate-200">{sharding.total_shards}</span></div>
                <div className="text-slate-400">Throughput: <span className="text-slate-200">{sharding.estimated_throughput.toLocaleString()}/s</span></div>
              </div>
              <div className="text-xs text-slate-400">{sharding.workflow_type}</div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-green-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Distributed Execution</h2>
          </div>
          {execution && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-green-400">{(execution.distribution_efficiency * 100).toFixed(0)}%</span>
                <span className="text-sm text-slate-400">efficiency</span>
              </div>
              {execution.skew_detected && (
                <div className="px-2 py-1 rounded bg-amber-500/10 border border-amber-500/20 text-xs text-amber-400">
                  Skew detected — rebalancing recommended
                </div>
              )}
              {execution.execution_nodes.map((n, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className="w-20 text-slate-400">{n.node}</span>
                  <div className="flex-1 bg-surface-border rounded-full h-1.5">
                    <div className={`rounded-full h-1.5 ${n.load_pct > 80 ? "bg-red-500" : n.load_pct > 60 ? "bg-amber-500" : "bg-green-500"}`}
                      style={{ width: `${n.load_pct}%` }} />
                  </div>
                  <span className="w-12 text-right text-slate-400">{n.tasks}tasks</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
