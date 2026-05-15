"use client";

import { motion } from "framer-motion";
import {
  DollarSign, TrendingUp, BarChart3, PieChart, Loader2,
  Cpu, Zap, Activity, Shield,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface AICosts {
  total_cost: number;
  daily_estimate: number;
  model_breakdown: Record<string, number>;
}

interface QueueCosts {
  total_cost: number;
  daily_estimate: number;
  queue_breakdown: Record<string, number>;
}

interface ScrapingCosts {
  total_cost: number;
  daily_estimate: number;
  source_breakdown: Record<string, number>;
}

interface UtilizationEntry {
  component: string;
  current_utilization: number;
  peak_utilization: number;
  recommended: number;
}

interface WorkerEfficiency {
  efficiency_score: number;
  idle_percentage: number;
  utilization_percentage: number;
  worker_count: number;
}

interface EventThroughput {
  total_events: number;
  events_per_second: number;
  cost_per_event: number;
  estimated_daily_cost: number;
}

interface OperationalROI {
  roi_score: number;
  total_cost: number;
  total_value: number;
  cost_breakdown: Record<string, number>;
  value_breakdown: Record<string, number>;
}

interface OptimizationRecommendation {
  action: string;
  expected_savings: number;
  category: string;
  effort: string;
}

interface OptimizationIntelligence {
  recommendations: OptimizationRecommendation[];
}

const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.4 },
};

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

function CardSkeleton() {
  return (
    <div className="glass-panel p-5 animate-pulse">
      <div className="h-3 w-24 bg-surface-border rounded mb-3" />
      <div className="h-8 w-20 bg-surface-border rounded" />
      <div className="h-3 w-32 bg-surface-border rounded mt-2" />
    </div>
  );
}

function formatCurrency(n: number): string {
  return `$${n.toFixed(2)}`;
}

