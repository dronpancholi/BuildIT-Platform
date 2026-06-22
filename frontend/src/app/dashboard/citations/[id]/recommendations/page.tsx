"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  RefreshCw,
  Sparkles,
  CheckCircle2,
  Filter,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { RecommendationCard } from "@/components/citations/recommendation-card";
import { CompetitorAnalysis } from "@/components/citations/competitor-analysis";
import { citationApi } from "@/lib/api";

interface Recommendation {
  site_id: string;
  site_name: string;
  site_url: string;
  site_category: string | null;
  site_importance: number | null;
  site_region: string | null;
  priority_score: number;
  priority: string;
  reasons: string[];
  scoring_breakdown: {
    location_score: number;
    authority_score: number;
    industry_score: number;
    competitor_score: number;
    tier_score: number;
  };
}

interface RecommendationSummary {
  total: number;
  pending: number;
  accepted: number;
  rejected: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
}

interface Competitor {
  id: string;
  competitor_name: string;
  competitor_domain: string | null;
}

interface Gap {
  site_id: string;
  site_name: string;
  site_url: string;
  site_importance: number | null;
  competitor_count: number;
  competitor_names: string[];
  is_client_listed: boolean;
}

export default function RecommendationsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [summary, setSummary] = useState<RecommendationSummary | null>(null);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [gaps, setGaps] = useState<Gap[]>([]);
  const [compStats, setCompStats] = useState({ unique_competitors: 0, total_citations: 0, unique_sites: 0 });
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [priorityFilter, setPriorityFilter] = useState<string>("all");
  const [activeTab, setActiveTab] = useState<"recommendations" | "competitors">("recommendations");

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Load existing recommendations
      try {
        const recResult = await fetch(
          `/api/v1/citations/projects/${projectId}/recommendations?tenant_id=00000000-0000-0000-0000-000000000001`,
          {
            headers: {
              Authorization: `Bearer ${typeof window !== "undefined" ? localStorage.getItem("token") || "" : ""}`,
            },
          }
        );
        const recData = await recResult.json();
        if (recData.success && recData.data) {
          setRecommendations(recData.data);
        }
      } catch {
        // Recommendations not generated yet
      }

      // Load competitors
      try {
        const compResult = await fetch(
          `/api/v1/citations/projects/${projectId}/competitors?tenant_id=00000000-0000-0000-0000-000000000001`,
          {
            headers: {
              Authorization: `Bearer ${typeof window !== "undefined" ? localStorage.getItem("token") || "" : ""}`,
            },
          }
        );
        const compData = await compResult.json();
        if (compData.success && compData.data) {
          setCompetitors(compData.data.competitors || []);
          setGaps(compData.data.gaps || []);
          setCompStats(compData.data.stats || { unique_competitors: 0, total_citations: 0, unique_sites: 0 });
        }
      } catch {
        // No competitors yet
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGenerate = async () => {
    try {
      setIsGenerating(true);
      setError(null);

      const result = await fetch(
        `/api/v1/citations/projects/${projectId}/recommendations?tenant_id=00000000-0000-0000-0000-000000000001`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${typeof window !== "undefined" ? localStorage.getItem("token") || "" : ""}`,
          },
          body: JSON.stringify({
            max_results: 50,
            force_regenerate: true,
          }),
        }
      );
      const data = await result.json();
      if (data.success && data.data) {
        setRecommendations(data.data.recommendations || []);
        setSummary(data.data.summary || null);
      } else {
        setError(data.error?.message || "Failed to generate recommendations");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to generate recommendations");
    } finally {
      setIsGenerating(false);
    }
  };

  const handleAccept = async (siteId: string) => {
    setRecommendations((prev) =>
      prev.map((r) => (r.site_id === siteId ? { ...r, priority: "accepted" } : r))
    );
  };

  const handleReject = async (siteId: string) => {
    setRecommendations((prev) =>
      prev.map((r) => (r.site_id === siteId ? { ...r, priority: "rejected" } : r))
    );
  };

  const handleAddCompetitor = async (name: string, domain: string) => {
    try {
      const result = await fetch(
        `/api/v1/citations/projects/${projectId}/competitors?tenant_id=00000000-0000-0000-0000-000000000001`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${typeof window !== "undefined" ? localStorage.getItem("token") || "" : ""}`,
          },
          body: JSON.stringify({ competitors: [{ name, domain }] }),
        }
      );
      const data = await result.json();
      if (data.success) {
        await loadData();
      }
    } catch (err: unknown) {
      console.error("Failed to add competitor:", err);
    }
  };

  const filteredRecommendations = recommendations.filter((r) => {
    if (priorityFilter === "all") return true;
    return r.priority === priorityFilter;
  });

  const priorityCounts = {
    critical: recommendations.filter((r) => r.priority === "critical").length,
    high: recommendations.filter((r) => r.priority === "high").length,
    medium: recommendations.filter((r) => r.priority === "medium").length,
    low: recommendations.filter((r) => r.priority === "low").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight font-mono">
              SITE_RECOMMENDATIONS
            </h1>
            <p className="text-slate-400 text-sm">Smart discovery engine for citation sites</p>
          </div>
        </div>
        <Button onClick={handleGenerate} disabled={isGenerating}>
          {isGenerating ? (
            <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Sparkles className="w-4 h-4 mr-2" />
          )}
          {isGenerating ? "Generating..." : "Generate"}
        </Button>
      </div>

      {isLoading ? (
        <LoadingSpinner size="lg" className="py-20" />
      ) : error ? (
        <Card className="border-red-500/20 bg-red-500/5">
          <CardContent className="p-6 text-center">
            <p className="text-red-400">{error}</p>
            <Button variant="outline" className="mt-4" onClick={loadData}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Tabs */}
          <div className="flex gap-2 border-b border-surface-border pb-2">
            <button
              onClick={() => setActiveTab("recommendations")}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                activeTab === "recommendations"
                  ? "bg-platform-600/10 text-platform-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Zap className="w-4 h-4 inline mr-1" />
              Recommendations ({recommendations.length})
            </button>
            <button
              onClick={() => setActiveTab("competitors")}
              className={`px-3 py-1.5 text-sm font-medium rounded transition-colors ${
                activeTab === "competitors"
                  ? "bg-platform-600/10 text-platform-400"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Competitors ({competitors.length})
            </button>
          </div>

          {activeTab === "recommendations" ? (
            <>
              {recommendations.length === 0 ? (
                <EmptyState
                  icon={<Sparkles className="w-8 h-8" />}
                  title="NO RECOMMENDATIONS YET"
                  description="Generate smart site recommendations based on your project profile and competitor data."
                  action={{ label: "Generate Recommendations", onClick: handleGenerate }}
                />
              ) : (
                <>
                  {/* Summary Cards */}
                  <div className="grid grid-cols-4 gap-3">
                    <Card className="border-surface-border bg-surface-card">
                      <CardContent className="p-3 text-center">
                        <p className="text-2xl font-bold text-slate-100">{recommendations.length}</p>
                        <p className="text-[10px] text-slate-500 uppercase">Total</p>
                      </CardContent>
                    </Card>
                    <Card className="border-red-500/20 bg-red-500/5">
                      <CardContent className="p-3 text-center">
                        <p className="text-2xl font-bold text-red-400">{priorityCounts.critical}</p>
                        <p className="text-[10px] text-slate-500 uppercase">Critical</p>
                      </CardContent>
                    </Card>
                    <Card className="border-orange-500/20 bg-orange-500/5">
                      <CardContent className="p-3 text-center">
                        <p className="text-2xl font-bold text-orange-400">{priorityCounts.high}</p>
                        <p className="text-[10px] text-slate-500 uppercase">High</p>
                      </CardContent>
                    </Card>
                    <Card className="border-yellow-500/20 bg-yellow-500/5">
                      <CardContent className="p-3 text-center">
                        <p className="text-2xl font-bold text-yellow-400">{priorityCounts.medium}</p>
                        <p className="text-[10px] text-slate-500 uppercase">Medium</p>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Filters */}
                  <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-slate-500" />
                    {["all", "critical", "high", "medium", "low"].map((p) => (
                      <Button
                        key={p}
                        size="sm"
                        variant={priorityFilter === p ? "default" : "outline"}
                        className="h-7 text-xs"
                        onClick={() => setPriorityFilter(p)}
                      >
                        {p.charAt(0).toUpperCase() + p.slice(1)}
                      </Button>
                    ))}
                  </div>

                  {/* Recommendation List */}
                  <div className="space-y-2">
                    {filteredRecommendations.map((rec) => (
                      <RecommendationCard
                        key={rec.site_id}
                        recommendation={rec}
                        onAccept={handleAccept}
                        onReject={handleReject}
                      />
                    ))}
                  </div>
                </>
              )}
            </>
          ) : (
            <CompetitorAnalysis
              competitors={competitors}
              gaps={gaps}
              stats={compStats}
              onAddCompetitor={handleAddCompetitor}
            />
          )}
        </>
      )}
    </div>
  );
}
