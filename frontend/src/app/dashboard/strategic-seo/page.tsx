"use client";

import { motion } from "framer-motion";
import {
  Search, BrainCircuit, TrendingUp, Link2, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface SEOStrategyArea {
  area: string;
  current_state: string;
  recommendation: string;
}

interface SEOStrategy {
  strategy_areas: SEOStrategyArea[];
}

interface MarketSegment {
  segment: string;
  competitive_density: number;
  trending_topics: string[];
}

interface MarketIntelligence {
  market_segments: MarketSegment[];
}

interface SERPTrend {
  keyword: string;
  current_position: number;
  predicted_position: number;
  trend_direction: string;
}

interface BacklinkOpportunity {
  domain: string;
  authority: number;
  relevance: number;
  difficulty: number;
}

interface BacklinkMap {
  opportunities: BacklinkOpportunity[];
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function StrategicSEOPage() {
  const { data: strategy, isLoading: loadingStrategy } = useQuery<SEOStrategy>({
    queryKey: ["seo-strategy"],
    queryFn: () => fetchApi(`/strategic-seo/operational-seo-strategy?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  const { data: marketIntel, isLoading: loadingMarket } = useQuery<MarketIntelligence>({
    queryKey: ["seo-market-intel"],
    queryFn: () => fetchApi("/strategic-seo/semantic-market-intelligence", { method: "POST", body: JSON.stringify({ tenant_id: MOCK_TENANT_ID }) }),
    refetchInterval: 15000,
  });

  const { data: serpTrends, isLoading: loadingSERP } = useQuery<SERPTrend[]>({
    queryKey: ["seo-serp-trends"],
    queryFn: () => fetchApi(`/strategic-seo/serp-trend-forecast?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  const { data: backlinkMap, isLoading: loadingBacklinks } = useQuery<BacklinkMap>({
    queryKey: ["seo-backlink-map"],
    queryFn: () => fetchApi("/strategic-seo/strategic-backlink-map", { method: "POST", body: JSON.stringify({ tenant_id: MOCK_TENANT_ID }) }),
    refetchInterval: 15000,
  });

  const areas = strategy?.strategy_areas || [];
  const segments = marketIntel?.market_segments || [];
  const serpList = serpTrends || [];
  const opportunities = backlinkMap?.opportunities || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">STRATEGIC_SEO</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Strategic SEO & Backlink Cognition Dashboard</p>
        </div>
        <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 flex items-center gap-2">
          <Search className="w-4 h-4" />
          {areas.length} STRATEGY AREAS
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SEO Strategy Overview */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Search className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">SEO_STRATEGY_OVERVIEW</h3>
          </div>
          {loadingStrategy ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : areas.length === 0 ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No strategy data</div>
          ) : (
            <div className="space-y-3">
              {areas.map((a, i) => (
                <motion.div
                  key={a.area || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-slate-200 uppercase">{a.area.replace(/_/g, " ")}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${
                      a.current_state === "optimal" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                      a.current_state === "needs_attention" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                      "bg-red-500/10 text-red-400 border-red-500/20"
                    }`}>{a.current_state.replace(/_/g, " ").toUpperCase()}</span>
                  </div>
                  <p className="text-[10px] font-mono text-slate-400">&gt; {a.recommendation}</p>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Semantic Market Intelligence */}
        <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <BrainCircuit className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">SEMANTIC_MARKET_INTELLIGENCE</h3>
          </div>
          {loadingMarket ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : segments.length === 0 ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No market intelligence data</div>
          ) : (
            <div className="space-y-3">
              {segments.map((s, i) => (
                <motion.div
                  key={s.segment || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-slate-200 uppercase">{s.segment.replace(/_/g, " ")}</span>
                    <span className={`text-[10px] font-mono font-bold ${s.competitive_density >= 70 ? "text-red-400" : s.competitive_density >= 40 ? "text-amber-400" : "text-emerald-400"}`}>
                      Density: {Math.round(s.competitive_density)}%
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden mb-2">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${s.competitive_density}%` }}
                      className={`h-full rounded-full ${s.competitive_density >= 70 ? "bg-red-500" : s.competitive_density >= 40 ? "bg-amber-500" : "bg-emerald-500"}`}
                      transition={{ duration: 0.5 }}
                    />
                  </div>
                  {s.trending_topics.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {s.trending_topics.map((topic, j) => (
                        <span key={j} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-platform-500/10 text-platform-400 border border-platform-500/20">{topic}</span>
                      ))}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* SERP Trend Forecasts */}
        <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">SERP_TREND_FORECASTS</h3>
          </div>
          {loadingSERP ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : serpList.length === 0 ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No SERP trend data</div>
          ) : (
            <div className="space-y-3">
              {serpList.map((s, i) => (
                <motion.div
                  key={s.keyword || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-200">{s.keyword}</span>
                    <span className={`text-[10px] font-mono ${s.trend_direction === "up" ? "text-emerald-400" : s.trend_direction === "down" ? "text-red-400" : "text-amber-400"}`}>
                      {s.trend_direction === "up" ? "↑" : s.trend_direction === "down" ? "↓" : "→"} {s.trend_direction.toUpperCase()}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500">
                    <span>Current: #{s.current_position}</span>
                    <span>Predicted: #{s.predicted_position}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Strategic Backlink Map */}
        <motion.div {...slideUp} transition={{ delay: 0.15 }} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Link2 className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">STRATEGIC_BACKLINK_MAP</h3>
          </div>
          {loadingBacklinks ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : opportunities.length === 0 ? (
            <div className="text-sm text-slate-500 font-mono py-8 text-center">No backlink opportunities</div>
          ) : (
            <div className="space-y-3">
              {opportunities.map((o, i) => (
                <motion.div
                  key={o.domain || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-4 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-slate-200">{o.domain}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="text-center p-2 rounded bg-surface-darker/30 border border-surface-border/30">
                      <span className={`text-sm font-bold font-mono ${o.authority >= 70 ? "text-emerald-400" : o.authority >= 40 ? "text-amber-400" : "text-red-400"}`}>
                        {Math.round(o.authority)}
                      </span>
                      <p className="text-[9px] font-mono text-slate-600">Authority</p>
                    </div>
                    <div className="text-center p-2 rounded bg-surface-darker/30 border border-surface-border/30">
                      <span className={`text-sm font-bold font-mono ${o.relevance >= 70 ? "text-emerald-400" : o.relevance >= 40 ? "text-amber-400" : "text-red-400"}`}>
                        {Math.round(o.relevance)}
                      </span>
                      <p className="text-[9px] font-mono text-slate-600">Relevance</p>
                    </div>
                    <div className="text-center p-2 rounded bg-surface-darker/30 border border-surface-border/30">
                      <span className={`text-sm font-bold font-mono ${o.difficulty <= 30 ? "text-emerald-400" : o.difficulty <= 60 ? "text-amber-400" : "text-red-400"}`}>
                        {Math.round(o.difficulty)}
                      </span>
                      <p className="text-[9px] font-mono text-slate-600">Difficulty</p>
                    </div>
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
