"use client";

import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import {
  GitBranch, TrendingUp, TrendingDown, Activity,
  Target, Link2, Mail, Users, Loader2,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import type { CampaignIntelligence } from "@/types/business-intelligence";

function getHealthColor(score: number): string {
  if (score >= 0.8) return "text-emerald-400";
  if (score >= 0.6) return "text-amber-400";
  if (score >= 0.4) return "text-orange-400";
  return "text-red-400";
}

function getHealthBarColor(score: number): string {
  if (score >= 0.8) return "bg-emerald-500";
  if (score >= 0.6) return "bg-amber-500";
  if (score >= 0.5) return "bg-orange-500";
  return "bg-red-500";
}

function getMomentumIcon(momentum: number) {
  if (momentum > 0.05) return <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />;
  if (momentum > 0.01) return <TrendingUp className="w-3 h-3 text-emerald-400" />;
  if (momentum < -0.05) return <TrendingDown className="w-3.5 h-3.5 text-red-400" />;
  if (momentum < -0.01) return <TrendingDown className="w-3 h-3 text-red-400" />;
  return <Activity className="w-3 h-3 text-slate-500" />;
}

function getMomentumLabel(momentum: number): string {
  if (momentum > 0.1) return "accelerating";
  if (momentum > 0.03) return "improving";
  if (momentum > 0.01) return "rising";
  if (momentum > -0.01) return "stable";
  if (momentum > -0.03) return "easing";
  if (momentum > -0.1) return "declining";
  return "critical";
}

function TrendSparkline({ trends, color }: { trends: number[]; color: string }) {
  if (trends.length < 2) return null;
  const max = Math.max(...trends, 0.01);
  const min = Math.min(...trends, 0);
  const range = max - min || 1;
  const w = 64;
  const h = 24;
  const pts = trends.map((v, i) => {
    const x = (i / (trends.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 4) - 2;
    return `${x},${y}`;
  });
  return (
    <svg width={w} height={h} className="flex-shrink-0">
      <path d={`M${pts.join(" L")}`} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
      <defs>
        <linearGradient id={`glow-${color.replace("#", "")}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.3" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={`M${pts.join(" L")} L${pts[pts.length - 1].split(",")[0]},24 L${pts[0].split(",")[0]},24 Z`}
        fill={`url(#glow-${color.replace("#", "")})`} opacity="0.15" />
    </svg>
  );
}

function SignalBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[8px] font-mono text-slate-600 w-14 text-right">{label}</span>
      <div className="flex-1 h-1 bg-surface-darker rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
          className={`h-full rounded-full ${color}`}
        />
      </div>
      <span className={`text-[8px] font-mono font-bold w-6 text-right ${color.replace("bg-", "text-")}`}>
        {pct}
      </span>
    </div>
  );
}

export function CampaignEvolutionPanel() {
  const [campaigns, setCampaigns] = useState<CampaignIntelligence[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await fetchApi<any>("/business-intelligence/intelligence/campaigns");
        if (data?.campaigns) setCampaigns(data.campaigns);
      } catch {} finally {
        setLoading(false);
      }
    };
    fetch();
    const interval = setInterval(fetch, 10000);
    return () => clearInterval(interval);
  }, []);

  const sorted = useMemo(() =>
    [...campaigns].sort((a, b) => b.health_score - a.health_score),
    [campaigns],
  );

  if (loading) {
    return (
      <div className="glass-panel p-6 flex items-center justify-center min-h-[200px]">
        <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
      </div>
    );
  }

  if (sorted.length === 0) {
    return (
      <div className="glass-panel p-6 text-center">
        <GitBranch className="w-8 h-8 text-slate-700 mx-auto mb-2" />
        <p className="text-xs font-mono text-slate-600">No campaigns with evolution data</p>
      </div>
    );
  }

  return (
    <div className="glass-panel overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border bg-surface-darker/50">
        <div className="flex items-center gap-2">
          <GitBranch className="w-4 h-4 text-platform-400" />
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase tracking-wider">
            Campaign Evolution
          </h3>
          <span className="text-[9px] font-mono text-slate-600">
            {sorted.length} campaigns · 5-signal health
          </span>
        </div>
        <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[9px] font-mono text-emerald-400">EVOLVING</span>
        </span>
      </div>
      <div className="divide-y divide-surface-border">
        {sorted.map((campaign, i) => {
          const latest = campaign.trends?.[0];
          const momentum = latest?.momentum ?? 0;
          const velocity = latest?.velocity ?? 0;
          const trendScores = campaign.trends?.map((t) => t.health_score).reverse() ?? [];
          const healthPct = Math.round(campaign.health_score * 100);
          const progressPct = Math.round(campaign.progress * 100);
          const isExpanded = expanded === campaign.id;

          return (
            <div key={campaign.id}>
              <motion.div
                initial={{ opacity: 0, x: -5 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.03 }}
                onClick={() => setExpanded(isExpanded ? null : campaign.id)}
                className="px-4 py-3 hover:bg-surface-border/30 transition-colors cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-sm font-mono text-slate-200 font-medium truncate">
                        {campaign.name}
                      </span>
                      <span className="text-[9px] font-mono text-slate-500 uppercase">
                        {campaign.campaign_type.replace("_", " ")}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 max-w-[220px]">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-2 bg-surface-darker rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${healthPct}%` }}
                              transition={{ duration: 0.8, delay: i * 0.05, ease: "easeOut" }}
                              className={`h-full rounded-full ${getHealthBarColor(campaign.health_score)}`}
                            />
                          </div>
                          <motion.span
                            key={healthPct}
                            initial={{ scale: 1.2 }}
                            animate={{ scale: 1 }}
                            className={`text-sm font-mono font-bold ${getHealthColor(campaign.health_score)}`}
                          >
                            {healthPct}%
                          </motion.span>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 text-[9px] font-mono">
                        <span className="flex items-center gap-1 text-slate-500">
                          <Link2 className="w-2.5 h-2.5" />
                          {campaign.acquired_link_count}/{campaign.target_link_count}
                        </span>
                        <span className="flex items-center gap-1 text-slate-500">
                          <Target className="w-2.5 h-2.5" />
                          {progressPct}%
                        </span>
                      </div>
                    </div>
                  </div>

                  {trendScores.length >= 2 && (
                    <div className="flex-shrink-0">
                      <TrendSparkline trends={trendScores.slice(-12)} color="#2dd4bf" />
                    </div>
                  )}

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <motion.div
                      animate={Math.abs(momentum) > 0.01 ? { scale: [1, 1.1, 1] } : {}}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="flex items-center gap-1 text-[9px] font-mono"
                    >
                      {getMomentumIcon(momentum)}
                      <span className={
                        momentum > 0.01 ? "text-emerald-500" :
                        momentum < -0.01 ? "text-red-400" :
                        "text-slate-500"
                      }>
                        {getMomentumLabel(momentum)}
                      </span>
                    </motion.div>
                    {velocity > 0 && (
                      <div className="flex items-center gap-1 text-[9px] font-mono text-slate-500">
                        <Activity className="w-2.5 h-2.5" />
                        {velocity.toFixed(1)}
                      </div>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-[9px] font-mono text-slate-600 flex-shrink-0">
                    <span className="flex items-center gap-1" title="Emails sent">
                      <Mail className="w-2.5 h-2.5" />
                      {campaign.total_emails_sent}
                    </span>
                    <span className="flex items-center gap-1" title="Total prospects">
                      <Users className="w-2.5 h-2.5" />
                      {campaign.total_prospects}
                    </span>
                  </div>
                </div>
              </motion.div>

              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  className="px-4 pb-3 bg-surface-darker/30 border-t border-surface-border/50"
                >
                  <div className="grid grid-cols-2 gap-4 pt-3">
                    <div>
                      <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-2">Health Components</p>
                      <div className="space-y-1">
                        <SignalBar label="outreach" value={latest?.snapshot_data?.outreach_health ?? 0.3} color="bg-platform-500" />
                        <SignalBar label="freshness" value={latest?.snapshot_data?.freshness_health ?? 0.5} color="bg-emerald-500" />
                        <SignalBar label="keywords" value={latest?.snapshot_data?.keyword_health ?? 0.4} color="bg-indigo-500" />
                        <SignalBar label="operations" value={latest?.snapshot_data?.operational_health ?? 0.3} color="bg-amber-500" />
                        <SignalBar label="seo" value={latest?.snapshot_data?.seo_health ?? 0.3} color="bg-purple-500" />
                      </div>
                    </div>
                    <div>
                      <p className="text-[9px] font-mono text-slate-500 uppercase tracking-wider mb-2">Trend Data</p>
                      {latest && (
                        <div className="space-y-1 text-[10px] font-mono">
                          <div className="flex justify-between">
                            <span className="text-slate-500">health</span>
                            <span className={getHealthColor(campaign.health_score)}>
                              {Math.round(campaign.health_score * 100)}%
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">momentum</span>
                            <span className={momentum > 0 ? "text-emerald-400" : "text-red-400"}>
                              {momentum.toFixed(4)}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">velocity</span>
                            <span className="text-platform-400">{velocity.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">acq rate</span>
                            <span className="text-slate-300">{(campaign.acquisition_rate * 100).toFixed(1)}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">reply rate</span>
                            <span className="text-slate-300">{(campaign.reply_rate * 100).toFixed(1)}%</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">acquired</span>
                            <span className="text-emerald-400">{campaign.acquired_link_count}</span>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="mt-3 pt-2 border-t border-surface-border/50 flex items-center gap-3 text-[9px] font-mono text-slate-600">
                    <span>created {campaign.created_at ? new Date(campaign.created_at).toLocaleDateString() : "—"}</span>
                    <span>updated {campaign.updated_at ? new Date(campaign.updated_at).toLocaleTimeString() : "—"}</span>
                    <span className="ml-auto text-platform-500">click to collapse</span>
                  </div>
                </motion.div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
