"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Search, Lightbulb, TrendingUp, AlertTriangle, Users, GitBranch } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface Keyword {
  id: string;
  keyword: string;
  search_volume: number;
  difficulty: number;
  cpc: number;
  competition: number;
  intent: string;
  cluster_id?: string;
}

interface Prospect {
  id: string;
  domain: string;
  domain_authority: number;
  relevance_score: number;
  spam_score: number;
  composite_score: number;
  status: string;
  campaign_id: string;
}

interface Opportunity {
  type: "keyword" | "prospect" | "seo";
  title: string;
  description: string;
  priority: "high" | "medium" | "low";
  impact: number;
  data: any;
}

function getIntentBadge(intent: string) {
  const intentConfig: Record<string, { color: string; label: string }> = {
    transactional: { color: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20", label: "TRANSACTIONAL" },
    commercial: { color: "bg-blue-500/10 text-blue-400 border-blue-500/20", label: "COMMERCIAL" },
    navigational: { color: "bg-purple-500/10 text-purple-400 border-purple-500/20", label: "NAVIGATIONAL" },
    informational: { color: "bg-amber-500/10 text-amber-400 border-amber-500/20", label: "INFORMATIONAL" },
  };
  
  const config = intentConfig[intent] || intentConfig.informational;
  
  return (
    <span className={`px-2 py-1 text-[10px] font-mono rounded border ${config.color}`}>
      {config.label}
    </span>
  );
}

function getPriorityBadge(priority: string) {
  const config: Record<string, { color: string; icon: any }> = {
    high: { color: "bg-red-500/10 text-red-400 border-red-500/20", icon: AlertTriangle },
    medium: { color: "bg-amber-500/10 text-amber-400 border-amber-500/20", icon: Lightbulb },
    low: { color: "bg-slate-500/10 text-slate-400 border-slate-500/20", icon: TrendingUp },
  };
  
  const { color, icon: Icon } = config[priority] || config.low;
  
  return (
    <span className={`px-2 py-1 text-[10px] font-mono rounded border ${color} flex items-center gap-1`}>
      <Icon className="w-3 h-3" />
      {safeUpper(priority)}
    </span>
  );
}

export function OpportunitiesTab({ customerId }: { customerId: string }) {
  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  // Fetch keywords
  const { data: keywords = [], isLoading: loadingKeywords } = useQuery<Keyword[]>({
    queryKey: ["customer", customerId, "keywords"],
    queryFn: async () => {
      const response = await fetchApi<any>(`/business-intelligence/intelligence/keywords?tenant_id=${tenantId}`);
      const allKeywords = response?.data?.keywords || [];
      return (safeArr(allKeywords) as Keyword[]).slice(0, 20); // Limit to 20 for performance
    },
    refetchInterval: 60000,
  });

  // Fetch prospects
  const { data: campaigns = [], isLoading: loadingCampaigns } = useQuery<any[]>({
    queryKey: ["customer", customerId, "campaigns"],
    queryFn: async () => {
      const response = await fetchApi<any>(`/business-intelligence/intelligence/campaigns?tenant_id=${tenantId}`);
      return (response?.data?.campaigns || []).filter((c: any) => c.client_id === customerId);
    },
  });

  const campaignIds = new Set(safeArr<any>(campaigns).map((c: any) => c.id));
  
  const { data: allProspects = [], isLoading: loadingProspects } = useQuery<Prospect[]>({
    queryKey: ["customer", customerId, "prospects"],
    queryFn: async () => {
      // This would need a dedicated prospects endpoint - using empty array for now
      return [];
    },
    enabled: campaignIds.size > 0,
  });

  // Build opportunities from keywords
  const opportunities: Opportunity[] = [
    // High volume keywords with low difficulty
    ...safeArr<Keyword>(keywords)
      .filter((k) => safeNum(k.search_volume) > 1000 && safeNum(k.difficulty) < 40)
      .slice(0, 5)
      .map((k) => ({
        type: "keyword" as const,
        title: `Target "${k.keyword}"`,
        description: `High volume (${safeLocale(k.search_volume)}) with low difficulty (${safeNum(k.difficulty)})`,
        priority: "high" as const,
        impact: safeNum(k.search_volume) * (100 - safeNum(k.difficulty)) / 100,
        data: k,
      })),

    // Commercial intent keywords
    ...safeArr<Keyword>(keywords)
      .filter((k) => k.intent === "commercial" && safeNum(k.search_volume) > 500)
      .slice(0, 5)
      .map((k) => ({
        type: "keyword" as const,
        title: `Optimize for "${k.keyword}"`,
        description: `Commercial intent keyword with ${safeNum(k.search_volume)} monthly searches`,
        priority: "medium" as const,
        impact: safeNum(k.search_volume) * 0.8,
        data: k,
      })),
  ];

  const stats = {
    totalKeywords: safeArr<Keyword>(keywords).length,
    highVolume: safeArr<Keyword>(keywords).filter((k) => safeNum(k.search_volume) > 1000).length,
    commercialIntent: safeArr<Keyword>(keywords).filter((k) => k.intent === "commercial").length,
    totalProspects: safeArr<Prospect>(allProspects).length,
    highQualityProspects: safeArr<Prospect>(allProspects).filter((p) => safeNum(p.composite_score) > 0.7).length,
    opportunities: opportunities.length,
  };

  const isLoading = loadingKeywords || loadingCampaigns || loadingProspects;

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="text-center p-8 glass-panel">
          <Search className="w-12 h-12 text-platform-500 animate-spin mx-auto mb-3" />
          <p className="text-xs font-mono text-slate-500">Loading opportunities...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <Search className="w-3.5 h-3.5" /> Keywords
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{stats.totalKeywords}</p>
        </div>
        <div className="glass-panel p-4 border-emerald-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-500 uppercase mb-2">
            <TrendingUp className="w-3.5 h-3.5" /> High Volume
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400">{stats.highVolume}</p>
        </div>
        <div className="glass-panel p-4 border-blue-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-blue-500 uppercase mb-2">
            <Lightbulb className="w-3.5 h-3.5" /> Opportunities
          </div>
          <p className="text-2xl font-bold font-mono text-blue-400">{stats.opportunities}</p>
        </div>
      </div>

      {/* Keyword Opportunities */}
      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50">
          <div className="flex items-center gap-2">
            <Lightbulb className="w-4 h-4 text-platform-400" />
            <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">Keyword Opportunities</h3>
          </div>
        </div>

        {safeArr<Opportunity>(opportunities).length === 0 ? (
          <div className="p-8 text-center">
            <Lightbulb className="w-12 h-12 text-slate-700 mx-auto mb-3" />
            <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Opportunities Yet</h3>
            <p className="text-xs text-slate-500">Conduct keyword research to discover opportunities</p>
          </div>
        ) : (
          <div className="divide-y divide-surface-border">
            {safeArr<Opportunity>(opportunities).map((opp, index) => (
              <div key={index} className="p-4 hover:bg-surface-border/20 transition-colors">
                <div className="flex items-start justify-between mb-2">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-sm font-bold font-mono text-slate-200">{opp.title}</h4>
                      {getPriorityBadge(opp.priority)}
                    </div>
                    <p className="text-[10px] text-slate-500">{opp.description}</p>
                  </div>
                  <div className="text-right ml-4">
                    <div className="text-[10px] font-mono text-slate-600">Impact Score</div>
                    <div className="text-sm font-bold font-mono text-platform-400">
                      {safeFixed(opp.impact, 0)}
                    </div>
                  </div>
                </div>

                {opp.type === "keyword" && opp.data && (
                  <div className="flex items-center gap-4 text-[10px] font-mono text-slate-600">
                    <span className="flex items-center gap-1">
                      <Search className="w-3 h-3 text-platform-500" />
                      Vol: {safeLocale(opp.data.search_volume)}
                    </span>
                    <span className="flex items-center gap-1">
                      <TrendingUp className="w-3 h-3 text-amber-500" />
                      KD: {safeNum(opp.data.difficulty)}
                    </span>
                    <span className="flex items-center gap-1">
                      {getIntentBadge(opp.data.intent)}
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Top Keywords */}
      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-platform-400" />
            <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">Top Keywords</h3>
          </div>
        </div>

        <div className="divide-y divide-surface-border">
          {safeArr<Keyword>(keywords).slice(0, 10).map((keyword) => (
            <div key={keyword.id} className="p-3 hover:bg-surface-border/20 transition-colors">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-mono text-slate-200">{keyword.keyword}</span>
                {getIntentBadge(keyword.intent)}
              </div>
              <div className="flex items-center gap-4 text-[10px] font-mono text-slate-600">
                <span>Vol: {safeLocale(keyword.search_volume)}</span>
                <span>KD: {safeNum(keyword.difficulty)}</span>
                <span>CPC: ${safeFixed(keyword.cpc, 2)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}