"use client";

import { useState, useMemo } from "react";
import { Lightbulb, CheckCircle2, ChevronDown, ChevronRight, Loader2, ArrowUpDown, Link2, Search, MapPin, Target, GitBranch } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface Recommendation {
  id: string;
  priority: string;
  category: string;
  recommendation_text: string;
  impact: string;
  effort: string;
  confidence: number;
  supporting_data: Record<string, any>;
  action_optional: boolean;
  created_at: string;
}

function splitRecommendationText(text: string): { title: string; description: string } {
  const sep = text.indexOf(" — ");
  if (sep === -1) return { title: text, description: "" };
  return { title: text.slice(0, sep), description: text.slice(sep + 3) };
}

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  backlink: <Link2 className="w-4 h-4" />,
  keyword: <Search className="w-4 h-4" />,
  local: <MapPin className="w-4 h-4" />,
  campaign: <Target className="w-4 h-4" />,
  workflow: <GitBranch className="w-4 h-4" />,
};

const PRIORITY_COLORS: Record<string, string> = {
  P0: "bg-red-500/10 text-red-400 border-red-500/20",
  P1: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  P2: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  P3: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

function confidenceColor(score: number): string {
  if (score >= 0.7) return "text-emerald-400";
  if (score >= 0.4) return "text-amber-400";
  return "text-red-400";
}

function confidenceBarColor(score: number): string {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-red-500";
}

function impactColor(impact: string): string {
  const i = impact.toLowerCase();
  if (i.includes("high")) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  if (i.includes("medium")) return "bg-amber-500/10 text-amber-400 border-amber-500/20";
  return "bg-slate-500/10 text-slate-400 border-slate-500/20";
}

function effortColor(effort: string): string {
  const e = effort.toLowerCase();
  if (e.includes("low")) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  if (e.includes("medium")) return "bg-amber-500/10 text-amber-400 border-amber-500/20";
  return "bg-red-500/10 text-red-400 border-red-500/20";
}

export default function RecommendationsPage() {
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [filterPriority, setFilterPriority] = useState<string>("all");
  const [filterSource, setFilterSource] = useState<string>("all");
  const [sortBy, setSortBy] = useState<string>("priority");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("asc");

  const { data: recommendations = [], isLoading } = useQuery<Recommendation[]>({
    queryKey: ["recommendations", MOCK_TENANT_ID],
    queryFn: async () => {
      const data = await fetchApi<{ all_recommendations: Recommendation[] }>(`/recommendations?tenant_id=${MOCK_TENANT_ID}`);
      return data.all_recommendations ?? [];
    },
    refetchInterval: 60000,
  });

  const implementMutation = useMutation({
    mutationFn: (id: string) =>
      fetchApi(`/recommendations/${id}/implement?tenant_id=${MOCK_TENANT_ID}`, { method: "POST" }),
    onSuccess: () => { setTimeout(() => queryClient.invalidateQueries({ queryKey: ["recommendations"] }), 300); },
  });

  const sources = useMemo(() => {
    const s = new Set(recommendations.map(r => r.category).filter(Boolean));
    return ["all", ...Array.from(s)];
  }, [recommendations]);

  const filtered = recommendations.filter((r) => {
    if (filterCategory !== "all" && r.category !== filterCategory) return false;
    if (filterPriority !== "all" && r.priority !== filterPriority) return false;
    if (filterSource !== "all" && r.category !== filterSource) return false;
    return true;
  });

  const sortedAndFiltered = useMemo(() => {
    const sorted = [...filtered];
    const dir = sortOrder === "asc" ? 1 : -1;
    if (sortBy === "confidence") {
      sorted.sort((a, b) => (a.confidence - b.confidence) * dir);
    } else if (sortBy === "priority") {
      const order = { P0: 0, P1: 1, P2: 2, P3: 3 };
      sorted.sort((a, b) => ((order[a.priority as keyof typeof order] ?? 99) - (order[b.priority as keyof typeof order] ?? 99)) * dir);
    } else if (sortBy === "source") {
      sorted.sort((a, b) => (a.category || "").localeCompare(b.category || "") * dir);
    }
    return sorted;
  }, [filtered, sortBy, sortOrder]);

  const grouped: Record<string, Recommendation[]> = {};
  const priorityOrder = ["P0", "P1", "P2", "P3"];
  for (const r of sortedAndFiltered) {
    if (!grouped[r.priority]) grouped[r.priority] = [];
    grouped[r.priority].push(r);
  }

  const activeCount = recommendations.length;
  const implementedCount = 0;

  const isImplemented = () => false;

  const toggleImplemented = (rec: Recommendation) => {
    implementMutation.mutate(rec.id);
  };

  const cycleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(prev => prev === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortOrder("asc");
    }
  };

  const sortIndicator = (field: string) => {
    if (sortBy !== field) return null;
    return <ArrowUpDown className={`w-3 h-3 ml-1 ${sortOrder === "asc" ? "rotate-180" : ""}`} />;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">RECOMMENDATIONS</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">AI-powered optimization recommendations</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400">
            {implementedCount} IMPLEMENTED
          </div>
          <div className="px-3 py-1.5 rounded-md bg-platform-500/10 border border-platform-500/30 text-xs font-mono text-platform-400 flex items-center gap-2">
            <Lightbulb className="w-4 h-4" />
            {activeCount} ACTIVE
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-500 uppercase">Category:</span>
          {["all", "backlink", "keyword", "local", "campaign", "workflow"].map((cat) => (
            <button
              key={cat}
              onClick={() => setFilterCategory(cat)}
              className={`px-2.5 py-1 rounded-md text-[10px] font-mono border transition-colors ${
                filterCategory === cat
                  ? "bg-platform-500/10 border-platform-500/30 text-platform-400"
                  : "bg-surface-darker border-surface-border text-slate-500 hover:text-slate-300"
              }`}
            >
              {cat === "all" ? "ALL" : cat.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-500 uppercase">Priority:</span>
          {["all", "P0", "P1", "P2", "P3"].map((p) => (
            <button
              key={p}
              onClick={() => setFilterPriority(p)}
              className={`px-2.5 py-1 rounded-md text-[10px] font-mono border transition-colors ${
                filterPriority === p
                  ? "bg-platform-500/10 border-platform-500/30 text-platform-400"
                  : "bg-surface-darker border-surface-border text-slate-500 hover:text-slate-300"
              }`}
            >
              {p === "all" ? "ALL" : p}
            </button>
          ))}
        </div>
        {sources.length > 1 && (
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono text-slate-500 uppercase">Source:</span>
            {sources.map((s) => (
              <button
                key={s}
                onClick={() => setFilterSource(s)}
                className={`px-2.5 py-1 rounded-md text-[10px] font-mono border transition-colors ${
                  filterSource === s
                    ? "bg-platform-500/10 border-platform-500/30 text-platform-400"
                    : "bg-surface-darker border-surface-border text-slate-500 hover:text-slate-300"
                }`}
              >
                {s === "all" ? "ALL" : s.toUpperCase()}
              </button>
            ))}
          </div>
        )}
        <div className="flex items-center gap-2 border-l border-surface-border pl-3">
          <span className="text-[10px] font-mono text-slate-500 uppercase">Sort:</span>
          {["priority", "confidence", "source"].map((field) => (
            <button
              key={field}
              onClick={() => cycleSort(field)}
              className={`px-2.5 py-1 rounded-md text-[10px] font-mono border transition-colors flex items-center ${
                sortBy === field
                  ? "bg-platform-500/10 border-platform-500/30 text-platform-400"
                  : "bg-surface-darker border-surface-border text-slate-500 hover:text-slate-300"
              }`}
            >
              {field.charAt(0).toUpperCase() + field.slice(1)}
              {sortIndicator(field)}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : sortedAndFiltered.length === 0 ? (
        <div className="glass-panel p-12 text-center flex flex-col items-center justify-center border-dashed">
          <div className="w-16 h-16 bg-surface-darker rounded-full flex items-center justify-center mb-4 border border-surface-border">
            <Lightbulb className="w-8 h-8 text-slate-600" />
          </div>
          <h3 className="text-xl font-medium text-slate-200">No Recommendations</h3>
          <p className="text-slate-400 mt-2 max-w-md">
            No recommendations match the current filters. Try adjusting your filter criteria.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {priorityOrder.map((priority) => {
            const items = grouped[priority];
            if (!items || items.length === 0) return null;
            return (
              <div key={priority} className="space-y-2">
                <div className="flex items-center gap-2 px-1">
                  <span className={`text-xs font-mono px-2 py-0.5 rounded border font-bold ${PRIORITY_COLORS[priority] || PRIORITY_COLORS.P3}`}>
                    {priority}
                  </span>
                  <span className="text-[10px] font-mono text-slate-600">{items.length} recommendation{items.length > 1 ? "s" : ""}</span>
                </div>
                {items.map((rec) => {
                  const { title, description } = splitRecommendationText(rec.recommendation_text);
                  return (
                    <div
                      key={rec.id}
                      className="glass-panel overflow-hidden transition-all"
                    >
                      <div
                        className="p-5 cursor-pointer hover:bg-surface-darker/30 transition-colors"
                        onClick={() => setExpandedId(expandedId === rec.id ? null : rec.id)}
                      >
                        <div className="flex items-start gap-4">
                          <div className="p-2 rounded-lg border bg-surface-darker border-surface-border text-slate-500">
                            {CATEGORY_ICONS[rec.category] || <Lightbulb className="w-4 h-4" />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border font-bold ${PRIORITY_COLORS[rec.priority] || PRIORITY_COLORS.P3}`}>
                                {rec.priority}
                              </span>
                              <span className="text-[10px] font-mono text-slate-500 uppercase">{rec.category}</span>
                            </div>
                            <h4 className="text-sm font-medium text-slate-200 font-mono">{title}</h4>
                            {description && <p className="text-xs text-slate-400 mt-1 line-clamp-2">{description}</p>}
                            <div className="flex items-center gap-3 mt-2">
                              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${impactColor(rec.impact)}`}>
                                IMPACT: {rec.impact.toUpperCase()}
                              </span>
                              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${effortColor(rec.effort)}`}>
                                EFFORT: {rec.effort.toUpperCase()}
                              </span>
                              <span className={`text-[10px] font-mono ${confidenceColor(rec.confidence)}`}>
                                CONF: {Math.round(rec.confidence * 100)}%
                              </span>
                            </div>
                            <div className="mt-2 w-48">
                              <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                                <div
                                  className={`h-full rounded-full ${confidenceBarColor(rec.confidence)}`}
                                  style={{ width: `${rec.confidence * 100}%` }}
                                />
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); toggleImplemented(rec); }}
                              disabled={implementMutation.isPending}
                              className="p-2 rounded-md transition-colors border bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border-emerald-500/20"
                              title="Implement"
                            >
                              <CheckCircle2 className="w-4 h-4" />
                            </button>
                            {expandedId === rec.id ? (
                              <ChevronDown className="w-4 h-4 text-slate-500" />
                            ) : (
                              <ChevronRight className="w-4 h-4 text-slate-500" />
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
