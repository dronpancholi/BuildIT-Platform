"use client";

import { motion } from "framer-motion";
import {
  GitBranch, Share2, Radio, BarChart3, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface GlobalTopologyRegion {
  region: string;
  workflow_count: number;
  health: number;
  dependencies: string[];
}

interface GlobalWorkflowTopology {
  regions: GlobalTopologyRegion[];
  interdependencies: { source: string; target: string; type: string }[];
}

interface WorkflowFederation {
  federation_health: number;
  consistency_check: string;
  regions_involved: string[];
}

interface CrossClusterCoordination {
  sync_status: string;
  clusters: { cluster: string; status: string; latency_ms: number }[];
}

interface FederationAnalytics {
  total_federated_workflows: number;
  efficiency: number;
  consistency_rate: number;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function GlobalOrchestrationPage() {
  const { data: topology, isLoading: loadingTopology } = useQuery<GlobalWorkflowTopology>({
    queryKey: ["global-orch-topology"],
    queryFn: () => fetchApi("/global-orchestration/global-topology"),
    refetchInterval: 15000,
  });

  const { data: federation, isLoading: loadingFederation } = useQuery<WorkflowFederation>({
    queryKey: ["global-orch-federation"],
    queryFn: () => fetchApi("/global-orchestration/federation"),
    refetchInterval: 15000,
  });

  const { data: crossCluster, isLoading: loadingCross } = useQuery<CrossClusterCoordination>({
    queryKey: ["global-orch-cross-cluster"],
    queryFn: () => fetchApi("/global-orchestration/cross-cluster"),
    refetchInterval: 15000,
  });

  const { data: analytics, isLoading: loadingAnalytics } = useQuery<FederationAnalytics>({
    queryKey: ["global-orch-analytics"],
    queryFn: () => fetchApi("/global-orchestration/federation-analytics"),
    refetchInterval: 15000,
  });

  const regionList = topology?.regions || [];
  const interdependencies = topology?.interdependencies || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">GLOBAL_ORCHESTRATION</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Global Workflow Orchestration Dashboard</p>
        </div>
        {analytics && (
          <div className="px-3 py-1.5 rounded-md bg-platform-500/10 border border-platform-500/30 text-xs font-mono text-platform-400 flex items-center gap-2">
            <Share2 className="w-4 h-4" />
            {analytics.total_federated_workflows} FEDERATED
          </div>
        )}
      </div>

      {loadingTopology && regionList.length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Global Workflow Topology */}
            <motion.div {...slideUp} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <GitBranch className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">GLOBAL_WORKFLOW_TOPOLOGY</h3>
              </div>
              {regionList.length === 0 ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No topology data</div>
              ) : (
                <div className="space-y-3">
                  {regionList.map((r, i) => (
                    <motion.div
                      key={r.region || i}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-mono text-slate-200">{r.region}</span>
                        <span className={`text-[10px] font-mono font-bold ${r.health >= 80 ? "text-emerald-400" : r.health >= 50 ? "text-amber-400" : "text-red-400"}`}>
                          {Math.round(r.health)}% HEALTH
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden mb-2">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${r.health}%` }}
                          className={`h-full rounded-full ${r.health >= 80 ? "bg-emerald-500" : r.health >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                      <div className="flex items-center justify-between text-[10px] font-mono">
                        <span className="text-slate-500">{r.workflow_count} workflows</span>
                        {r.dependencies.length > 0 && (
                          <span className="text-slate-600">{r.dependencies.length} dependencies</span>
                        )}
                      </div>
                      {r.dependencies.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {r.dependencies.map((dep, j) => (
                            <span key={j} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-slate-500/10 text-slate-500">{dep}</span>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  ))}
                  {interdependencies.length > 0 && (
                    <div className="pt-3 border-t border-surface-border">
                      <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Interdependencies</p>
                      <div className="space-y-1">
                        {interdependencies.map((dep, i) => (
                          <div key={i} className="text-[10px] font-mono text-slate-400">
                            {dep.source} → {dep.target} <span className="text-slate-600">({dep.type})</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.div>

            {/* Workflow Federation */}
            <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Share2 className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">WORKFLOW_FEDERATION</h3>
              </div>
              {loadingFederation ? (
                <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
              ) : !federation ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No federation data</div>
              ) : (
                <div className="space-y-4">
                  <div className="text-center">
                    <span className={`text-4xl font-bold font-mono ${federation.federation_health >= 80 ? "text-emerald-400" : federation.federation_health >= 50 ? "text-amber-400" : "text-red-400"}`}>
                      {Math.round(federation.federation_health)}%
                    </span>
                    <p className="text-xs font-mono text-slate-500 mt-1">Federation Health</p>
                  </div>
                  <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${federation.federation_health}%` }}
                      className={`h-full rounded-full ${federation.federation_health >= 80 ? "bg-emerald-500" : federation.federation_health >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                    <span className="text-xs font-mono text-slate-400">Consistency</span>
                    <span className={`text-xs font-mono font-bold ${federation.consistency_check === "consistent" ? "text-emerald-400" : "text-amber-400"}`}>
                      {federation.consistency_check.toUpperCase()}
                    </span>
                  </div>
                  {federation.regions_involved.length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Regions Involved</p>
                      <div className="flex flex-wrap gap-1">
                        {federation.regions_involved.map((rg, i) => (
                          <span key={i} className="px-2 py-0.5 rounded text-[10px] font-mono bg-platform-500/10 text-platform-400 border border-platform-500/20">{rg}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Cross-Cluster Coordination */}
            <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Radio className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">CROSS_CLUSTER_COORDINATION</h3>
              </div>
              {loadingCross ? (
                <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
              ) : !crossCluster ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No cross-cluster data</div>
              ) : (
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                    <span className="text-xs font-mono text-slate-400">Sync Status</span>
                    <span className={`text-xs font-mono font-bold ${crossCluster.sync_status === "synced" ? "text-emerald-400" : crossCluster.sync_status === "syncing" ? "text-amber-400" : "text-red-400"}`}>
                      {crossCluster.sync_status.toUpperCase()}
                    </span>
                  </div>
                  {crossCluster.clusters.map((c, i) => (
                    <motion.div
                      key={c.cluster || i}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-mono text-slate-300">{c.cluster}</span>
                        <span className={`text-[10px] font-mono ${c.status === "healthy" ? "text-emerald-400" : c.status === "degraded" ? "text-amber-400" : "text-red-400"}`}>
                          {c.status.toUpperCase()}
                        </span>
                      </div>
                      <div className="text-[10px] font-mono text-slate-500">Latency: {c.latency_ms}ms</div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Federation Analytics */}
            <motion.div {...slideUp} transition={{ delay: 0.15 }} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <BarChart3 className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">FEDERATION_ANALYTICS</h3>
              </div>
              {loadingAnalytics ? (
                <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
              ) : !analytics ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No analytics data</div>
              ) : (
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                    <span className="text-3xl font-bold font-mono text-slate-100">{analytics.total_federated_workflows}</span>
                    <p className="text-[10px] font-mono text-slate-500 mt-1">Federated Workflows</p>
                  </div>
                  <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                    <span className={`text-3xl font-bold font-mono ${analytics.efficiency >= 80 ? "text-emerald-400" : analytics.efficiency >= 50 ? "text-amber-400" : "text-red-400"}`}>
                      {Math.round(analytics.efficiency)}%
                    </span>
                    <p className="text-[10px] font-mono text-slate-500 mt-1">Efficiency</p>
                  </div>
                  <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                    <span className={`text-3xl font-bold font-mono ${analytics.consistency_rate >= 80 ? "text-emerald-400" : analytics.consistency_rate >= 50 ? "text-amber-400" : "text-red-400"}`}>
                      {Math.round(analytics.consistency_rate)}%
                    </span>
                    <p className="text-[10px] font-mono text-slate-500 mt-1">Consistency Rate</p>
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        </>
      )}
    </div>
  );
}
