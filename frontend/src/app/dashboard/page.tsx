"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { formatNumber } from "@/lib/utils";
import { useCommandCenter } from "@/hooks/use-command-center";
import { useRealtimeStore } from "@/hooks/use-realtime";
import { useClient } from "@/hooks/use-client";
import { CampaignEvolutionPanel } from "@/components/operational/campaign-evolution-panel";
import { KeywordIntelligencePanel } from "@/components/operational/keyword-intelligence-panel";
import { RecommendationTicker } from "@/components/operational/recommendation-ticker";
import { GitBranch, Search, Target, Activity, Sparkles } from "lucide-react";

export default function ClientCommandCenter() {
  const { openCommand } = useCommandCenter();
  const store = useRealtimeStore();
  const client = useClient();

  const { data: overview } = useQuery<any>({
    queryKey: ["bi-overview"],
    queryFn: () => fetchApi("/business-intelligence/intelligence/overview"),
    refetchInterval: 30000,
  });

  const activeWorkflows = useMemo(() =>
    store.workflows.filter((w) => w.status === "running"),
    [store.workflows],
  );

  const campaigns = overview?.campaigns;
  const keywords = overview?.keywords;
  const intel = overview?.intelligence;
  const recs = overview?.recommendations;
  const avgHealth = campaigns?.avg_health ?? 0;
  const kwTotal = keywords?.total ?? 0;

  return (
    <div className="space-y-5">
      {/* Client Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400 font-bold text-sm">
              TS
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight">{client.name}</h1>
              <p className="text-slate-500 text-sm">
                {client.niche} · {client.domain}
                <span className="mx-2">·</span>
                Health <span className="text-emerald-400 font-mono">{(avgHealth * 100).toFixed(0)}%</span>
                <span className="mx-2">·</span>
                {kwTotal} keywords
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => openCommand("keyword_discovery")} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" /> Discover Keywords
          </button>
          <button onClick={() => openCommand("create_campaign")} className="px-3 py-1.5 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-1.5">
            <GitBranch className="w-3.5 h-3.5" /> New Campaign
          </button>
        </div>
      </div>

      {/* Client KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Link href="/dashboard/campaigns" className="glass-panel p-4 hover:border-platform-500/30 transition-colors">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">
            <GitBranch className="w-3.5 h-3.5 text-emerald-400" /> Campaigns
          </div>
          <span className="text-2xl font-bold font-mono text-slate-100">{formatNumber(campaigns?.active ?? 0)}</span>
          <span className="text-xs text-slate-500 ml-2">active</span>
        </Link>
        <Link href="/dashboard/keywords" className="glass-panel p-4 hover:border-platform-500/30 transition-colors">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">
            <Search className="w-3.5 h-3.5 text-platform-400" /> Keywords
          </div>
          <span className="text-2xl font-bold font-mono text-slate-100">{formatNumber(kwTotal)}</span>
          <span className="text-xs text-slate-500 ml-2">tracked</span>
        </Link>
        <Link href="/dashboard/backlink-intelligence" className="glass-panel p-4 hover:border-platform-500/30 transition-colors">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">
            <Target className="w-3.5 h-3.5 text-amber-400" /> Opportunities
          </div>
          <span className="text-2xl font-bold font-mono text-slate-100">{formatNumber(intel?.events_24h ?? 0)}</span>
          <span className="text-xs text-slate-500 ml-2">found</span>
        </Link>
        <Link href="/dashboard/topology" className="glass-panel p-4 hover:border-platform-500/30 transition-colors">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase tracking-wider mb-2">
            <Activity className="w-3.5 h-3.5 text-indigo-400" /> Active
          </div>
          <span className="text-2xl font-bold font-mono text-slate-100">{activeWorkflows.length}</span>
          <span className="text-xs text-slate-500 ml-2">workflows</span>
        </Link>
      </div>

      {/* Live Intelligence */}
      <RecommendationTicker />

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <CampaignEvolutionPanel />
        <KeywordIntelligencePanel />
      </div>

      {/* Intelligence Quick Links */}
      <div className="glass-panel p-4">
        <div className="text-xs font-mono text-slate-500 uppercase tracking-wider mb-3">Intelligence Center</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <Link href="/dashboard/seo-intelligence" className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border/50 hover:border-platform-500/30 transition-colors">
            <span className="text-sm font-mono text-slate-200">SEO Intelligence</span>
            <span className="text-[10px] font-mono text-slate-500 block mt-0.5">{kwTotal} keywords analyzed</span>
          </Link>
          <Link href="/dashboard/backlink-intelligence" className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border/50 hover:border-platform-500/30 transition-colors">
            <span className="text-sm font-mono text-slate-200">Backlink Analysis</span>
            <span className="text-[10px] font-mono text-slate-500 block mt-0.5">{campaigns?.total_links_acquired ?? 0} links</span>
          </Link>
          <Link href="/dashboard/recommendations" className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border/50 hover:border-platform-500/30 transition-colors">
            <span className="text-sm font-mono text-slate-200">Recommendations</span>
            <span className="text-[10px] font-mono text-slate-500 block mt-0.5">{recs?.active ?? 0} active</span>
          </Link>
          <Link href="/dashboard/local-seo" className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border/50 hover:border-platform-500/30 transition-colors">
            <span className="text-sm font-mono text-slate-200">Local SEO</span>
            <span className="text-[10px] font-mono text-slate-500 block mt-0.5">techstart.io</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
