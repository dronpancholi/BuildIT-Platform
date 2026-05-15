"use client";

import { motion } from "framer-motion";
import {
  Layers, BarChart3, Activity, TrendingUp, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface CrossTenantAnalytics {
  aggregated_metrics: Record<string, number>;
  active_tenants: number;
  trend_period: string;
}

interface Benchmark {
  operation: string;
  p50: number;
  p75: number;
  p90: number;
  p99: number;
  unit: string;
}

interface WorkflowBaseline {
  workflow_type: string;
  p50_duration_ms: number;
  p95_duration_ms: number;
  success_rate: number;
}

interface OperationalTrend {
  metric: string;
  direction: string;
  change_pct: number;
  significance: string;
}

interface TenantBenchmark {
  tenant_id: string;
  metric: string;
  tenant_value: number;
  benchmark_value: number;
  percentile: number;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function CrossTenantPage() {
  const { data: analytics, isLoading: loadingAnalytics } = useQuery<CrossTenantAnalytics>({
    queryKey: ["cross-tenant-analytics"],
    queryFn: () => fetchApi("/cross-tenant/analytics"),
    refetchInterval: 15000,
  });

  const { data: benchmarks, isLoading: loadingBenchmarks } = useQuery<Benchmark[]>({
    queryKey: ["cross-tenant-benchmarks"],
    queryFn: () => fetchApi("/cross-tenant/benchmarks"),
    refetchInterval: 15000,
  });

  const { data: baselines, isLoading: loadingBaselines } = useQuery<WorkflowBaseline[]>({
    queryKey: ["cross-tenant-baselines"],
    queryFn: () => fetchApi("/cross-tenant/workflow-baselines"),
    refetchInterval: 15000,
  });

  const { data: trends, isLoading: loadingTrends } = useQuery<OperationalTrend[]>({
    queryKey: ["cross-tenant-trends"],
    queryFn: () => fetchApi("/cross-tenant/operational-trends"),
    refetchInterval: 15000,
  });

  const { data: tenantBenchmarks, isLoading: loadingTenant } = useQuery<TenantBenchmark[]>({
    queryKey: ["cross-tenant-tenant-benchmarks"],
    queryFn: () => fetchApi("/cross-tenant/tenant-benchmarks"),
    refetchInterval: 15000,
  });

  const benchmarkList = benchmarks || [];
  const baselineList = baselines || [];
  const trendList = trends || [];
  const tenantBenchList = tenantBenchmarks || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">CROSS_TENANT</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Cross-Tenant Intelligence Dashboard</p>
        </div>
        {analytics && (
          <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 flex items-center gap-2">
            <Layers className="w-4 h-4" />
            {analytics.active_tenants} TENANTS
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cross-Tenant Analytics */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Layers className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">CROSS_TENANT_ANALYTICS</h3>
          </div>
          {loadingAnalytics ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !analytics ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No analytics data</div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <span className="text-2xl font-bold font-mono text-slate-100">{analytics.active_tenants}</span>
                  <p className="text-[10px] font-mono text-slate-500 mt-1">Active Tenants</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <span className="text-2xl font-bold font-mono text-slate-100">{analytics.trend_period}</span>
                  <p className="text-[10px] font-mono text-slate-500 mt-1">Trend Period</p>
                </div>
              </div>
              {analytics.aggregated_metrics && Object.keys(analytics.aggregated_metrics).length > 0 && (
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(analytics.aggregated_metrics).map(([key, val]) => (
                    <div key={key} className="flex items-center justify-between p-2 rounded bg-surface-darker/30 border border-surface-border/30 text-xs font-mono">
                      <span className="text-slate-500 uppercase">{key.replace(/_/g, " ")}</span>
                      <span className="text-slate-300">{typeof val === 'number' ? val.toLocaleString() : val}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* Benchmark Comparisons */}
        <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">BENCHMARK_COMPARISONS</h3>
          </div>
          {loadingBenchmarks ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : benchmarkList.length === 0 ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No benchmark data</div>
          ) : (
            <div className="space-y-3">
              {benchmarkList.map((b, i) => (
                <motion.div
                  key={b.operation || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <p className="text-xs font-mono text-slate-300 uppercase mb-2">{b.operation.replace(/_/g, " ")}</p>
                  <div className="grid grid-cols-4 gap-2">
                    <div className="text-center">
                      <span className="text-sm font-bold font-mono text-emerald-400">{b.p50}</span>
                      <p className="text-[9px] font-mono text-slate-600">P50</p>
                    </div>
                    <div className="text-center">
                      <span className="text-sm font-bold font-mono text-amber-400">{b.p75}</span>
                      <p className="text-[9px] font-mono text-slate-600">P75</p>
                    </div>
                    <div className="text-center">
                      <span className="text-sm font-bold font-mono text-orange-400">{b.p90}</span>
                      <p className="text-[9px] font-mono text-slate-600">P90</p>
                    </div>
                    <div className="text-center">
                      <span className="text-sm font-bold font-mono text-red-400">{b.p99}</span>
                      <p className="text-[9px] font-mono text-slate-600">P99</p>
                    </div>
                  </div>
                  <p className="text-[9px] font-mono text-slate-600 mt-1">Unit: {b.unit}</p>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Workflow Baselines */}
        <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">WORKFLOW_BASELINES</h3>
          </div>
          {loadingBaselines ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : baselineList.length === 0 ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No baseline data</div>
          ) : (
            <div className="space-y-3">
              {baselineList.map((bl, i) => (
                <motion.div
                  key={bl.workflow_type || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-slate-200 uppercase">{bl.workflow_type.replace(/_/g, " ")}</span>
                    <span className={`text-[10px] font-mono font-bold ${bl.success_rate >= 99 ? "text-emerald-400" : bl.success_rate >= 95 ? "text-amber-400" : "text-red-400"}`}>
                      {bl.success_rate.toFixed(1)}% SR
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-[10px] font-mono text-slate-500">
                    <span>P50: <span className="text-slate-300">{bl.p50_duration_ms}ms</span></span>
                    <span>P95: <span className="text-slate-300">{bl.p95_duration_ms}ms</span></span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden mt-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${bl.success_rate}%` }}
                      className={`h-full rounded-full ${bl.success_rate >= 99 ? "bg-emerald-500" : bl.success_rate >= 95 ? "bg-amber-500" : "bg-red-500"}`}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Operational Trends */}
        <motion.div {...slideUp} transition={{ delay: 0.15 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">OPERATIONAL_TRENDS</h3>
          </div>
          {loadingTrends ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : trendList.length === 0 ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No trend data</div>
          ) : (
            <div className="space-y-3">
              {trendList.map((t, i) => (
                <motion.div
                  key={t.metric || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300 uppercase">{t.metric.replace(/_/g, " ")}</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono ${t.direction === "up" ? "text-emerald-400" : t.direction === "down" ? "text-red-400" : "text-amber-400"}`}>
                        {t.direction === "up" ? "↑" : t.direction === "down" ? "↓" : "→"} {t.change_pct > 0 ? "+" : ""}{t.change_pct.toFixed(1)}%
                      </span>
                      <span className={`text-[9px] font-mono px-1 py-0.5 rounded border ${
                        t.significance === "high" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                        t.significance === "medium" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                        "bg-slate-500/10 text-slate-400 border-slate-500/20"
                      }`}>{t.significance.toUpperCase()}</span>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}

          {loadingTenant ? (
            <div className="flex items-center justify-center py-8 mt-4"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : tenantBenchList.length > 0 ? (
            <div className="mt-4 pt-4 border-t border-surface-border">
              <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Tenant vs Benchmark</p>
              <div className="space-y-2">
                {tenantBenchList.slice(0, 5).map((tb, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/30 border border-surface-border/30 text-[10px] font-mono">
                    <span className="text-slate-400 truncate max-w-[120px]">{tb.tenant_id.slice(0, 8)}...</span>
                    <span className="text-slate-500">{tb.metric}</span>
                    <span className="text-slate-300">{typeof tb.percentile === 'number' ? tb.percentile.toFixed(0) : tb.percentile}th</span>
                  </div>
                ))}
              </div>
            </div>
          ) : null}
        </motion.div>
      </div>
    </div>
  );
}
