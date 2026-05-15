"use client";

import { Cpu, Clock, AlertTriangle, Zap, BarChart3, Loader2, Shield, TrendingUp, Layers, MessageSquare, Activity } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { HealthResponse } from "@/types/api";

interface AIQualityDashboard {
  avg_confidence_score: number;
  hallucination_rate_trend: { date: string; hallucination_rate: number; avg_confidence: number }[];
  quality_score_by_category: Record<string, number>;
  schema_repair_rate: number;
  fallback_model_usage_rate: number;
}

interface RecommendationQuality {
  total_recommendations: number;
  implementation_rate: number;
  positive_outcome_rate: number;
  best_performing_categories: { category: string; positive_rate: number }[];
}

function scoreColor(score: number): string {
  if (score >= 0.7) return "text-emerald-400";
  if (score >= 0.5) return "text-amber-400";
  return "text-red-400";
}

function scoreBg(score: number): string {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.5) return "bg-amber-500";
  return "bg-red-500";
}

export default function AiOpsPage() {
  const { data: healthData, isLoading } = useQuery<HealthResponse>({
    queryKey: ["health"],
    queryFn: () => fetchApi("/health"),
    refetchInterval: 10000,
  });

  const { data: qualityDashboard, isLoading: loadingQuality } = useQuery<AIQualityDashboard>({
    queryKey: ["ai-quality", "dashboard", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/ai-quality/dashboard?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 30000,
  });

  const { data: recQuality, isLoading: loadingRecs } = useQuery<RecommendationQuality>({
    queryKey: ["ai-quality", "recommendation-quality"],
    queryFn: () => fetchApi("/ai-quality/recommendation-quality"),
    refetchInterval: 60000,
  });

  const quality = qualityDashboard;
  const recs = recQuality;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">AI_OPS</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Inference Performance & Quality</p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400">
          <Cpu className="w-4 h-4" />
          {isLoading ? "LOADING..." : healthData ? "GATEWAY_CONNECTED" : "GATEWAY_OFFLINE"}
        </div>
      </div>

      {/* Quality KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Avg Confidence"
          value={quality ? `${Math.round(quality.avg_confidence_score * 100)}%` : "—"}
          icon={<Shield className="w-5 h-5 text-platform-400" />}
        />
        <MetricCard
          label="Schema Repair Rate"
          value={quality ? `${Math.round(quality.schema_repair_rate * 100)}%` : "—"}
          icon={<Activity className="w-5 h-5 text-amber-400" />}
        />
        <MetricCard
          label="Fallback Rate"
          value={quality ? `${Math.round(quality.fallback_model_usage_rate * 100)}%` : "—"}
          icon={<AlertTriangle className="w-5 h-5 text-orange-400" />}
        />
        <MetricCard
          label="Recommendations"
          value={recs ? String(recs.total_recommendations) : "—"}
          icon={<BarChart3 className="w-5 h-5 text-indigo-400" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI Quality Dashboard */}
        <div className="lg:col-span-2 glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Cpu className="w-5 h-5 text-platform-500" />
            AI_QUALITY_DASHBOARD
          </h3>
          {loadingQuality ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
            </div>
          ) : quality ? (
            <div className="space-y-6">
              {/* Quality Scores by Category */}
              <div>
                <p className="text-xs font-mono text-slate-500 uppercase mb-3">Quality Score by Category</p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {Object.entries(quality.quality_score_by_category).map(([cat, score]) => (
                    <div key={cat} className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border/50">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] font-mono text-slate-400 uppercase">{cat}</span>
                        <span className={`text-xs font-mono font-bold ${scoreColor(score)}`}>{Math.round(score * 100)}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-surface-darker rounded-full overflow-hidden">
                        <div className={`h-full rounded-full ${scoreBg(score)}`} style={{ width: `${score * 100}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Hallucination Rate Trend */}
              <div>
                <p className="text-xs font-mono text-slate-500 uppercase mb-3">Hallucination Trend (7 days)</p>
                <div className="space-y-2">
                  {quality.hallucination_rate_trend.map((day, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-[10px] font-mono text-slate-500 w-24">{day.date}</span>
                      <div className="flex-1 h-2 bg-surface-darker rounded-full overflow-hidden">
                        <div className="h-full bg-amber-500 rounded-full" style={{ width: `${day.hallucination_rate * 100}%` }} />
                      </div>
                      <span className="text-[10px] font-mono text-slate-500 w-16 text-right">{Math.round(day.hallucination_rate * 100)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Operational Metrics */}
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border/50">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Schema Repair Rate</p>
                  <p className={`text-lg font-bold font-mono ${scoreColor(1 - quality.schema_repair_rate)}`}>
                    {Math.round(quality.schema_repair_rate * 100)}%
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-surface-darker/50 border border-surface-border/50">
                  <p className="text-[10px] font-mono text-slate-500 uppercase">Fallback Usage</p>
                  <p className={`text-lg font-bold font-mono ${scoreColor(1 - quality.fallback_model_usage_rate)}`}>
                    {Math.round(quality.fallback_model_usage_rate * 100)}%
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-500 font-mono">NO_QUALITY_DATA</div>
          )}
        </div>

        {/* Recommendation Quality & Clustering */}
        <div className="space-y-6">
          {/* Recommendation Quality */}
          <div className="glass-panel p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
              <TrendingUp className="w-5 h-5 text-emerald-500" />
              RECOMMENDATION_QUALITY
            </h3>
            {loadingRecs ? (
              <div className="flex justify-center py-6">
                <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
              </div>
            ) : recs ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50 text-center">
                    <p className="text-lg font-bold font-mono text-slate-200">{recs.total_recommendations}</p>
                    <p className="text-[9px] font-mono text-slate-500 uppercase">Total</p>
                  </div>
                  <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50 text-center">
                    <p className={`text-lg font-bold font-mono ${scoreColor(recs.implementation_rate)}`}>
                      {Math.round(recs.implementation_rate * 100)}%
                    </p>
                    <p className="text-[9px] font-mono text-slate-500 uppercase">Implemented</p>
                  </div>
                </div>
                <div className="p-2 bg-surface-darker/50 rounded border border-surface-border/50 text-center">
                  <p className={`text-lg font-bold font-mono ${scoreColor(recs.positive_outcome_rate)}`}>
                    {Math.round(recs.positive_outcome_rate * 100)}%
                  </p>
                  <p className="text-[9px] font-mono text-slate-500 uppercase">Positive Outcomes</p>
                </div>
                {recs.best_performing_categories.length > 0 && (
                  <div>
                    <p className="text-[10px] font-mono text-slate-500 uppercase mb-1">Best Categories</p>
                    {recs.best_performing_categories.slice(0, 3).map((cat, i) => (
                      <div key={i} className="flex items-center justify-between text-[10px] font-mono text-slate-400 p-1">
                        <span>{cat.category}</span>
                        <span className={scoreColor(cat.positive_rate)}>{Math.round(cat.positive_rate * 100)}%</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-6 text-slate-500 font-mono">NO_REC_DATA</div>
            )}
          </div>

          {/* Clustering Quality */}
          <div className="glass-panel p-6">
            <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
              <Layers className="w-5 h-5 text-purple-500" />
              CLUSTERING_QUALITY
            </h3>
            <div className="text-center py-6">
              <p className="text-sm text-slate-500 font-mono">NO_CLUSTER_DATA</p>
              <p className="text-xs text-slate-600 mt-2">
                Submit clustering jobs via POST /ai-quality/clustering-quality with cluster data.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Outreach Quality */}
      <div className="glass-panel p-6">
        <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
          <MessageSquare className="w-5 h-5 text-cyan-500" />
          OUTREACH_QUALITY_TRENDS
        </h3>
        <div className="text-center py-8">
          <p className="text-sm text-slate-500 font-mono">NO_OUTREACH_QUALITY_DATA</p>
          <p className="text-xs text-slate-600 mt-2">
            Score outreach emails via POST /ai-quality/outreach-quality with email content and prospect data.
          </p>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="glass-panel p-5">
      <div className="flex justify-between items-start mb-3">
        <span className="text-xs font-mono text-slate-500 uppercase tracking-wider">{label}</span>
        <div className="p-2 bg-surface-darker rounded-lg border border-surface-border">{icon}</div>
      </div>
      <div className="flex items-end gap-2">
        <span className="text-2xl font-bold text-slate-100 font-mono">{value}</span>
      </div>
    </div>
  );
}
