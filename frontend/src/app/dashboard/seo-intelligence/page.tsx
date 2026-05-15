"use client";

import { Search, BarChart3, GitBranch, PieChart, MapPin, Loader2, TrendingUp, Activity, Grid3X3, Layers } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface OpportunityScore {
  keyword: string;
  opportunity_score: number;
  search_volume: number;
  difficulty: number;
  intent: string;
}

interface TopicalNode {
  id: string;
  name: string;
  children?: TopicalNode[];
  volume?: number;
  difficulty?: number;
}

interface SERPFeature {
  feature_type: string;
  present: boolean;
  estimated_traffic_share: number;
}

interface RankingDifficulty {
  overall_difficulty: number;
  top10_authority: number;
  content_quality_required: number;
}

interface LocalIntent {
  keyword: string;
  intent_category: string;
  local_intent_score: number;
}

const INTENT_COLORS: Record<string, string> = {
  informational: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  commercial: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  transactional: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  navigational: "bg-purple-500/10 text-purple-400 border-purple-500/20",
};

function opportunityColor(score: number): string {
  if (score >= 70) return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
  if (score >= 50) return "bg-amber-500/20 text-amber-400 border-amber-500/30";
  if (score >= 30) return "bg-orange-500/20 text-orange-400 border-orange-500/30";
  return "bg-red-500/20 text-red-400 border-red-500/30";
}

function opportunityBg(score: number): string {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  if (score >= 30) return "bg-orange-500";
  return "bg-red-500";
}

function difficultyColor(diff: number): string {
  if (diff <= 0.3) return "text-emerald-400";
  if (diff <= 0.6) return "text-amber-400";
  return "text-red-400";
}

