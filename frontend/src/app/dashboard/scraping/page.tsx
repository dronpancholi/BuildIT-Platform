"use client";

import { motion } from "framer-motion";
import {
  Globe, Shield, AlertTriangle, Activity, Loader2, Cpu,
  Zap, Server, CheckCircle2, XCircle,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { safeArr, safeStr, safeUpper, safeFixed, safeNum, safeReplace } from "@/lib/safe";

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
            safeNum(antiBot?.overall_effectiveness) >= 70 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
            safeNum(antiBot?.overall_effectiveness) >= 40 ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
            "bg-red-500/10 text-red-400 border-red-500/20"
          }`}>
            <Shield className="w-4 h-4" />
            {Math.round(safeNum(antiBot?.overall_effectiveness))}% EFFECTIVE
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
                <span className={`text-4xl font-bold font-mono ${safeNum(antiBot?.overall_effectiveness) >= 70 ? "text-emerald-400" : safeNum(antiBot?.overall_effectiveness) >= 40 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(safeNum(antiBot?.overall_effectiveness))}%
                </span>
                <p className="text-xs font-mono text-slate-500 mt-1">Overall Effectiveness</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-slate-100">{Math.round(safeNum(antiBot?.detection_rate))}%</p>
                  <p className="text-[10px] font-mono text-slate-500">Detection Rate</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-slate-100">{Math.round(safeNum(antiBot?.bypass_success_rate))}%</p>
                  <p className="text-[10px] font-mono text-slate-500">Bypass Rate</p>
                </div>
              </div>
              {safeArr(antiBot?.recommended_actions).length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  <p className="text-[10px] font-mono text-amber-400 uppercase">Actions</p>
                  {safeArr<string>(antiBot?.recommended_actions).map((a, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {safeStr(a).replace(/_/g, " ")}</p>
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
                <span className="text-3xl font-bold font-mono text-slate-100">{safeFixed(captcha?.current_rate, 1)}%</span>
                <span className={`px-2 py-0.5 rounded text-xs font-mono ${
                  captcha?.trend === "increasing" ? "bg-red-500/10 text-red-400" :
                  captcha?.trend === "decreasing" ? "bg-emerald-500/10 text-emerald-400" :
                  "bg-amber-500/10 text-amber-400"
                }`}>{safeUpper(captcha?.trend, "STABLE")}</span>
              </div>
              <p className="text-[10px] font-mono text-slate-500">Current CAPTCHA Rate</p>
              {safeArr(captcha?.daily_rates).length > 0 && (
                <div className="pt-3 border-t border-surface-border">
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Recent Trend</p>
                  <div className="flex items-end gap-1 h-16">
                    {safeArr<{ date: string; rate: number }>(captcha?.daily_rates).slice(-7).map((d, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center gap-1">
                        <motion.div
                          initial={{ height: 0 }}
                          animate={{ height: `${safeNum(d?.rate)}%` }}
                          className={`w-full rounded-t ${safeNum(d?.rate) > 50 ? "bg-red-500" : safeNum(d?.rate) > 25 ? "bg-amber-500" : "bg-emerald-500"}`}
                          style={{ maxHeight: "60px" }}
                          transition={{ duration: 0.3, delay: i * 0.05 }}
                        />
                        <span className="text-[7px] font-mono text-slate-600">{safeStr(d?.date) ? new Date(d.date).getDate() : "—"}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {safeArr(captcha?.recommendations).length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  {safeArr<string>(captcha?.recommendations).map((r, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {safeStr(r).replace(/_/g, " ")}</p>
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
                <span className={`text-4xl font-bold font-mono ${safeNum(ipBan?.health_percentage) >= 80 ? "text-emerald-400" : safeNum(ipBan?.health_percentage) >= 50 ? "text-amber-400" : "text-red-400"}`}>
                  {Math.round(safeNum(ipBan?.health_percentage))}%
                </span>
                <p className="text-xs font-mono text-slate-500 mt-1">Pool Health</p>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-emerald-400">{safeNum(ipBan?.pool_size)}</p>
                  <p className="text-[10px] font-mono text-slate-500">Pool Size</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-red-400">{safeNum(ipBan?.banned_count)}</p>
                  <p className="text-[10px] font-mono text-slate-500">Banned</p>
                </div>
              </div>
              <div className="w-full h-3 bg-surface-darker rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${safeNum(ipBan?.health_percentage)}%` }}
                  className={`h-full rounded-full ${safeNum(ipBan?.health_percentage) >= 80 ? "bg-emerald-500" : safeNum(ipBan?.health_percentage) >= 50 ? "bg-amber-500" : "bg-red-500"}`}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <p className="text-[10px] font-mono text-slate-500">Rotation: {safeStr(ipBan?.rotation_frequency)}</p>
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
          ) : safeArr(selectors).length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No selector degradation data</div>
          ) : (
            <div className="space-y-3">
              {safeArr<{ selector: string; degradation_score: number; recommended_action: string }>(selectors).map((s, i) => (
                <motion.div
                  key={s.selector || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300 truncate max-w-[200px]">{safeStr(s.selector)}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      safeNum(s.degradation_score) > 70 ? "bg-red-500/10 text-red-400" :
                      safeNum(s.degradation_score) > 40 ? "bg-amber-500/10 text-amber-400" :
                      "bg-emerald-500/10 text-emerald-400"
                    }`}>{Math.round(safeNum(s.degradation_score))}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${safeNum(s.degradation_score)}%` }}
                      className={`h-full rounded-full ${safeNum(s.degradation_score) > 70 ? "bg-red-500" : safeNum(s.degradation_score) > 40 ? "bg-amber-500" : "bg-emerald-500"}`}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  {s.recommended_action && (
                    <p className="text-[10px] font-mono text-slate-500 mt-1">&gt; {safeReplace(s.recommended_action, /_/g, " ")}</p>
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
          ) : safeArr(serpChanges).length === 0 ? (
            <div className="flex flex-col items-center py-8">
              <CheckCircle2 className="w-8 h-8 text-emerald-500 mb-2" />
              <span className="text-sm font-mono text-slate-500">NO_CHANGES_DETECTED</span>
            </div>
          ) : (
            <div className="space-y-3">
              {safeArr<{ impact: string; source: string; detected_at: string; change_type: string; migration_strategy: string }>(serpChanges).map((c, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                      c?.impact === "high" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                      c?.impact === "medium" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                      "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    }`}>{safeUpper(c?.impact, "UNKNOWN")}</span>
                    <span className="text-[10px] font-mono text-slate-500">{safeStr(c?.source)}</span>
                    <span className="text-[9px] font-mono text-slate-600 ml-auto">{safeStr(c?.detected_at) ? new Date(c.detected_at).toLocaleDateString() : "—"}</span>
                  </div>
                  <p className="text-xs font-mono text-slate-300">{safeReplace(c?.change_type, /_/g, " ")}</p>
                  {c.migration_strategy && (
                    <p className="text-[10px] font-mono text-amber-400 mt-1">&gt; {safeReplace(c.migration_strategy, /_/g, " ")}</p>
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
                  <p className={`text-lg font-bold font-mono ${safeNum(browserHealth?.crash_rate) > 5 ? "text-red-400" : "text-emerald-400"}`}>
                    {safeFixed(browserHealth?.crash_rate, 1)}%
                  </p>
                  <p className="text-[9px] font-mono text-slate-500">Crash Rate</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-slate-100">{safeNum(browserHealth?.total_crashes)}</p>
                  <p className="text-[9px] font-mono text-slate-500">Crashes</p>
                </div>
                <div className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50 text-center">
                  <p className="text-lg font-bold font-mono text-emerald-400">{Math.round(safeNum(browserHealth?.auto_recovery_rate))}%</p>
                  <p className="text-[9px] font-mono text-slate-500">Recovery</p>
                </div>
              </div>
              {safeArr(browserHealth?.recommendations).length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  {safeArr<string>(browserHealth?.recommendations).map((r, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {safeStr(r).replace(/_/g, " ")}</p>
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
                <span className="text-3xl font-bold font-mono text-slate-100">{safeNum(overload?.current_concurrency)}</span>
                <span className="text-sm font-mono text-slate-500">/ {safeNum(overload?.max_concurrency)}</span>
              </div>
              <p className="text-[10px] font-mono text-slate-500">Current / Max Concurrency</p>
              <div className="w-full h-4 bg-surface-darker rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(safeNum(overload?.overload_pct), 100)}%` }}
                  className={`h-full rounded-full ${safeNum(overload?.overload_pct) > 80 ? "bg-red-500" : safeNum(overload?.overload_pct) > 50 ? "bg-amber-500" : "bg-emerald-500"}`}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <p className="text-[10px] font-mono text-slate-500">{Math.round(safeNum(overload?.overload_pct))}% loaded</p>
              {safeArr(overload?.recommendations).length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  {safeArr<string>(overload?.recommendations).map((r, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {safeStr(r).replace(/_/g, " ")}</p>
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
          ) : safeArr(strategies).length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No adaptive strategies</div>
          ) : (
            <div className="space-y-3">
              {safeArr<{ strategy: string; status: string; effectiveness: number }>(strategies).map((s, i) => (
                <motion.div
                  key={s.strategy || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300 uppercase">{safeReplace(s.strategy, /_/g, " ")}</span>
                    <span className={`w-2 h-2 rounded-full ${s?.status === "active" ? "bg-emerald-500" : s?.status === "standby" ? "bg-amber-500" : "bg-slate-500"}`} />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-slate-500">{safeUpper(s?.status)}</span>
                    <div className="flex-1 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${safeNum(s.effectiveness)}%` }}
                        className="h-full rounded-full bg-platform-500"
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                    <span className="text-[10px] font-mono text-slate-500">{Math.round(safeNum(s.effectiveness))}%</span>
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
