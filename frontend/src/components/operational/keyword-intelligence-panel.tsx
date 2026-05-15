"use client";

import { useState, useEffect, useMemo } from "react";
import { motion } from "framer-motion";
import {
  Search, Sparkles, Target, TrendingUp,
  BarChart3, Globe, Loader2, Layers,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import type {
  KeywordOpportunity, ClusterAuthority,
  ClusterVisualizationNode, ClusterVisualizationEdge,
} from "@/types/business-intelligence";

export function KeywordIntelligencePanel() {
  const [opportunities, setOpportunities] = useState<KeywordOpportunity[]>([]);
  const [clusters, setClusters] = useState<ClusterAuthority[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<"opportunities" | "clusters">("clusters");

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [oppData, clusData] = await Promise.all([
          fetchApi<any>("/business-intelligence/intelligence/keyword-opportunities"),
          fetchApi<any>("/business-intelligence/intelligence/clusters"),
        ]);
        if (oppData?.opportunities) setOpportunities(oppData.opportunities);
        if (clusData?.clusters) setClusters(clusData.clusters);
      } catch {} finally {
        setLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  const topOpportunities = useMemo(() =>
    [...opportunities].sort((a, b) => b.opportunity_score - a.opportunity_score).slice(0, 8),
    [opportunities],
  );

  const sortedClusters = useMemo(() =>
    [...clusters].sort((a, b) => b.authority - a.authority),
    [clusters],
  );

  if (loading) {
    return (
      <div className="glass-panel p-6 flex items-center justify-center min-h-[200px]">
        <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="glass-panel overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border bg-surface-darker/50">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-platform-400" />
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase tracking-wider">
            Keyword Intelligence
          </h3>
          <span className="text-[9px] font-mono text-slate-600">
            {opportunities.length} keywords · {clusters.length} clusters
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setView("clusters")}
            className={`px-2 py-1 text-[9px] font-mono rounded transition-colors ${
              view === "clusters"
                ? "bg-platform-500/10 text-platform-400 border border-platform-500/20"
                : "text-slate-600 hover:text-slate-400"
            }`}
          >
            CLUSTERS
          </button>
          <button
            onClick={() => setView("opportunities")}
            className={`px-2 py-1 text-[9px] font-mono rounded transition-colors ${
              view === "opportunities"
                ? "bg-platform-500/10 text-platform-400 border border-platform-500/20"
                : "text-slate-600 hover:text-slate-400"
            }`}
          >
            OPPORTUNITIES
          </button>
        </div>
      </div>

      <div className="p-4">
        {view === "clusters" ? (
          <div className="space-y-2">
            {sortedClusters.length === 0 ? (
              <div className="text-center py-6">
                <Layers className="w-6 h-6 text-slate-700 mx-auto mb-2" />
                <p className="text-[10px] font-mono text-slate-600">No clusters formed yet</p>
              </div>
            ) : (
              sortedClusters.map((cluster, i) => {
                const authorityPct = Math.round(cluster.authority * 100);
                const opportunityPct = Math.round(cluster.opportunity * 100);
                return (
                  <motion.div
                    key={cluster.name}
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border/50 hover:border-platform-500/20 transition-colors"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="text-xs font-mono text-slate-200 font-medium">{cluster.name}</span>
                        <span className="text-[9px] font-mono text-slate-500 ml-2">{cluster.keyword_count} keywords</span>
                      </div>
                      <div className="flex items-center gap-3 text-[9px] font-mono">
                        <span className="flex items-center gap-1 text-slate-500">
                          <Globe className="w-2.5 h-2.5" />
                          {cluster.total_volume.toLocaleString()}
                        </span>
                        <span className="text-slate-600">diff {cluster.avg_difficulty.toFixed(0)}%</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="flex items-center justify-between text-[8px] font-mono mb-0.5">
                          <span className="text-slate-600">Authority</span>
                          <span className="text-emerald-400">{authorityPct}%</span>
                        </div>
                        <div className="h-1 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${authorityPct}%` }}
                            transition={{ duration: 0.5, delay: i * 0.05 }}
                            className="h-full rounded-full bg-emerald-500"
                          />
                        </div>
                      </div>
                      <div>
                        <div className="flex items-center justify-between text-[8px] font-mono mb-0.5">
                          <span className="text-slate-600">Opportunity</span>
                          <span className="text-platform-400">{opportunityPct}%</span>
                        </div>
                        <div className="h-1 bg-surface-darker rounded-full overflow-hidden">
                          <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${opportunityPct}%` }}
                            transition={{ duration: 0.5, delay: i * 0.05 }}
                            className="h-full rounded-full bg-platform-500"
                          />
                        </div>
                      </div>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        ) : (
          <div className="space-y-1.5">
            {topOpportunities.length === 0 ? (
              <div className="text-center py-6">
                <Target className="w-6 h-6 text-slate-700 mx-auto mb-2" />
                <p className="text-[10px] font-mono text-slate-600">No opportunity data yet</p>
              </div>
            ) : (
              topOpportunities.map((opp, i) => {
                const oppPct = Math.round(opp.opportunity_score * 100);
                return (
                  <motion.div
                    key={opp.keyword}
                    initial={{ opacity: 0, x: -5 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="flex items-center gap-3 p-2 rounded bg-surface-darker/50 border border-surface-border/50"
                  >
                    <span className="text-[10px] font-mono text-slate-500 w-5 text-right">{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] font-mono text-slate-200 truncate">{opp.keyword}</p>
                      <div className="flex items-center gap-2 text-[8px] font-mono text-slate-600">
                        <span>vol {opp.search_volume.toLocaleString()}</span>
                        <span>diff {opp.difficulty}%</span>
                        {opp.cluster && <span className="text-platform-500/70">{opp.cluster}</span>}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0">
                      <div className="w-12 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${oppPct}%` }}
                          transition={{ duration: 0.5 }}
                          className={`h-full rounded-full ${oppPct > 70 ? "bg-emerald-500" : oppPct > 50 ? "bg-amber-500" : "bg-platform-500"}`}
                        />
                      </div>
                      <span className={`text-[10px] font-mono font-bold ${oppPct > 70 ? "text-emerald-400" : oppPct > 50 ? "text-amber-400" : "text-platform-400"}`}>
                        {oppPct}%
                      </span>
                    </div>
                  </motion.div>
                );
              })
            )}
          </div>
        )}
      </div>
    </div>
  );
}