export default function SEOIntelligencePage() {
  const { data: opportunities, isLoading: loadingOpps } = useQuery<OpportunityScore[]>({
    queryKey: ["seo-intelligence", "opportunities", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/seo-intelligence/opportunities?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 60000,
  });

  const { data: topicalMap, isLoading: loadingTopical } = useQuery<{ tree: TopicalNode[] }>({
    queryKey: ["seo-intelligence", "topical", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/seo-intelligence/topical-map?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const { data: serpFeatures, isLoading: loadingSERP } = useQuery<SERPFeature[]>({
    queryKey: ["seo-intelligence", "serp"],
    queryFn: () => fetchApi("/serp-intelligence/features"),
    refetchInterval: 300000,
  });

  const { data: difficulty, isLoading: loadingDiff } = useQuery<RankingDifficulty>({
    queryKey: ["seo-intelligence", "difficulty"],
    queryFn: () => fetchApi("/serp-intelligence/ranking-difficulty"),
    refetchInterval: 300000,
  });

  const { data: localIntent, isLoading: loadingLocal } = useQuery<LocalIntent[]>({
    queryKey: ["seo-intelligence", "local-intent", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/seo-intelligence/local-intent?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const opps = opportunities ?? [];
  const tree = topicalMap?.tree ?? [];
  const serp = serpFeatures ?? [];
  const local = localIntent ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">SEO_INTELLIGENCE</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Keyword & market intelligence command center</p>
        </div>
        <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 flex items-center gap-2">
          <Search className="w-4 h-4" />
          {opps.length} KEYWORDS TRACKED
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Keyword Opportunity Heatmap */}
        <div className="lg:col-span-2 glass-panel overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-border flex items-center gap-2">
            <Grid3X3 className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">KEYWORD_OPPORTUNITY_HEATMAP</h3>
            <span className="ml-auto text-[10px] font-mono text-slate-600">COLOR = OPPORTUNITY SCORE</span>
          </div>
          <div className="p-4">
            {loadingOpps ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
              </div>
            ) : opps.length === 0 ? (
              <div className="text-center py-16 text-slate-500 font-mono">NO_KEYWORD_DATA</div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
                {opps.slice(0, 30).map((kw, i) => (
                  <div
                    key={i}
                    className={`p-3 rounded-lg border ${opportunityColor(kw.opportunity_score)} transition-all hover:scale-105`}
                  >
                    <p className="text-xs font-mono truncate mb-1">{kw.keyword}</p>
                    <div className="flex items-center gap-1">
                      <div className={`w-2 h-2 rounded-full ${opportunityBg(kw.opportunity_score)}`} />
                      <span className="text-[10px] font-mono">{Math.round(kw.opportunity_score)}</span>
                    </div>
                    <div className="flex justify-between text-[9px] text-slate-500 mt-1">
                      <span>V:{kw.search_volume}</span>
                      <span>D:{Math.round(kw.difficulty * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* SERP Feature Analysis */}
        <div className="glass-panel flex flex-col">
          <div className="px-6 py-4 border-b border-surface-border flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">SERP_FEATURES</h3>
          </div>
          <div className="flex-1 p-4 space-y-3 overflow-auto max-h-[400px]">
            {loadingSERP ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
              </div>
            ) : serp.length === 0 ? (
              <div className="text-center py-12 text-slate-500 font-mono">NO_SERP_DATA</div>
            ) : (
              serp.map((f, i) => (
                <div key={i} className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300 uppercase">{f.feature_type.replace(/_/g, " ")}</span>
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${f.present ? "bg-emerald-500/10 text-emerald-400" : "bg-slate-500/10 text-slate-500"}`}>
                      {f.present ? "PRESENT" : "ABSENT"}
                    </span>
                  </div>
                  <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                    <div className="h-full bg-indigo-500 rounded-full" style={{ width: `${f.estimated_traffic_share}%` }} />
                  </div>
                  <p className="text-[10px] font-mono text-slate-600 mt-1">{f.estimated_traffic_share}% traffic share</p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Topical Authority Tree */}
        <div className="lg:col-span-2 glass-panel overflow-hidden">
          <div className="px-6 py-4 border-b border-surface-border flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-emerald-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">TOPICAL_AUTHORITY_TREE</h3>
            <span className="ml-auto text-[10px] font-mono text-slate-600">EXPANDABLE</span>
          </div>
          <div className="p-4">
            {loadingTopical ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
              </div>
            ) : tree.length === 0 ? (
              <div className="text-center py-16 text-slate-500 font-mono">NO_TOPICAL_DATA</div>
            ) : (
              <div className="space-y-2">
                {tree.map((node, i) => (
                  <TopicalTreeNode key={node.id || i} node={node} depth={0} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Ranking Difficulty & Local Intent */}
        <div className="space-y-6">
          {/* Ranking Difficulty */}
          <div className="glass-panel p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
              <Activity className="w-5 h-5 text-orange-500" />
              RANKING_DIFFICULTY
            </h3>
            {loadingDiff ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
              </div>
            ) : difficulty ? (
              <div className="space-y-4">
                <div className="text-center">
                  <span className={`text-4xl font-bold font-mono ${difficultyColor(difficulty.overall_difficulty / 100)}`}>
                    {Math.round(difficulty.overall_difficulty)}
                  </span>
                  <p className="text-xs font-mono text-slate-500 mt-1">OVERALL DIFFICULTY</p>
                </div>
                <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${difficulty.overall_difficulty > 60 ? "bg-red-500" : difficulty.overall_difficulty > 30 ? "bg-amber-500" : "bg-emerald-500"}`}
                    style={{ width: `${difficulty.overall_difficulty}%` }}
                  />
                </div>
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50">
                    <p className="text-xs font-mono text-slate-400">{Math.round(difficulty.top10_authority)}%</p>
                    <p className="text-[9px] font-mono text-slate-600">TOP 10 AUTHORITY</p>
                  </div>
                  <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50">
                    <p className="text-xs font-mono text-slate-400">{Math.round(difficulty.content_quality_required)}%</p>
                    <p className="text-[9px] font-mono text-slate-600">CONTENT QUALITY</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8 text-slate-500 font-mono">NO_DIFFICULTY_DATA</div>
            )}
          </div>

          {/* Local Intent Map */}
          <div className="glass-panel p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
              <MapPin className="w-5 h-5 text-rose-500" />
              LOCAL_INTENT_MAP
            </h3>
            {loadingLocal ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
              </div>
            ) : local.length === 0 ? (
              <div className="text-center py-8 text-slate-500 font-mono">NO_LOCAL_INTENT_DATA</div>
            ) : (
              <div className="space-y-2 max-h-[200px] overflow-auto">
                {local.map((li, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/50 border border-surface-border/50">
                    <span className="text-xs font-mono text-slate-300 truncate max-w-[140px]">{li.keyword}</span>
                    <div className="flex items-center gap-2">
                      <span className={`text-[9px] font-mono px-1.5 py-0.5 rounded border ${INTENT_COLORS[li.intent_category] || "bg-slate-500/10 text-slate-400 border-slate-500/20"}`}>
                        {li.intent_category?.slice(0, 4).toUpperCase()}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500">{Math.round(li.local_intent_score * 100)}%</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function TopicalTreeNode({ node, depth }: { node: TopicalNode; depth: number }) {
  const hasChildren = node.children && node.children.length > 0;
  return (
    <div className="select-none">
      <div
        className="flex items-center gap-2 p-2 rounded-md hover:bg-surface-darker/50 transition-colors"
        style={{ paddingLeft: `${12 + depth * 20}px` }}
      >
        {hasChildren ? (
          <Layers className="w-3.5 h-3.5 text-platform-400 shrink-0" />
        ) : (
          <div className="w-3.5 h-0.5 bg-slate-600 shrink-0" />
        )}
        <span className="text-xs font-mono text-slate-300 truncate">{node.name}</span>
        {node.volume !== undefined && (
          <span className="text-[10px] font-mono text-slate-600 ml-auto">{node.volume.toLocaleString()}</span>
        )}
      </div>
      {hasChildren && (
        <div>
          {node.children!.map((child, i) => (
            <TopicalTreeNode key={child.id || i} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
