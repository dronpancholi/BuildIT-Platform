"use client";

import { useState, useMemo } from "react";
import { useApiList, useApiCreate } from "@/services/hooks";
import { ENDPOINTS } from "@/services/endpoints";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { formatDate, formatNumber } from "@/lib/utils";
import {
  Search,
  Sparkles,
  ArrowUpDown,
  CheckSquare,
  Square,
  Globe,
  DollarSign,
  Target,
  TrendingUp,
} from "lucide-react";
import type { Keyword } from "@/types/models";

interface KeywordResearch extends Keyword {
  search_volume: number;
  difficulty: number;
  cpc: number;
  intent: string;
  cluster: string;
}

type SortField = "keyword" | "volume" | "difficulty" | "cpc" | "intent" | "cluster";
type SortDir = "asc" | "desc";
type DifficultyFilter = "" | "easy" | "medium" | "hard";

const DIFFICULTY_VARIANT: Record<string, "default" | "success" | "warning" | "destructive"> = {
  easy: "success",
  medium: "warning",
  hard: "destructive",
};

function getDifficultyLevel(score: number): "easy" | "medium" | "hard" {
  if (score <= 30) return "easy";
  if (score <= 60) return "medium";
  return "hard";
}

export default function KeywordsPage() {
  const [activeTab, setActiveTab] = useState<"results" | "clusters" | "insights">("results");
  const [seedKeywords, setSeedKeywords] = useState("");
  const [domain, setDomain] = useState("");
  const [selectedClientId, setSelectedClientId] = useState<string>("");
  const [sortField, setSortField] = useState<SortField>("keyword");
  const [sortDir, setSortDir] = useState<SortDir>("asc");
  const [difficultyFilter, setDifficultyFilter] = useState<DifficultyFilter>("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [hasSearched, setHasSearched] = useState(false);

  const { data: clients } = useApiList<{ id: string; name: string }>(ENDPOINTS.CLIENTS, {});

  const researchMutation = useApiCreate<KeywordResearch[], { seed_keywords: string[]; domain: string; client_id: string }>(
    ENDPOINTS.KEYWORDS_RESEARCH,
    {
      invalidateKeys: [ENDPOINTS.KEYWORDS],
      successMessage: "Keyword research completed",
    }
  );

  const { data: keywords, isLoading } = useApiList<KeywordResearch>(
    ENDPOINTS.KEYWORDS,
    {},
    { enabled: hasSearched }
  );

  const handleResearch = () => {
    if (!seedKeywords.trim() || !selectedClientId) return;
    setHasSearched(true);
    researchMutation.mutate({
      seed_keywords: seedKeywords.split(",").map((s) => s.trim()).filter(Boolean),
      domain,
      client_id: selectedClientId,
    });
  };

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(sortDir === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDir("asc");
    }
  };

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (!filteredKeywords) return;
    if (selectedIds.size === filteredKeywords.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredKeywords.map((k) => k.id)));
    }
  };

  const filteredKeywords = useMemo(() => {
    if (!keywords) return null;
    let result = [...keywords];

    if (difficultyFilter) {
      result = result.filter((k) => {
        const level = getDifficultyLevel(k.difficulty || 0);
        return level === difficultyFilter;
      });
    }

    result.sort((a, b) => {
      const aVal = a[sortField] ?? "";
      const bVal = b[sortField] ?? "";
      const cmp = typeof aVal === "number" && typeof bVal === "number"
        ? aVal - bVal
        : String(aVal).localeCompare(String(bVal));
      return sortDir === "asc" ? cmp : -cmp;
    });

    return result;
  }, [keywords, sortField, sortDir, difficultyFilter]);

  const clusters = useMemo(() => {
    if (!filteredKeywords) return [];
    const map = new Map<string, KeywordResearch[]>();
    filteredKeywords.forEach((k) => {
      const cluster = k.cluster || "Uncategorized";
      if (!map.has(cluster)) map.set(cluster, []);
      map.get(cluster)!.push(k);
    });
    return Array.from(map.entries()).sort((a, b) => b[1].length - a[1].length);
  }, [filteredKeywords]);

  const insights = useMemo(() => {
    if (!filteredKeywords || filteredKeywords.length === 0) return null;
    const total = filteredKeywords.length;
    const avgVolume = filteredKeywords.reduce((sum, k) => sum + (k.volume || 0), 0) / total;
    const avgDifficulty = filteredKeywords.reduce((sum, k) => sum + (k.difficulty || 0), 0) / total;
    const avgCpc = filteredKeywords.reduce((sum, k) => sum + (k.cpc || 0), 0) / total;
    const easy = filteredKeywords.filter((k) => getDifficultyLevel(k.difficulty || 0) === "easy").length;
    const medium = filteredKeywords.filter((k) => getDifficultyLevel(k.difficulty || 0) === "medium").length;
    const hard = filteredKeywords.filter((k) => getDifficultyLevel(k.difficulty || 0) === "hard").length;
    const intents = new Map<string, number>();
    filteredKeywords.forEach((k) => {
      if (k.intent) intents.set(k.intent, (intents.get(k.intent) || 0) + 1);
    });
    return { total, avgVolume, avgDifficulty, avgCpc, easy, medium, hard, intents };
  }, [filteredKeywords]);

  const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <th
      className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider cursor-pointer hover:text-slate-200 select-none"
      onClick={() => toggleSort(field)}
    >
      <span className="flex items-center gap-1">
        {children}
        <ArrowUpDown className="w-3 h-3" />
        {sortField === field && (
          <span className="text-platform-400">{sortDir === "asc" ? "↑" : "↓"}</span>
        )}
      </span>
    </th>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Keyword Research</h1>
          <p className="text-slate-400 mt-1">Discover and analyze keyword opportunities</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-platform-400" />
            Research
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 space-y-2">
              <Label htmlFor="seed-keywords">Seed Keywords</Label>
              <Input
                id="seed-keywords"
                placeholder="Enter seed keywords, comma separated..."
                value={seedKeywords}
                onChange={(e) => setSeedKeywords(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleResearch()}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="client">Client *</Label>
              <select
                id="client"
                value={selectedClientId}
                onChange={(e) => setSelectedClientId(e.target.value)}
                className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
              >
                <option value="">Select client...</option>
                {clients?.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="domain">Domain (optional)</Label>
              <Input
                id="domain"
                placeholder="example.com"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end">
            <Button
              onClick={handleResearch}
              disabled={!seedKeywords.trim() || !selectedClientId || researchMutation.isPending}
            >
              {researchMutation.isPending ? (
                "Researching..."
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  Research Keywords
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {hasSearched && (
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1 bg-surface-card border border-surface-border rounded-lg p-1">
            <button
              onClick={() => setActiveTab("results")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                activeTab === "results"
                  ? "bg-surface-darker text-slate-100 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Results
            </button>
            <button
              onClick={() => setActiveTab("clusters")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                activeTab === "clusters"
                  ? "bg-surface-darker text-slate-100 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Cluster View
            </button>
            <button
              onClick={() => setActiveTab("insights")}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                activeTab === "insights"
                  ? "bg-surface-darker text-slate-100 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Insights
            </button>
          </div>

          {activeTab === "results" && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Difficulty:</span>
              {(["", "easy", "medium", "hard"] as const).map((level) => (
                <button
                  key={level}
                  onClick={() => setDifficultyFilter(level)}
                  className={`px-2 py-1 text-[10px] font-medium rounded transition-all ${
                    difficultyFilter === level
                      ? level === "easy"
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : level === "medium"
                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                        : level === "hard"
                        ? "bg-red-500/10 text-red-400 border border-red-500/20"
                        : "bg-surface-card text-slate-300 border border-surface-border"
                      : "text-slate-500 hover:text-slate-300"
                  }`}
                >
                  {level === "" ? "All" : level.charAt(0).toUpperCase() + level.slice(1)}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {isLoading || researchMutation.isPending ? (
        <LoadingSpinner size="lg" className="py-20" />
      ) : !hasSearched || !filteredKeywords ? (
        <EmptyState
          icon={<Search className="w-8 h-8" />}
          title="Start your research"
          description="Enter seed keywords above to discover keyword opportunities and clusters."
        />
      ) : filteredKeywords.length === 0 ? (
        <EmptyState
          icon={<Search className="w-8 h-8" />}
          title="No keywords found"
          description="Try different seed keywords or adjust your filters."
        />
      ) : (
        <>
          {activeTab === "results" && (
            <Card>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-surface-border">
                      <th className="px-4 py-3 w-10">
                        <button onClick={toggleSelectAll} className="text-slate-500 hover:text-slate-300">
                          {selectedIds.size === filteredKeywords.length && filteredKeywords.length > 0 ? (
                            <CheckSquare className="w-4 h-4 text-platform-400" />
                          ) : (
                            <Square className="w-4 h-4" />
                          )}
                        </button>
                      </th>
                      <SortHeader field="keyword">Keyword</SortHeader>
                      <SortHeader field="volume">Volume</SortHeader>
                      <SortHeader field="difficulty">Difficulty</SortHeader>
                      <SortHeader field="cpc">CPC</SortHeader>
                      <SortHeader field="intent">Intent</SortHeader>
                      <SortHeader field="cluster">Cluster</SortHeader>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {filteredKeywords.map((kw) => (
                      <tr
                        key={kw.id}
                        className={`hover:bg-surface-card/50 transition-colors ${
                          selectedIds.has(kw.id) ? "bg-platform-500/5" : ""
                        }`}
                      >
                        <td className="px-4 py-3">
                          <button onClick={() => toggleSelect(kw.id)} className="text-slate-500 hover:text-slate-300">
                            {selectedIds.has(kw.id) ? (
                              <CheckSquare className="w-4 h-4 text-platform-400" />
                            ) : (
                              <Square className="w-4 h-4" />
                            )}
                          </button>
                        </td>
                        <td className="px-4 py-3 font-medium text-slate-200">{kw.keyword}</td>
                        <td className="px-4 py-3 text-slate-300">
                          <span className="flex items-center gap-1">
                            <Globe className="w-3 h-3 text-slate-500" />
                            {formatNumber(kw.volume || 0)}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={DIFFICULTY_VARIANT[getDifficultyLevel(kw.difficulty || 0)]}>
                            {kw.difficulty || 0}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          <span className="flex items-center gap-1">
                            <DollarSign className="w-3 h-3 text-slate-500" />
                            {(kw.cpc || 0).toFixed(2)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-400 capitalize">{kw.intent || "—"}</td>
                        <td className="px-4 py-3">
                          {kw.cluster ? (
                            <Badge variant="outline">{kw.cluster}</Badge>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {activeTab === "clusters" && (
            <div className="space-y-4">
              {clusters.map(([cluster, kws]) => (
                <Card key={cluster}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <Target className="w-4 h-4 text-platform-400" />
                        {cluster}
                      </span>
                      <Badge variant="secondary">{kws.length} keywords</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {kws.map((kw) => (
                        <span
                          key={kw.id}
                          className="px-2 py-1 text-xs bg-surface-darker border border-surface-border rounded text-slate-300"
                        >
                          {kw.keyword}
                        </span>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {activeTab === "insights" && insights && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-slate-400">Total Keywords</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-slate-100">{insights.total}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                    <Globe className="w-4 h-4" />
                    Avg. Volume
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-slate-100">{formatNumber(Math.round(insights.avgVolume))}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" />
                    Avg. Difficulty
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-slate-100">{Math.round(insights.avgDifficulty)}</p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                    <DollarSign className="w-4 h-4" />
                    Avg. CPC
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold text-slate-100">${insights.avgCpc.toFixed(2)}</p>
                </CardContent>
              </Card>

              <Card className="md:col-span-2">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-slate-400">Difficulty Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center gap-4">
                    <div className="flex-1">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-emerald-400">Easy</span>
                        <span className="text-slate-400">{insights.easy}</span>
                      </div>
                      <div className="w-full h-3 bg-surface-darker rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${(insights.easy / insights.total) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-amber-400">Medium</span>
                        <span className="text-slate-400">{insights.medium}</span>
                      </div>
                      <div className="w-full h-3 bg-surface-darker rounded-full overflow-hidden">
                        <div
                          className="h-full bg-amber-500 rounded-full"
                          style={{ width: `${(insights.medium / insights.total) * 100}%` }}
                        />
                      </div>
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-red-400">Hard</span>
                        <span className="text-slate-400">{insights.hard}</span>
                      </div>
                      <div className="w-full h-3 bg-surface-darker rounded-full overflow-hidden">
                        <div
                          className="h-full bg-red-500 rounded-full"
                          style={{ width: `${(insights.hard / insights.total) * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="md:col-span-2">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm text-slate-400">Search Intent Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {Array.from(insights.intents.entries())
                      .sort((a, b) => b[1] - a[1])
                      .map(([intent, count]) => (
                        <div key={intent} className="flex items-center gap-3">
                          <span className="text-xs text-slate-300 w-24 capitalize">{intent}</span>
                          <div className="flex-1 h-2 bg-surface-darker rounded-full overflow-hidden">
                            <div
                              className="h-full bg-platform-500 rounded-full"
                              style={{ width: `${(count / insights.total) * 100}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-500 w-8 text-right">{count}</span>
                        </div>
                      ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}
