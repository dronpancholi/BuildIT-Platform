"use client";

import { motion } from "framer-motion";
import {
  Globe, Server, Activity, Network, Navigation, Shield,
  Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface RegionDeployment {
  region: string;
  status: string;
  health_score: number;
  replica_count: number;
  active_connections: number;
}

interface ActiveActiveTopology {
  global_health_score: number;
  traffic_distribution: Record<string, number>;
  load_percentages: Record<string, number>;
}

interface GeoRoute {
  workflow_type: string;
  strategy: string;
  preferred_region: string;
  latency_threshold_ms: number;
}

interface DisasterRecovery {
  region: string;
  dr_readiness: number;
  rpo_seconds: number;
  rto_seconds: number;
  last_dr_test: string;
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
  active: "bg-emerald-500",
  stand: "bg-amber-500",
};

export default function GlobalInfraPage() {
  const { data: regions, isLoading: loadingRegions } = useQuery<RegionDeployment[]>({
    queryKey: ["global-infra-regions"],
    queryFn: () => fetchApi("/global-infra/regions"),
    refetchInterval: 15000,
  });

  const { data: topology, isLoading: loadingTopology } = useQuery<ActiveActiveTopology>({
    queryKey: ["global-infra-topology"],
    queryFn: () => fetchApi("/global-infra/active-active-topology"),
    refetchInterval: 15000,
  });

  const { data: geoRoutes, isLoading: loadingRoutes } = useQuery<GeoRoute[]>({
    queryKey: ["global-infra-geo-routes"],
    queryFn: () => fetchApi("/global-infra/geo-routes"),
    refetchInterval: 15000,
  });

  const { data: drStatus, isLoading: loadingDr } = useQuery<DisasterRecovery[]>({
    queryKey: ["global-infra-dr"],
    queryFn: () => fetchApi("/global-infra/disaster-recovery"),
    refetchInterval: 15000,
  });

  const regionList = regions || [];
  const routeList = geoRoutes || [];
  const drList = drStatus || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">GLOBAL_INFRA</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Global Infrastructure Command Center</p>
        </div>
        <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 flex items-center gap-2">
          <Globe className="w-4 h-4" />
          {regionList.length} REGIONS
        </div>
      </div>

      {loadingRegions && regionList.length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Global Region Map */}
            <motion.div {...slideUp} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Globe className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">GLOBAL_REGION_MAP</h3>
              </div>
              {regionList.length === 0 ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No region data</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {regionList.map((r, i) => (
                    <motion.div
                      key={r.region || i}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${STATUS_DOT[r.status] || "bg-slate-500"} ${r.status === "unhealthy" ? "animate-pulse" : ""}`} />
                          <span className="text-sm font-mono text-slate-200">{r.region}</span>
                        </div>
                        <span className="text-[10px] font-mono text-slate-500 uppercase">{r.status}</span>
                      </div>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs font-mono">
                          <span className="text-slate-500">Health Score</span>
                          <span className={`font-bold ${r.health_score >= 80 ? "text-emerald-400" : r.health_score >= 50 ? "text-amber-400" : "text-red-400"}`}>
                            {Math.round(r.health_score)}%
                          </span>
                        </div>
                        <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${r.health_score}%` }}
                            className={`h-full rounded-full ${r.health_score >= 80 ? "bg-emerald-500" : r.health_score >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                            transition={{ duration: 0.5 }}
                          />
                        </div>
                        <div className="flex items-center justify-between text-[10px] font-mono text-slate-600 pt-1 border-t border-surface-border/50">
                          <span className="flex items-center gap-1"><Server className="w-3 h-3" /> {r.replica_count} replicas</span>
                          <span className="flex items-center gap-1"><Activity className="w-3 h-3" /> {r.active_connections} conns</span>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Active-Active Topology */}
            <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Network className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">ACTIVE_ACTIVE_TOPOLOGY</h3>
              </div>
              {loadingTopology ? (
                <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
              ) : !topology ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No topology data</div>
              ) : (
                <div className="space-y-4">
                  <div className="text-center">
                    <span className={`text-4xl font-bold font-mono ${topology.global_health_score >= 80 ? "text-emerald-400" : topology.global_health_score >= 50 ? "text-amber-400" : "text-red-400"}`}>
                      {Math.round(topology.global_health_score)}%
                    </span>
                    <p className="text-xs font-mono text-slate-500 mt-1">Global Health Score</p>
                  </div>
                  <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${topology.global_health_score}%` }}
                      className={`h-full rounded-full ${topology.global_health_score >= 80 ? "bg-emerald-500" : topology.global_health_score >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  {topology.traffic_distribution && Object.keys(topology.traffic_distribution).length > 0 && (
                    <div>
                      <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Traffic Distribution</p>
                      <div className="space-y-2">
                        {Object.entries(topology.traffic_distribution).map(([region, pct], i) => (
                          <div key={region}>
                            <div className="flex items-center justify-between text-xs font-mono mb-0.5">
                              <span className="text-slate-300">{region}</span>
                              <span className="text-slate-500">{typeof pct === 'number' ? Math.round(pct) : pct}%</span>
                            </div>
                            <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${typeof pct === 'number' ? pct : 0}%` }}
                                className="h-full rounded-full bg-platform-500"
                                transition={{ duration: 0.5, delay: i * 0.05 }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {topology.load_percentages && Object.keys(topology.load_percentages).length > 0 && (
                    <div className="pt-3 border-t border-surface-border">
                      <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Load Percentages</p>
                      <div className="space-y-2">
                        {Object.entries(topology.load_percentages).map(([region, pct], i) => (
                          <div key={region}>
                            <div className="flex items-center justify-between text-xs font-mono mb-0.5">
                              <span className="text-slate-300">{region}</span>
                              <span className="text-slate-500">{typeof pct === 'number' ? Math.round(pct) : pct}%</span>
                            </div>
                            <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${typeof pct === 'number' ? pct : 0}%` }}
                                className={`h-full rounded-full ${(typeof pct === 'number' ? pct : 0) > 80 ? "bg-red-500" : (typeof pct === 'number' ? pct : 0) > 50 ? "bg-amber-500" : "bg-emerald-500"}`}
                                transition={{ duration: 0.5, delay: i * 0.05 }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </motion.div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Geo-Aware Routes */}
            <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Navigation className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">GEO_AWARE_ROUTES</h3>
              </div>
              {loadingRoutes ? (
                <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
              ) : routeList.length === 0 ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No route data</div>
              ) : (
                <div className="space-y-3">
                  {routeList.map((route, i) => (
                    <motion.div
                      key={route.workflow_type || i}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono text-slate-200 uppercase">{route.workflow_type.replace(/_/g, " ")}</span>
                        <span className="text-[10px] font-mono text-platform-400">{route.strategy}</span>
                      </div>
                      <div className="flex items-center gap-4 text-[10px] font-mono">
                        <span className="text-slate-500">Preferred: <span className="text-slate-300">{route.preferred_region}</span></span>
                        <span className="text-slate-500">Latency Threshold: <span className="text-slate-300">{route.latency_threshold_ms}ms</span></span>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>

            {/* Disaster Recovery Status */}
            <motion.div {...slideUp} transition={{ delay: 0.15 }} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <Shield className="w-5 h-5 text-amber-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">DISASTER_RECOVERY</h3>
              </div>
              {loadingDr ? (
                <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
              ) : drList.length === 0 ? (
                <div className="text-sm text-slate-500 font-mono py-8 text-center">No DR data</div>
              ) : (
                <div className="space-y-3">
                  {drList.map((dr, i) => (
                    <motion.div
                      key={dr.region || i}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                    >
                      <div className="flex items-center justify-between mb-3">
                        <span className="text-xs font-mono text-slate-200">{dr.region}</span>
                        <span className={`text-[10px] font-mono font-bold ${dr.dr_readiness >= 80 ? "text-emerald-400" : dr.dr_readiness >= 50 ? "text-amber-400" : "text-red-400"}`}>
                          {Math.round(dr.dr_readiness)}% READY
                        </span>
                      </div>
                      <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden mb-3">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${dr.dr_readiness}%` }}
                          className={`h-full rounded-full ${dr.dr_readiness >= 80 ? "bg-emerald-500" : dr.dr_readiness >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                      <div className="grid grid-cols-3 gap-2 text-[10px] font-mono">
                        <div className="p-2 rounded bg-surface-darker/30 border border-surface-border/30 text-center">
                          <span className="text-slate-500">RPO</span>
                          <p className="text-slate-200 font-bold">{dr.rpo_seconds}s</p>
                        </div>
                        <div className="p-2 rounded bg-surface-darker/30 border border-surface-border/30 text-center">
                          <span className="text-slate-500">RTO</span>
                          <p className="text-slate-200 font-bold">{dr.rto_seconds}s</p>
                        </div>
                        <div className="p-2 rounded bg-surface-darker/30 border border-surface-border/30 text-center">
                          <span className="text-slate-500">Last DR</span>
                          <p className="text-slate-200 font-bold text-[9px]">{new Date(dr.last_dr_test).toLocaleDateString()}</p>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}
            </motion.div>
          </div>
        </>
      )}
    </div>
  );
}
