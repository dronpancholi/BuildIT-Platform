"use client";

import { motion } from "framer-motion";
import {
  Wrench, Activity, Clock, RefreshCw, Server, Loader2,
  CheckCircle2, AlertTriangle, XCircle, BarChart3,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface SchemaEvolution {
  schema_name: string;
  current_version: number;
  total_versions: number;
  last_migration: string;
  status: string;
}

interface TemporalVersion {
  version_id: string;
  workflow_type: string;
  version: number;
  created_at: string;
  compatibility: string;
}

interface ReplayCompatibility {
  workflow_type: string;
  current_version: number;
  oldest_compatible_version: number;
  replay_success_rate: number;
}

interface LongTermMaintainability {
  score: number;
  technical_debt: string;
  deprecated_components: string[];
  recommendations: string[];
}

interface ServiceDependency {
  service: string;
  dependencies: string[];
  dependents: string[];
  health: string;
}

interface PlatformLifecycle {
  component: string;
  version: string;
  release_date: string;
  end_of_life: string;
  status: string;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function MaintainabilityPage() {
  const { data: schemaEvolution, isLoading: loadingSchema } = useQuery<SchemaEvolution[]>({
    queryKey: ["maintainability-schema"],
    queryFn: () => fetchApi("/maintainability/event-schema-evolution"),
    refetchInterval: 15000,
  });

  const { data: temporalVersions, isLoading: loadingTemporal } = useQuery<TemporalVersion[]>({
    queryKey: ["maintainability-temporal"],
    queryFn: () => fetchApi("/maintainability/temporal-versioning"),
    refetchInterval: 15000,
  });

  const { data: replayCompat, isLoading: loadingReplay } = useQuery<ReplayCompatibility[]>({
    queryKey: ["maintainability-replay"],
    queryFn: () => fetchApi("/maintainability/replay-compatibility"),
    refetchInterval: 15000,
  });

  const { data: longTerm, isLoading: loadingLong } = useQuery<LongTermMaintainability>({
    queryKey: ["maintainability-long-term"],
    queryFn: () => fetchApi("/maintainability/long-term"),
    refetchInterval: 15000,
  });

  const { data: dependencies, isLoading: loadingDeps } = useQuery<ServiceDependency[]>({
    queryKey: ["maintainability-dependencies"],
    queryFn: () => fetchApi("/maintainability/service-dependencies"),
    refetchInterval: 15000,
  });

  const { data: lifecycle, isLoading: loadingLifecycle } = useQuery<PlatformLifecycle[]>({
    queryKey: ["maintainability-lifecycle"],
    queryFn: () => fetchApi("/maintainability/platform-lifecycle"),
    refetchInterval: 15000,
  });

  const schemas = schemaEvolution || [];
  const temporalVersionsList = temporalVersions || [];
  const replayList = replayCompat || [];
  const depsList = dependencies || [];
  const lifecycleList = lifecycle || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">MAINTAINABILITY</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Platform Maintainability Dashboard</p>
        </div>
        {longTerm && (
          <span className={`px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 ${
            longTerm.score >= 70 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
            longTerm.score >= 40 ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
            "bg-red-500/10 text-red-400 border-red-500/20"
          }`}>
            <Wrench className="w-4 h-4" />
            SCORE: {Math.round(longTerm.score)}%
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Event Schema Evolution */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">SCHEMA_EVOLUTION</h3>
          </div>
          {loadingSchema ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : schemas.length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No schema data</div>
          ) : (
            <div className="space-y-3">
              {schemas.map((s, i) => (
                <motion.div
                  key={s.schema_name || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300 uppercase">{s.schema_name.replace(/_/g, " ")}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      s.status === "active" ? "bg-emerald-500/10 text-emerald-400" :
                      s.status === "deprecated" ? "bg-amber-500/10 text-amber-400" :
                      "bg-red-500/10 text-red-400"
                    }`}>{s.status.toUpperCase()}</span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
                    <span>v{s.current_version}/{s.total_versions}</span>
                    <span>Last: {new Date(s.last_migration).toLocaleDateString()}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Temporal Versioning */}
        <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">TEMPORAL_VERSIONS</h3>
          </div>
          {loadingTemporal ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : temporalVersionsList.length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No temporal version data</div>
          ) : (
            <div className="space-y-2">
              {temporalVersionsList.slice(0, 8).map((v, i) => (
                <motion.div
                  key={v.version_id || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-center justify-between p-2.5 rounded bg-surface-darker/50 border border-surface-border/50"
                >
                  <div>
                    <span className="text-xs font-mono text-slate-300">{v.workflow_type.replace(/_/g, " ")}</span>
                    <span className="text-[9px] font-mono text-slate-600 ml-2">v{v.version}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono ${
                      v.compatibility === "compatible" ? "text-emerald-400" :
                      v.compatibility === "deprecated" ? "text-amber-400" :
                      "text-red-400"
                    }`}>{v.compatibility.toUpperCase()}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Replay Compatibility */}
        <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <RefreshCw className="w-5 h-5 text-emerald-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">REPLAY_COMPATIBILITY</h3>
          </div>
          {loadingReplay ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : replayList.length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No replay data</div>
          ) : (
            <div className="space-y-3">
              {replayList.map((r, i) => (
                <motion.div
                  key={r.workflow_type || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300">{r.workflow_type.replace(/_/g, " ")}</span>
                    <span className={`text-xs font-mono font-bold ${r.replay_success_rate >= 95 ? "text-emerald-400" : r.replay_success_rate >= 80 ? "text-amber-400" : "text-red-400"}`}>
                      {Math.round(r.replay_success_rate)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${r.replay_success_rate}%` }}
                      className={`h-full rounded-full ${r.replay_success_rate >= 95 ? "bg-emerald-500" : r.replay_success_rate >= 80 ? "bg-amber-500" : "bg-red-500"}`}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  <div className="flex justify-between text-[9px] font-mono text-slate-600 mt-1">
                    <span>Current: v{r.current_version}</span>
                    <span>Oldest Compatible: v{r.oldest_compatible_version}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Long-Term Maintainability */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Wrench className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">LONG_TERM_MAINTAINABILITY</h3>
            {longTerm && (
              <span className="ml-auto text-lg font-bold font-mono text-slate-100">{Math.round(longTerm.score)}%</span>
            )}
          </div>
          {loadingLong ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !longTerm ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No data</div>
          ) : (
            <div className="space-y-4">
              <div className="w-full h-4 bg-surface-darker rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${longTerm.score}%` }}
                  className={`h-full rounded-full ${longTerm.score >= 70 ? "bg-emerald-500" : longTerm.score >= 40 ? "bg-amber-500" : "bg-red-500"}`}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                <p className="text-[10px] font-mono text-slate-500 uppercase mb-1">Technical Debt</p>
                <p className="text-xs font-mono text-slate-300">{longTerm.technical_debt}</p>
              </div>
              {longTerm.deprecated_components.length > 0 && (
                <div>
                  <p className="text-[10px] font-mono text-amber-400 uppercase mb-1">Deprecated Components</p>
                  <div className="flex flex-wrap gap-1">
                    {longTerm.deprecated_components.map((c, i) => (
                      <span key={i} className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-500/10 text-amber-400 border border-amber-500/20">{c}</span>
                    ))}
                  </div>
                </div>
              )}
              {longTerm.recommendations.length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  <p className="text-[10px] font-mono text-platform-400 uppercase">Recommendations</p>
                  {longTerm.recommendations.map((r, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {r.replace(/_/g, " ")}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* Service Dependencies */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-5 h-5 text-cyan-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">SERVICE_DEPENDENCIES</h3>
            <span className="ml-auto text-xs font-mono text-slate-500">{depsList.length} services</span>
          </div>
          {loadingDeps ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : depsList.length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No dependency data</div>
          ) : (
            <div className="space-y-2 max-h-[350px] overflow-auto custom-scrollbar">
              {depsList.map((d, i) => (
                <motion.div
                  key={d.service || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300">{d.service}</span>
                    <span className={`w-2 h-2 rounded-full ${d.health === "healthy" ? "bg-emerald-500" : d.health === "degraded" ? "bg-amber-500" : "bg-red-500"}`} />
                  </div>
                  <div className="flex gap-4 text-[10px] font-mono">
                    {d.dependencies.length > 0 && (
                      <span className="text-slate-500">Depends on: {d.dependencies.join(", ")}</span>
                    )}
                    {d.dependents.length > 0 && (
                      <span className="text-slate-500">Used by: {d.dependents.join(", ")}</span>
                    )}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      {/* Platform Lifecycle */}
      <motion.div {...slideUp} className="glass-panel p-6">
        <div className="flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-platform-500" />
          <h3 className="text-lg font-medium text-slate-200 font-mono">PLATFORM_LIFECYCLE</h3>
        </div>
        {loadingLifecycle ? (
          <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
        ) : lifecycleList.length === 0 ? (
          <div className="text-center py-8 text-sm font-mono text-slate-500">No lifecycle data</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm font-mono">
              <thead>
                <tr className="text-[10px] text-slate-500 uppercase border-b border-surface-border">
                  <th className="px-4 py-3 text-left font-medium">Component</th>
                  <th className="px-4 py-3 text-left font-medium">Version</th>
                  <th className="px-4 py-3 text-left font-medium">Release Date</th>
                  <th className="px-4 py-3 text-left font-medium">End of Life</th>
                  <th className="px-4 py-3 text-left font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {lifecycleList.map((c, i) => (
                  <motion.tr
                    key={c.component || i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.03 }}
                    className="hover:bg-surface-darker/30"
                  >
                    <td className="px-4 py-3 text-xs text-slate-300">{c.component}</td>
                    <td className="px-4 py-3 text-xs text-slate-400">{c.version}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{new Date(c.release_date).toLocaleDateString()}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{new Date(c.end_of_life).toLocaleDateString()}</td>
                    <td className="px-4 py-3">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded ${
                        c.status === "supported" ? "bg-emerald-500/10 text-emerald-400" :
                        c.status === "deprecated" ? "bg-amber-500/10 text-amber-400" :
                        "bg-red-500/10 text-red-400"
                      }`}>{c.status.toUpperCase()}</span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </motion.div>
    </div>
  );
}
