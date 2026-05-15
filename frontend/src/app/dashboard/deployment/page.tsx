"use client";

import { motion } from "framer-motion";
import {
  Container, Server, Activity, Shield, Loader2, CheckCircle2,
  XCircle, BarChart3, TrendingUp, Clock, ArrowUpRight, Globe, AlertTriangle,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface ServiceInstance {
  id: string;
  name: string;
  version: string;
  status: "healthy" | "degraded" | "unhealthy";
  region: string;
  uptime_pct: number;
}

interface AutoscalingStatus {
  current_replicas: number;
  min_replicas: number;
  max_replicas: number;
  target_cpu_utilization: number;
  current_cpu_utilization: number;
  recommendations: string[];
}

interface MultiRegionReadiness {
  regions: { name: string; status: string; health_score: number; failover_ready: boolean }[];
  failover_readiness: number;
}

interface RollbackSafety {
  checks: { check: string; status: "pass" | "fail" | "warn"; detail: string }[];
  overall_safe: boolean;
}

interface CanaryAnalysis {
  status: string;
  metrics: { metric: string; canary_value: number; baseline_value: number; deviation_pct: number }[];
  recommendation: string;
}

interface DeploymentIntelligence {
  total_deployments: number;
  failure_rate: number;
  mttr_minutes: number;
  trend: string;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

const STATUS_DOT: Record<string, string> = {
  healthy: "bg-emerald-500",
  degraded: "bg-amber-500",
  unhealthy: "bg-red-500",
};

export default function DeploymentPage() {
  const { data: topology, isLoading: loadingTopo } = useQuery<ServiceInstance[]>({
    queryKey: ["deployment-topology"],
    queryFn: () => fetchApi("/deployment/topology"),
    refetchInterval: 15000,
  });

  const { data: autoscaling, isLoading: loadingAuto } = useQuery<AutoscalingStatus>({
    queryKey: ["deployment-autoscaling"],
    queryFn: () => fetchApi("/deployment/autoscaling-optimization"),
    refetchInterval: 15000,
  });

  const { data: multiRegion, isLoading: loadingRegion } = useQuery<MultiRegionReadiness>({
    queryKey: ["deployment-multi-region"],
    queryFn: () => fetchApi("/deployment/multi-region-readiness"),
    refetchInterval: 15000,
  });

  const { data: rollback, isLoading: loadingRollback } = useQuery<RollbackSafety>({
    queryKey: ["deployment-rollback-safety"],
    queryFn: () => fetchApi("/deployment/rollback-safety"),
    refetchInterval: 15000,
  });

  const { data: canary, isLoading: loadingCanary } = useQuery<CanaryAnalysis>({
    queryKey: ["deployment-canary"],
    queryFn: () => fetchApi("/deployment/canary-analysis"),
    refetchInterval: 15000,
  });

  const { data: intelligence, isLoading: loadingIntel } = useQuery<DeploymentIntelligence>({
    queryKey: ["deployment-intelligence"],
    queryFn: () => fetchApi("/deployment/intelligence"),
    refetchInterval: 15000,
  });

  const instances = topology || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">DEPLOYMENT</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Production Deployment Dashboard</p>
        </div>
        {intelligence && (
          <span className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400">
            {intelligence.total_deployments} DEPLOYS
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Production Topology */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">PRODUCTION_TOPOLOGY</h3>
            <span className="ml-auto text-xs font-mono text-slate-500">{instances.length} instances</span>
          </div>
          {loadingTopo ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : instances.length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No topology data</div>
          ) : (
            <div className="space-y-2 max-h-[350px] overflow-auto custom-scrollbar">
              {instances.map((inst, i) => (
                <motion.div
                  key={inst.id || i}
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-center justify-between p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center gap-3">
                    <span className={`w-2 h-2 rounded-full ${STATUS_DOT[inst.status] || "bg-slate-500"} ${inst.status === "unhealthy" ? "animate-pulse" : ""}`} />
                    <div>
                      <span className="text-xs font-mono text-slate-300">{inst.name}</span>
                      <span className="text-[9px] font-mono text-slate-600 ml-2">v{inst.version}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] font-mono text-slate-500">{inst.region}</span>
                    <span className={`text-[10px] font-mono ${inst.uptime_pct >= 99 ? "text-emerald-400" : "text-amber-400"}`}>
                      {inst.uptime_pct.toFixed(1)}%
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Autoscaling Status */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-cyan-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">AUTOSCALING_STATUS</h3>
          </div>
          {loadingAuto ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !autoscaling ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No autoscaling data</div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-center flex-1">
                  <span className="text-3xl font-bold font-mono text-slate-100">{autoscaling.current_replicas}</span>
                  <p className="text-[10px] font-mono text-slate-500">Current</p>
                </div>
                <span className="text-slate-600 text-lg">/</span>
                <div className="text-center flex-1">
                  <span className="text-3xl font-bold font-mono text-slate-100">{autoscaling.max_replicas}</span>
                  <p className="text-[10px] font-mono text-slate-500">Max</p>
                </div>
              </div>
              <div className="w-full h-3 bg-surface-darker rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${(autoscaling.current_replicas / Math.max(autoscaling.max_replicas, 1)) * 100}%` }}
                  className="h-full rounded-full bg-platform-500"
                  transition={{ duration: 0.5 }}
                />
              </div>
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="p-2 rounded bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-xs font-mono text-slate-300">{autoscaling.current_cpu_utilization.toFixed(1)}%</p>
                  <p className="text-[9px] font-mono text-slate-500">CPU Util</p>
                </div>
                <div className="p-2 rounded bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-xs font-mono text-slate-300">Target {autoscaling.target_cpu_utilization}%</p>
                  <p className="text-[9px] font-mono text-slate-500">Target CPU</p>
                </div>
              </div>
              {autoscaling.recommendations.length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  <p className="text-[10px] font-mono text-amber-400 uppercase">Recommendations</p>
                  {autoscaling.recommendations.map((r, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {r.replace(/_/g, " ")}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Multi-Region Readiness */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5 text-emerald-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">MULTI_REGION_READINESS</h3>
          </div>
          {loadingRegion ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !multiRegion ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No multi-region data</div>
          ) : (
            <div className="space-y-4">
              <div className="text-center">
                <span className={`text-3xl font-bold font-mono ${multiRegion.failover_readiness >= 80 ? "text-emerald-400" : multiRegion.failover_readiness >= 50 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(multiRegion.failover_readiness)}%
                </span>
                <p className="text-xs font-mono text-slate-500 mt-1">Failover Readiness</p>
              </div>
              <div className="space-y-2">
                {multiRegion.regions.map((r, i) => (
                  <div key={r.name || i} className="flex items-center justify-between p-2.5 rounded bg-surface-darker/50 border border-surface-border/50">
                    <div className="flex items-center gap-2">
                      <span className={`w-2 h-2 rounded-full ${r.status === "healthy" ? "bg-emerald-500" : r.status === "degraded" ? "bg-amber-500" : "bg-red-500"}`} />
                      <span className="text-xs font-mono text-slate-300">{r.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-slate-500">{Math.round(r.health_score)}%</span>
                      {r.failover_ready ? (
                        <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                      ) : (
                        <XCircle className="w-3 h-3 text-red-500" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        {/* Rollback Safety */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">ROLLBACK_SAFETY</h3>
            {rollback && (
              <span className={`ml-auto text-xs font-mono px-2 py-0.5 rounded border flex items-center gap-1 ${
                rollback.overall_safe ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-red-500/10 text-red-400 border-red-500/20"
              }`}>
                {rollback.overall_safe ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
                {rollback.overall_safe ? "SAFE" : "UNSAFE"}
              </span>
            )}
          </div>
          {loadingRollback ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !rollback ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No rollback data</div>
          ) : (
            <div className="space-y-2">
              {rollback.checks.map((c, i) => (
                <motion.div
                  key={c.check || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-center justify-between p-2.5 rounded bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center gap-2">
                    {c.status === "pass" ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : c.status === "fail" ? (
                      <XCircle className="w-4 h-4 text-red-500" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                    )}
                    <span className="text-xs font-mono text-slate-300">{c.check.replace(/_/g, " ")}</span>
                  </div>
                  <span className={`text-[10px] font-mono ${
                    c.status === "pass" ? "text-emerald-400" : c.status === "fail" ? "text-red-400" : "text-amber-400"
                  }`}>{c.detail}</span>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Canary Analysis */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-purple-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">CANARY_ANALYSIS</h3>
            {canary && (
              <span className={`ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                canary.recommendation === "promote" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                canary.recommendation === "rollback" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                "bg-amber-500/10 text-amber-400 border-amber-500/20"
              }`}>{canary.recommendation.toUpperCase()}</span>
            )}
          </div>
          {loadingCanary ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !canary ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No canary data</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-mono text-slate-500 uppercase">Status</span>
                <span className={`text-xs font-mono ${canary.status === "running" ? "text-blue-400" : canary.status === "completed" ? "text-emerald-400" : "text-amber-400"}`}>
                  {canary.status.toUpperCase()}
                </span>
              </div>
              {canary.metrics.map((m, i) => (
                <div key={m.metric || i} className="p-2.5 rounded bg-surface-darker/50 border border-surface-border/50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[10px] font-mono text-slate-400 uppercase">{m.metric.replace(/_/g, " ")}</span>
                    <span className={`text-[10px] font-mono font-bold ${Math.abs(m.deviation_pct) > 10 ? "text-red-400" : Math.abs(m.deviation_pct) > 5 ? "text-amber-400" : "text-emerald-400"}`}>
                      {m.deviation_pct > 0 ? "+" : ""}{m.deviation_pct.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between text-[9px] font-mono text-slate-600">
                    <span>Canary: {m.canary_value}</span>
                    <span>Baseline: {m.baseline_value}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Deployment Intelligence */}
      <motion.div {...slideUp} className="glass-panel p-6">
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5 text-platform-500" />
          <h3 className="text-lg font-medium text-slate-200 font-mono">DEPLOYMENT_INTELLIGENCE</h3>
        </div>
        {loadingIntel ? (
          <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
        ) : !intelligence ? (
          <div className="text-center py-8 text-sm font-mono text-slate-500">No deployment intelligence data</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
              <p className="text-2xl font-bold font-mono text-slate-100">{intelligence.total_deployments}</p>
              <p className="text-[10px] font-mono text-slate-500">Total Deployments</p>
            </div>
            <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
              <p className={`text-2xl font-bold font-mono ${intelligence.failure_rate > 10 ? "text-red-400" : "text-emerald-400"}`}>
                {intelligence.failure_rate.toFixed(1)}%
              </p>
              <p className="text-[10px] font-mono text-slate-500">Failure Rate</p>
            </div>
            <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
              <p className="text-2xl font-bold font-mono text-amber-400">{Math.round(intelligence.mttr_minutes)}m</p>
              <p className="text-[10px] font-mono text-slate-500">MTTR</p>
            </div>
            <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
              <p className={`text-2xl font-bold font-mono ${intelligence.trend === "improving" ? "text-emerald-400" : intelligence.trend === "degrading" ? "text-red-400" : "text-amber-400"}`}>
                {intelligence.trend.toUpperCase()}
              </p>
              <p className="text-[10px] font-mono text-slate-500">Trend</p>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  );
}
