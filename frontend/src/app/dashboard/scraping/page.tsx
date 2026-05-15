"use client";

import { motion } from "framer-motion";
import {
  Globe, Shield, AlertTriangle, Activity, Loader2, Cpu,
  Zap, Server, CheckCircle2, XCircle,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface AntiBotAssessment {
  overall_effectiveness: number;
  detection_rate: number;
  bypass_success_rate: number;
  recommended_actions: string[];
}

interface CaptchaAnalysis {
  current_rate: number;
  trend: "increasing" | "stable" | "decreasing";
  daily_rates: { date: string; rate: number }[];
  recommendations: string[];
}

interface IpBanStatus {
  pool_size: number;
  banned_count: number;
  health_percentage: number;
  rotation_frequency: string;
}

interface SelectorDegradation {
  selector: string;
  degradation_score: number;
  status: string;
  recommended_action: string;
}

interface SerpLayoutChange {
  detected_at: string;
  source: string;
  change_type: string;
  impact: string;
  migration_strategy: string;
}

interface BrowserCrashRecovery {
  crash_rate: number;
  total_crashes: number;
  auto_recovery_rate: number;
  recommendations: string[];
}

interface ScrapingOverload {
  current_concurrency: number;
  max_concurrency: number;
  overload_pct: number;
  recommendations: string[];
}

interface AdaptiveStrategy {
  strategy: string;
  status: string;
  effectiveness: number;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function ScrapingPage() {
  const { data: antiBot, isLoading: loading1 } = useQuery<AntiBotAssessment>({
    queryKey: ["scraping-anti-bot"],
    queryFn: () => fetchApi("/scraping-resilience/anti-bot"),
    refetchInterval: 15000,
  });

  const { data: captcha, isLoading: loading2 } = useQuery<CaptchaAnalysis>({
    queryKey: ["scraping-captcha"],
    queryFn: () => fetchApi("/scraping-resilience/captcha"),
    refetchInterval: 15000,
  });

  const { data: ipBan, isLoading: loading3 } = useQuery<IpBanStatus>({
    queryKey: ["scraping-ip-ban"],
    queryFn: () => fetchApi("/scraping-resilience/ip-ban-status"),
    refetchInterval: 15000,
  });

  const { data: selectors, isLoading: loading4 } = useQuery<SelectorDegradation[]>({
    queryKey: ["scraping-selector-degradation"],
    queryFn: () => fetchApi("/scraping-resilience/selector-degradation"),
    refetchInterval: 15000,
  });

  const { data: serpChanges, isLoading: loading5 } = useQuery<SerpLayoutChange[]>({
    queryKey: ["scraping-serp-layout"],
    queryFn: () => fetchApi("/scraping-resilience/serp-layout-changes"),
    refetchInterval: 15000,
  });

  const { data: browserHealth, isLoading: loading6 } = useQuery<BrowserCrashRecovery>({
    queryKey: ["scraping-browser-crash"],
    queryFn: () => fetchApi("/scraping-resilience/browser-crash-recovery"),
    refetchInterval: 15000,
  });

  const { data: overload, isLoading: loading7 } = useQuery<ScrapingOverload>({
    queryKey: ["scraping-overload"],
    queryFn: () => fetchApi("/scraping-resilience/overload"),
    refetchInterval: 15000,
  });

  const { data: strategies, isLoading: loading8 } = useQuery<AdaptiveStrategy[]>({
    queryKey: ["scraping-adaptive-strategies"],
    queryFn: () => fetchApi("/scraping-resilience/adaptive-strategies"),
    refetchInterval: 15000,
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">SCRAPING</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Scraping Resilience Dashboard</p>
        </div>
        {antiBot && (
          <span className={`px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 ${
            antiBot.overall_effectiveness >= 70 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
            antiBot.overall_effectiveness >= 40 ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
            "bg-red-500/10 text-red-400 border-red-500/20"
          }`}>
            <Shield className="w-4 h-4" />
            {Math.round(antiBot.overall_effectiveness)}% EFFECTIVE
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Anti-Bot Status */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Shield className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">ANTI_BOT_STATUS</h3>
          </div>
          {loading1 ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !antiBot ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No data</div>
          ) : (
            <div className="space-y-4">
              <div className="text-center">
                <span className={`text-4xl font-bold font-mono ${antiBot.overall_effectiveness >= 70 ? "text-emerald-400" : antiBot.overall_effectiveness >= 40 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(antiBot.overall_effectiveness)}%
                </span>
                <p className="text-xs font-mono text-slate-500 mt-1">Overall Effectiveness</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-slate-100">{Math.round(antiBot.detection_rate)}%</p>
                  <p className="text-[10px] font-mono text-slate-500">Detection Rate</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-slate-100">{Math.round(antiBot.bypass_success_rate)}%</p>
                  <p className="text-[10px] font-mono text-slate-500">Bypass Rate</p>
                </div>
              </div>
              {antiBot.recommended_actions.length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  <p className="text-[10px] font-mono text-amber-400 uppercase">Actions</p>
                  {antiBot.recommended_actions.map((a, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {a.replace(/_/g, " ")}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* CAPTCHA Monitor */}
        <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">CAPTCHA_MONITOR</h3>
          </div>
          {loading2 ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !captcha ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No data</div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-3xl font-bold font-mono text-slate-100">{captcha.current_rate.toFixed(1)}%</span>
                <span className={`px-2 py-0.5 rounded text-xs font-mono ${
                  captcha.trend === "increasing" ? "bg-red-500/10 text-red-400" :
                  captcha.trend === "decreasing" ? "bg-emerald-500/10 text-emerald-400" :
                  "bg-amber-500/10 text-amber-400"
                }`}>{captcha.trend.toUpperCase()}</span>
              </div>
              <p className="text-[10px] font-mono text-slate-500">Current CAPTCHA Rate</p>
              {captcha.daily_rates.length > 0 && (
                <div className="pt-3 border-t border-surface-border">
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Recent Trend</p>
                  <div className="flex items-end gap-1 h-16">
                    {captcha.daily_rates.slice(-7).map((d, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1">
                        <motion.div
                          initial={{ height: 0 }}
                          animate={{ height: `${d.rate}%` }}
                          className={`w-full rounded-t ${d.rate > 50 ? "bg-red-500" : d.rate > 25 ? "bg-amber-500" : "bg-emerald-500"}`}
                          style={{ maxHeight: "60px" }}
                          transition={{ duration: 0.3, delay: i * 0.05 }}
                        />
                        <span className="text-[7px] font-mono text-slate-600">{new Date(d.date).getDate()}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {captcha.recommendations.length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  {captcha.recommendations.map((r, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {r.replace(/_/g, " ")}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* IP Pool Health */}
        <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Globe className="w-5 h-5 text-cyan-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">IP_POOL_HEALTH</h3>
          </div>
          {loading3 ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !ipBan ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No data</div>
          ) : (
            <div className="space-y-4">
              <div className="text-center">
                <span className={`text-4xl font-bold font-mono ${ipBan.health_percentage >= 80 ? "text-emerald-400" : ipBan.health_percentage >= 50 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(ipBan.health_percentage)}%
                </span>
                <p className="text-xs font-mono text-slate-500 mt-1">Pool Health</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-emerald-400">{ipBan.pool_size}</p>
                  <p className="text-[10px] font-mono text-slate-500">Pool Size</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-red-400">{ipBan.banned_count}</p>
                  <p className="text-[10px] font-mono text-slate-500">Banned</p>
                </div>
              </div>
              <div className="w-full h-3 bg-surface-darker rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${ipBan.health_percentage}%` }}
                  className={`h-full rounded-full ${ipBan.health_percentage >= 80 ? "bg-emerald-500" : ipBan.health_percentage >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <p className="text-[10px] font-mono text-slate-500">Rotation: {ipBan.rotation_frequency}</p>
            </div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Selector Performance */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">SELECTOR_DEGRADATION</h3>
          </div>
          {loading4 ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !selectors || selectors.length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No selector degradation data</div>
          ) : (
            <div className="space-y-3">
              {selectors.map((s, i) => (
                <motion.div
                  key={s.selector || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300 truncate max-w-[200px]">{s.selector}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      s.degradation_score > 70 ? "bg-red-500/10 text-red-400" :
                      s.degradation_score > 40 ? "bg-amber-500/10 text-amber-400" :
                      "bg-emerald-500/10 text-emerald-400"
                    }`}>{Math.round(s.degradation_score)}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${s.degradation_score}%` }}
                      className={`h-full rounded-full ${s.degradation_score > 70 ? "bg-red-500" : s.degradation_score > 40 ? "bg-amber-500" : "bg-emerald-500"}`}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  {s.recommended_action && (
                    <p className="text-[10px] font-mono text-slate-500 mt-1">&gt; {s.recommended_action.replace(/_/g, " ")}</p>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* SERP Change Detection */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Zap className="w-5 h-5 text-purple-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">SERP_CHANGES</h3>
          </div>
          {loading5 ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !serpChanges || serpChanges.length === 0 ? (
            <div className="flex flex-col items-center py-8">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
              <span className="text-sm font-mono text-slate-500">NO_CHANGES_DETECTED</span>
            </div>
          ) : (
            <div className="space-y-3">
              {serpChanges.map((c, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                      c.impact === "high" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                      c.impact === "medium" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                      "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    }`}>{c.impact.toUpperCase()}</span>
                    <span className="text-[10px] font-mono text-slate-500">{c.source}</span>
                    <span className="text-[9px] font-mono text-slate-600 ml-auto">{new Date(c.detected_at).toLocaleDateString()}</span>
                  </div>
                  <p className="text-xs font-mono text-slate-300">{c.change_type.replace(/_/g, " ")}</p>
                  {c.migration_strategy && (
                    <p className="text-[10px] font-mono text-amber-400 mt-1">&gt; {c.migration_strategy.replace(/_/g, " ")}</p>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Browser Health */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Server className="w-5 h-5 text-red-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">BROWSER_HEALTH</h3>
          </div>
          {loading6 ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !browserHealth ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No data</div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-3">
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className={`text-lg font-bold font-mono ${browserHealth.crash_rate > 5 ? "text-red-400" : "text-emerald-400"}`}>
                    {browserHealth.crash_rate.toFixed(1)}%
                  </p>
                  <p className="text-[9px] font-mono text-slate-500">Crash Rate</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-slate-100">{browserHealth.total_crashes}</p>
                  <p className="text-[9px] font-mono text-slate-500">Crashes</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-emerald-400">{Math.round(browserHealth.auto_recovery_rate)}%</p>
                  <p className="text-[9px] font-mono text-slate-500">Recovery</p>
                </div>
              </div>
              {browserHealth.recommendations.length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  {browserHealth.recommendations.map((r, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {r.replace(/_/g, " ")}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* Overload Status */}
        <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Cpu className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">OVERLOAD_STATUS</h3>
          </div>
          {loading7 ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !overload ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No data</div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-3xl font-bold font-mono text-slate-100">{overload.current_concurrency}</span>
                <span className="text-sm font-mono text-slate-500">/ {overload.max_concurrency}</span>
              </div>
              <p className="text-[10px] font-mono text-slate-500">Current / Max Concurrency</p>
              <div className="w-full h-4 bg-surface-darker rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(overload.overload_pct, 100)}%` }}
                  className={`h-full rounded-full ${overload.overload_pct > 80 ? "bg-red-500" : overload.overload_pct > 50 ? "bg-amber-500" : "bg-emerald-500"}`}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <p className="text-[10px] font-mono text-slate-500">{Math.round(overload.overload_pct)}% loaded</p>
              {overload.recommendations.length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  {overload.recommendations.map((r, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {r.replace(/_/g, " ")}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* Adaptive Strategies */}
        <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">ADAPTIVE_STRATEGIES</h3>
          </div>
          {loading8 ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !strategies || strategies.length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No adaptive strategies</div>
          ) : (
            <div className="space-y-3">
              {strategies.map((s, i) => (
                <motion.div
                  key={s.strategy || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300 uppercase">{s.strategy.replace(/_/g, " ")}</span>
                    <span className={`w-2 h-2 rounded-full ${s.status === "active" ? "bg-emerald-500" : s.status === "standby" ? "bg-amber-500" : "bg-slate-500"}`} />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-slate-500">{s.status.toUpperCase()}</span>
                    <div className="flex-1 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${s.effectiveness}%` }}
                        className="h-full rounded-full bg-platform-500"
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-slate-500">{Math.round(s.effectiveness)}%</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