export default function EconomicsPage() {
  const { data: aiCosts, isLoading: loadingAi } = useQuery<AICosts>({
    queryKey: ["infra-economics-ai-costs"],
    queryFn: () => fetchApi("/infra-economics/ai-costs"),
    refetchInterval: 15000,
  });

  const { data: queueCosts, isLoading: loadingQueue } = useQuery<QueueCosts>({
    queryKey: ["infra-economics-queue-costs"],
    queryFn: () => fetchApi("/infra-economics/queue-costs"),
    refetchInterval: 15000,
  });

  const { data: scrapingCosts, isLoading: loadingScraping } = useQuery<ScrapingCosts>({
    queryKey: ["infra-economics-scraping-costs"],
    queryFn: () => fetchApi("/infra-economics/scraping-costs"),
    refetchInterval: 15000,
  });

  const { data: utilization, isLoading: loadingUtil } = useQuery<UtilizationEntry[]>({
    queryKey: ["infra-economics-utilization"],
    queryFn: () => fetchApi("/infra-economics/utilization"),
    refetchInterval: 15000,
  });

  const { data: efficiency, isLoading: loadingEff } = useQuery<WorkerEfficiency>({
    queryKey: ["infra-economics-worker-efficiency"],
    queryFn: () => fetchApi("/infra-economics/worker-efficiency"),
    refetchInterval: 15000,
  });

  const { data: throughput, isLoading: loadingThroughput } = useQuery<EventThroughput>({
    queryKey: ["infra-economics-event-throughput"],
    queryFn: () => fetchApi("/infra-economics/event-throughput"),
    refetchInterval: 15000,
  });

  const { data: roi, isLoading: loadingRoi } = useQuery<OperationalROI>({
    queryKey: ["infra-economics-roi"],
    queryFn: () => fetchApi("/infra-economics/roi"),
    refetchInterval: 15000,
  });

  const { data: optimization, isLoading: loadingOpt } = useQuery<OptimizationIntelligence>({
    queryKey: ["infra-economics-optimization"],
    queryFn: () => fetchApi("/infra-economics/optimization-intelligence"),
    refetchInterval: 15000,
  });

  const recommendations = optimization?.recommendations || [];
  const utilList = utilization || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">ECONOMICS</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Infrastructure Economics Dashboard</p>
        </div>
        {roi && (
          <div className="px-3 py-1.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-xs font-mono text-emerald-400 flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            ROI: {roi.roi_score.toFixed(1)}x
          </div>
        )}
      </div>

      {/* Cost Overview */}
      <motion.div {...slideUp}>
        <h2 className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">Cost Overview</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {loadingAi ? <CardSkeleton /> : (
            <div className="glass-panel p-5">
              <div className="flex items-center gap-2 mb-2">
                <Cpu className="w-4 h-4 text-purple-400" />
                <span className="text-[10px] font-mono text-slate-500 uppercase">AI Costs</span>
              </div>
              <span className="text-2xl font-bold font-mono text-slate-100">{aiCosts ? formatCurrency(aiCosts.total_cost) : "—"}</span>
              <p className="text-[10px] font-mono text-slate-600 mt-1">~{aiCosts ? formatCurrency(aiCosts.daily_estimate) : "—"}/day</p>
              {aiCosts?.model_breakdown && (
                <div className="mt-3 pt-3 border-t border-surface-border space-y-1">
                  {Object.entries(aiCosts.model_breakdown).map(([model, cost]) => (
                    <div key={model} className="flex justify-between text-[10px] font-mono text-slate-500">
                      <span>{model}</span>
                      <span>{formatCurrency(cost)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {loadingQueue ? <CardSkeleton /> : (
            <div className="glass-panel p-5">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="w-4 h-4 text-amber-400" />
                <span className="text-[10px] font-mono text-slate-500 uppercase">Queue Costs</span>
              </div>
              <span className="text-2xl font-bold font-mono text-slate-100">{queueCosts ? formatCurrency(queueCosts.total_cost) : "—"}</span>
              <p className="text-[10px] font-mono text-slate-600 mt-1">~{queueCosts ? formatCurrency(queueCosts.daily_estimate) : "—"}/day</p>
              {queueCosts?.queue_breakdown && (
                <div className="mt-3 pt-3 border-t border-surface-border space-y-1">
                  {Object.entries(queueCosts.queue_breakdown).map(([q, cost]) => (
                    <div key={q} className="flex justify-between text-[10px] font-mono text-slate-500">
                      <span>{q}</span>
                      <span>{formatCurrency(cost)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {loadingScraping ? <CardSkeleton /> : (
            <div className="glass-panel p-5">
              <div className="flex items-center gap-2 mb-2">
                <Zap className="w-4 h-4 text-cyan-400" />
                <span className="text-[10px] font-mono text-slate-500 uppercase">Scraping Costs</span>
              </div>
              <span className="text-2xl font-bold font-mono text-slate-100">{scrapingCosts ? formatCurrency(scrapingCosts.total_cost) : "—"}</span>
              <p className="text-[10px] font-mono text-slate-600 mt-1">~{scrapingCosts ? formatCurrency(scrapingCosts.daily_estimate) : "—"}/day</p>
              {scrapingCosts?.source_breakdown && (
                <div className="mt-3 pt-3 border-t border-surface-border space-y-1">
                  {Object.entries(scrapingCosts.source_breakdown).map(([src, cost]) => (
                    <div key={src} className="flex justify-between text-[10px] font-mono text-slate-500">
                      <span>{src}</span>
                      <span>{formatCurrency(cost)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Resource Utilization */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <BarChart3 className="w-5 h-5 text-emerald-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">RESOURCE_UTILIZATION</h3>
          </div>
          {loadingUtil ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : utilList.length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No utilization data</div>
          ) : (
            <div className="space-y-4">
              {utilList.map((u, i) => (
                <div key={u.component || i}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300 uppercase">{u.component}</span>
                    <span className="text-[10px] font-mono text-slate-500">
                      {Math.round(u.current_utilization)}% / peak {Math.round(u.peak_utilization)}%
                    </span>
                  </div>
                  <div className="w-full h-3 bg-surface-darker rounded-full overflow-hidden relative">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.min(u.current_utilization, 100)}%` }}
                      className={`h-full rounded-full ${u.current_utilization > 80 ? "bg-red-500" : u.current_utilization > 50 ? "bg-amber-500" : "bg-emerald-500"}`}
                      transition={{ duration: 0.5, delay: i * 0.05 }}
                    />
                    {u.peak_utilization > 0 && (
                      <div className="absolute top-0 h-full w-0.5 bg-white/30" style={{ left: `${Math.min(u.peak_utilization, 100)}%` }} />
                    )}
                  </div>
                  <div className="flex justify-between text-[10px] font-mono text-slate-600 mt-0.5">
                    <span>Recommended: {Math.round(u.recommended)}%</span>
                    <span className={u.current_utilization > u.recommended * 1.2 ? "text-red-400" : "text-emerald-400"}>
                      {u.current_utilization > u.recommended * 1.2 ? "OVER" : "OK"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Worker Efficiency */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">WORKER_EFFICIENCY</h3>
          </div>
          {loadingEff ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !efficiency ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No efficiency data</div>
          ) : (
            <div className="space-y-6">
              <div className="text-center">
                <span className={`text-5xl font-bold font-mono ${efficiency.efficiency_score >= 80 ? "text-emerald-400" : efficiency.efficiency_score >= 50 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(efficiency.efficiency_score)}%
                </span>
                <p className="text-xs font-mono text-slate-500 mt-1">Efficiency Score</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <span className="text-2xl font-bold font-mono text-slate-100">{Math.round(efficiency.utilization_percentage)}%</span>
                  <p className="text-[10px] font-mono text-slate-500 mt-1">Utilization</p>
                </div>
                <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <span className="text-2xl font-bold font-mono text-slate-100">{Math.round(efficiency.idle_percentage)}%</span>
                  <p className="text-[10px] font-mono text-slate-500 mt-1">Idle</p>
                </div>
              </div>
              <div className="flex items-center justify-between text-xs font-mono text-slate-500">
                <span>Workers</span>
                <span className="text-slate-300">{efficiency.worker_count}</span>
              </div>
            </div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Event Economics */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-indigo-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">EVENT_ECONOMICS</h3>
          </div>
          {loadingThroughput ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !throughput ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No throughput data</div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Total Events</p>
                <p className="text-xl font-bold font-mono text-slate-100">{throughput.total_events.toLocaleString()}</p>
              </div>
              <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Events/sec</p>
                <p className="text-xl font-bold font-mono text-slate-100">{throughput.events_per_second.toFixed(1)}</p>
              </div>
              <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Cost/Event</p>
                <p className="text-xl font-bold font-mono text-slate-100">{formatCurrency(throughput.cost_per_event)}</p>
              </div>
              <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50">
                <p className="text-[10px] font-mono text-slate-500 uppercase">Daily Est.</p>
                <p className="text-xl font-bold font-mono text-slate-100">{formatCurrency(throughput.estimated_daily_cost)}</p>
              </div>
            </div>
          )}
        </motion.div>

        {/* Operational ROI */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-emerald-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">OPERATIONAL_ROI</h3>
            {roi && (
              <span className={`ml-auto text-lg font-bold font-mono ${roi.roi_score >= 2 ? "text-emerald-400" : roi.roi_score >= 1 ? "text-amber-400" : "text-red-400"}`}>
                {roi.roi_score.toFixed(1)}x
              </span>
            )}
          </div>
          {loadingRoi ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !roi ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No ROI data</div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Total Cost</p>
                  <p className="text-xl font-bold font-mono text-red-400">{formatCurrency(roi.total_cost)}</p>
                </div>
                <div className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Total Value</p>
                  <p className="text-xl font-bold font-mono text-emerald-400">{formatCurrency(roi.total_value)}</p>
                </div>
              </div>
              <div className="w-full h-3 bg-surface-darker rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min((roi.total_value / Math.max(roi.total_cost, 1)) * 50, 100)}%` }}
                  className="h-full rounded-full bg-emerald-500"
                  transition={{ duration: 0.5 }}
                />
              </div>
              {roi.cost_breakdown && Object.keys(roi.cost_breakdown).length > 0 && (
                <div className="pt-3 border-t border-surface-border">
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Cost Breakdown</p>
                  {Object.entries(roi.cost_breakdown).map(([k, v]) => (
                    <div key={k} className="flex justify-between text-[10px] font-mono text-slate-500">
                      <span>{k.replace(/_/g, " ")}</span>
                      <span>{formatCurrency(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>
      </div>

      {/* Optimization Recommendations */}
      <motion.div {...slideUp} className="glass-panel p-6">
        <div className="flex items-center gap-2 mb-4">
          <PieChart className="w-5 h-5 text-platform-500" />
          <h3 className="text-lg font-medium text-slate-200 font-mono">OPTIMIZATION_RECOMMENDATIONS</h3>
        </div>
        {loadingOpt ? (
          <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
        ) : recommendations.length === 0 ? (
          <div className="flex flex-col items-center py-8">
            <Shield className="w-8 h-8 text-emerald-500 mb-2" />
            <span className="text-sm font-mono text-slate-500">NO_OPTIMIZATIONS_AVAILABLE</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {recommendations.map((r, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
              >
                <div className="flex items-center gap-2 mb-2">
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-bold ${
                    r.effort === "low" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                    r.effort === "medium" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                    "bg-red-500/10 text-red-400 border-red-500/20"
                  }`}>{r.effort.toUpperCase()}</span>
                  <span className="text-[10px] font-mono text-slate-500">{r.category}</span>
                </div>
                <p className="text-xs font-mono text-slate-300 mb-2">{r.action.replace(/_/g, " ")}</p>
                <p className="text-[10px] font-mono text-emerald-400">Save {formatCurrency(r.expected_savings)}</p>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
