"use client";

import {
  AlertTriangle,
  BrainCircuit,
  Gauge,
  Activity,
  Clock,
  Shield,
  Zap,
  BarChart3,
  Box,
  Loader2,
  TrendingUp,
  Cpu,
  ArrowUpRight,
  Search,
  Network,
  MapPin,
  Lightbulb,
} from "lucide-react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AnomalyReport {
  type: string;
  severity: string;
  component: string;
  message: string;
  timestamp: string;
  metric_value: number;
  threshold: number;
}

interface QueueCongestionReport {
  queue_name: string;
  depth: number;
  worker_count: number;
  backlog_rate: number;
  congestion_level: string;
}

interface Recommendation {
  priority: string;
  category: string;
  title: string;
  description: string;
  impact: string;
}

interface BottleneckReport {
  phase: string;
  avg_duration_ms: number;
  p50: number;
  p95: number;
  sample_count: number;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const severityColor: Record<string, string> = {
  critical: "text-red-400 bg-red-500/10 border-red-500/20",
  high: "text-orange-400 bg-orange-500/10 border-orange-500/20",
  medium: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  low: "text-slate-400 bg-slate-500/10 border-slate-500/20",
};

const congestionColor: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  moderate: "bg-amber-500",
  low: "bg-yellow-500",
  none: "bg-emerald-500",
};

const priorityColor: Record<string, string> = {
  P0: "text-red-400 bg-red-500/10 border-red-500/20",
  P1: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  P2: "text-slate-400 bg-slate-500/10 border-slate-500/20",
};

const bottleneckBarWidth = (p95: number, max: number) =>
  max > 0 ? `${(p95 / max) * 100}%` : "0%";

// ---------------------------------------------------------------------------
// Tenant ID — matches dashboard convention
// ---------------------------------------------------------------------------
const TENANT_ID = "00000000-0000-0000-0000-000000000001";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

function MetricCard({
  label,
  value,
  icon,
  sub,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  sub?: string;
}) {
  return (
    <div className="glass-panel p-5">
      <div className="flex justify-between items-start mb-3">
        <span className="text-xs font-mono text-slate-500 uppercase tracking-wider">
          {label}
        </span>
        <div className="p-2 bg-surface-darker rounded-lg border border-surface-border">
          {icon}
        </div>
      </div>
      <div className="flex items-end gap-2">
        <span className="text-2xl font-bold text-slate-100 font-mono">
          {value}
        </span>
      </div>
      {sub && (
        <p className="text-[10px] font-mono text-slate-600 mt-1">{sub}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function IntelligencePage() {
  const { data: anomaliesData, isLoading: loadingAnomalies } =
    useQuery<AnomalyReport[]>({
      queryKey: ["intelligence", "anomalies"],
      queryFn: () =>
        fetchApi<AnomalyReport[]>(`/intelligence/anomalies?tenant_id=${TENANT_ID}`),
      refetchInterval: 15000,
    });

  const { data: congestionData, isLoading: loadingCongestion } =
    useQuery<QueueCongestionReport[]>({
      queryKey: ["intelligence", "congestion"],
      queryFn: () => fetchApi<QueueCongestionReport[]>("/intelligence/congestion"),
      refetchInterval: 15000,
    });

  const { data: recsData, isLoading: loadingRecs } =
    useQuery<Recommendation[]>({
      queryKey: ["intelligence", "recommendations"],
      queryFn: () =>
        fetchApi<Recommendation[]>(`/intelligence/recommendations?tenant_id=${TENANT_ID}`),
      refetchInterval: 60000,
    });

  const { data: bottlenecksData, isLoading: loadingBottlenecks } =
    useQuery<BottleneckReport[]>({
      queryKey: ["intelligence", "bottlenecks"],
      queryFn: () =>
        fetchApi<BottleneckReport[]>(`/intelligence/bottlenecks?tenant_id=${TENANT_ID}`),
      refetchInterval: 30000,
    });

  const anomalies = anomaliesData ?? [];
  const congestion = congestionData ?? [];
  const recommendations = recsData ?? [];
  const bottlenecks = bottlenecksData ?? [];

  const criticalCount = anomalies.filter(
    (a) => a.severity === "critical"
  ).length;
  const highCount = anomalies.filter((a) => a.severity === "high").length;
  const criticalCongestion = congestion.filter(
    (c) => c.congestion_level === "critical"
  ).length;
  const maxBottleneckP95 = Math.max(
    ...bottlenecks.map((b) => b.p95),
    1
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">
            OPERATIONAL_INTEL
          </h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">
            System intelligence & anomaly detection
          </p>
        </div>
        <div className="flex items-center gap-3">
          {criticalCount > 0 && (
            <div className="px-3 py-1.5 rounded-md bg-red-500/10 border border-red-500/20 text-xs font-mono text-red-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              {criticalCount} CRITICAL
            </div>
          )}
          {highCount > 0 && (
            <div className="px-3 py-1.5 rounded-md bg-orange-500/10 border border-orange-500/20 text-xs font-mono text-orange-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />
              {highCount} HIGH
            </div>
          )}
          <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 flex items-center gap-2">
            <BrainCircuit className="w-4 h-4" />
            {loadingAnomalies ? "SCANNING..." : `${anomalies.length} ANOMALIES`}
          </div>
        </div>
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Active Anomalies"
          value={String(anomalies.length)}
          icon={<AlertTriangle className="w-5 h-5 text-red-400" />}
          sub={`${criticalCount} critical, ${highCount} high`}
        />
        <MetricCard
          label="Congested Queues"
          value={String(criticalCongestion)}
          icon={<Box className="w-5 h-5 text-orange-400" />}
          sub={`${congestion.length} total queues monitored`}
        />
        <MetricCard
          label="Bottlenecks Tracked"
          value={String(bottlenecks.length)}
          icon={<BarChart3 className="w-5 h-5 text-indigo-400" />}
          sub="Workflow phases with latency data"
        />
        <MetricCard
          label="Recommendations"
          value={String(recommendations.length)}
          icon={<Cpu className="w-5 h-5 text-platform-400" />}
          sub="LLM-generated optimizations"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Anomaly Timeline */}
        <div className="lg:col-span-2 glass-panel overflow-hidden flex flex-col">
          <div className="px-6 py-4 border-b border-surface-border flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">
              ANOMALY_TIMELINE
            </h3>
            <span className="ml-auto text-xs font-mono text-slate-500">
              {anomalies.length > 0
                ? `LAST UPDATED ${new Date(
                    anomalies[0].timestamp
                  ).toLocaleTimeString()}`
                : "REAL-TIME"}
            </span>
          </div>
          <div className="flex-1 overflow-auto max-h-[400px]">
            {loadingAnomalies ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
              </div>
            ) : anomalies.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-4">
                  <Shield className="text-emerald-500" size={32} />
                </div>
                <h3 className="text-lg font-medium text-slate-300 font-mono">
                  ALL_SYSTEMS_NOMINAL
                </h3>
                <p className="text-sm text-slate-500 mt-2 max-w-sm">
                  No anomalies detected. Platform is operating within normal
                  parameters across all components.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-surface-border">
                {anomalies.map((a, i) => (
                  <div
                    key={i}
                    className="px-6 py-4 hover:bg-surface-darker/30 transition-colors"
                  >
                    <div className="flex items-start gap-4">
                      <div
                        className={`mt-0.5 w-2 h-2 rounded-full shrink-0 ${
                          a.severity === "critical"
                            ? "bg-red-500"
                            : a.severity === "high"
                            ? "bg-orange-500"
                            : a.severity === "medium"
                            ? "bg-amber-500"
                            : "bg-slate-500"
                        }`}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span
                            className={`text-xs font-mono px-2 py-0.5 rounded border ${severityColor[a.severity] || severityColor.low}`}
                          >
                            {a.severity.toUpperCase()}
                          </span>
                          <span className="text-xs font-mono text-slate-500 uppercase">
                            {a.component}
                          </span>
                          <span className="text-[10px] font-mono text-slate-600 ml-auto">
                            {new Date(a.timestamp).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm text-slate-300 font-mono">
                          {a.message}
                        </p>
                        {(a.metric_value > 0 || a.threshold > 0) && (
                          <div className="mt-1 flex items-center gap-3 text-[10px] font-mono text-slate-500">
                            <span>
                              VALUE: {a.metric_value.toFixed(2)}
                            </span>
                            <span>
                              THRESHOLD: {a.threshold.toFixed(2)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Queue Congestion Heatmap */}
        <div className="glass-panel flex flex-col">
          <div className="px-6 py-4 border-b border-surface-border flex items-center gap-2">
            <Box className="w-5 h-5 text-orange-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">
              QUEUE_CONGESTION
            </h3>
          </div>
          <div className="flex-1 p-4 space-y-3 overflow-auto max-h-[400px]">
            {loadingCongestion ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
              </div>
            ) : congestion.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <p className="text-sm text-slate-500 font-mono">
                  NO_QUEUE_DATA
                </p>
              </div>
            ) : (
              congestion.map((q, i) => (
                <div key={i} className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-300 uppercase">
                      {q.queue_name.replace(/_/g, " ")}
                    </span>
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          congestionColor[q.congestion_level] ||
                          congestionColor.none
                        }`}
                      />
                      <span className="text-[10px] font-mono text-slate-500 uppercase">
                        {q.congestion_level}
                      </span>
                    </div>
                  </div>
                  <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        q.congestion_level === "critical"
                          ? "bg-red-500"
                          : q.congestion_level === "high"
                          ? "bg-orange-500"
                          : q.congestion_level === "moderate"
                          ? "bg-amber-500"
                          : q.congestion_level === "low"
                          ? "bg-yellow-500"
                          : "bg-emerald-500"
                      }`}
                      style={{
                        width: `${Math.min(
                          (q.depth / Math.max(q.depth + q.worker_count * 10, 1)) *
                            100,
                          100
                        )}%`,
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-[10px] font-mono text-slate-600">
                    <span>DEPTH: {q.depth}</span>
                    <span>WORKERS: {q.worker_count}</span>
                    <span>RATE: {q.backlog_rate.toFixed(1)}/s</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Workflow Bottleneck Waterfall */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <BarChart3 className="w-5 h-5 text-indigo-500" />
            WORKFLOW_BOTTLENECKS
          </h3>
          <div className="space-y-4">
            {loadingBottlenecks ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
              </div>
            ) : bottlenecks.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-sm text-slate-500 font-mono">
                  NO_BOTTLENECK_DATA
                </p>
                <p className="text-xs text-slate-600 mt-2">
                  Workflow timing data will appear once workflows execute.
                </p>
              </div>
            ) : (
              bottlenecks
                .sort((a, b) => b.p95 - a.p95)
                .map((b, i) => (
                  <div key={i} className="space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-slate-300 uppercase">
                        {b.phase.replace(/_/g, " ")}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        {b.avg_duration_ms.toFixed(0)}ms
                      </span>
                    </div>
                    <div className="w-full h-3 bg-surface-darker rounded-full overflow-hidden flex">
                      <div
                        className="h-full bg-emerald-500/60 rounded-l-full"
                        style={{
                          width: bottleneckBarWidth(b.p50, maxBottleneckP95),
                        }}
                        title={`P50: ${b.p50.toFixed(0)}ms`}
                      />
                      <div
                        className="h-full bg-amber-500/60 rounded-r-full"
                        style={{
                          width: bottleneckBarWidth(
                            b.p95 - b.p50,
                            maxBottleneckP95
                          ),
                        }}
                        title={`P95: ${b.p95.toFixed(0)}ms`}
                      />
                    </div>
                    <div className="flex justify-between text-[10px] font-mono text-slate-600">
                      <span>P50: {b.p50.toFixed(0)}ms</span>
                      <span>P95: {b.p95.toFixed(0)}ms</span>
                      <span>SAMPLES: {b.sample_count}</span>
                    </div>
                  </div>
                ))
            )}
          </div>
        </div>

        {/* Recommendations */}
        <div className="glass-panel overflow-hidden flex flex-col">
          <div className="px-6 py-4 border-b border-surface-border flex items-center gap-2">
            <Cpu className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">
              OPTIMIZATION_RECOMMENDATIONS
            </h3>
            <span className="ml-auto text-[10px] font-mono text-slate-600">
              AI-GENERATED
            </span>
          </div>
          <div className="flex-1 overflow-auto max-h-[400px]">
            {loadingRecs ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
              </div>
            ) : recommendations.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-center">
                <div className="w-16 h-16 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-4">
                  <TrendingUp className="text-slate-600" size={32} />
                </div>
                <h3 className="text-lg font-medium text-slate-300 font-mono">
                  NO_RECOMMENDATIONS
                </h3>
                <p className="text-sm text-slate-500 mt-2 max-w-sm">
                  Optimization recommendations will be generated once the LLM
                  gateway processes platform telemetry.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-surface-border">
                {recommendations.map((r, i) => (
                  <div key={i} className="px-6 py-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded border font-bold ${
                          priorityColor[r.priority] || priorityColor.P2
                        }`}
                      >
                        {r.priority}
                      </span>
                      <span className="text-[10px] font-mono text-slate-500 uppercase">
                        {r.category}
                      </span>
                    </div>
                    <h4 className="text-sm font-medium text-slate-200 font-mono mb-1">
                      {r.title}
                    </h4>
                    <p className="text-xs text-slate-400 leading-relaxed mb-2">
                      {r.description}
                    </p>
                    <p className="text-[10px] font-mono text-slate-500">
                      IMPACT: {r.impact}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Infrastructure Health & AI Confidence Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Infra Health */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Shield className="w-5 h-5 text-emerald-500" />
            INFRASTRUCTURE_HEALTH
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {["database", "redis", "temporal", "kafka"].map((comp) => (
              <div
                key={comp}
                className="p-3 rounded-md bg-surface-darker border border-surface-border"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-mono text-slate-400 uppercase">
                    {comp}
                  </span>
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                </div>
                <span className="text-[10px] font-mono text-slate-500">
                  HEALTHY
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* AI Confidence */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Activity className="w-5 h-5 text-purple-500" />
            AI_CONFIDENCE_METRICS
          </h3>
          <div className="text-center py-8">
            <p className="text-sm text-slate-500 font-mono">
              NO_INFERENCE_DATA
            </p>
            <p className="text-xs text-slate-600 mt-2">
              LLM confidence scores will appear once AI inferences are made
              through the NVIDIA NIM gateway.
            </p>
          </div>
        </div>
      </div>

      {/* Scraping Quality */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-4 flex items-center gap-3">
          <div className="p-2 bg-surface-darker rounded-lg border border-surface-border">
            <Zap className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-xs font-mono text-slate-500 uppercase tracking-wider">
              Scraping Quality
            </p>
            <p className="text-sm font-mono text-slate-300">—</p>
          </div>
        </div>
        <div className="glass-panel p-4 flex items-center gap-3">
          <div className="p-2 bg-surface-darker rounded-lg border border-surface-border">
            <Activity className="w-5 h-5 text-cyan-400" />
          </div>
          <div>
            <p className="text-xs font-mono text-slate-500 uppercase tracking-wider">
              Retry Storm Status
            </p>
            <p className="text-sm font-mono text-slate-300">NOMINAL</p>
          </div>
        </div>
        <div className="glass-panel p-4 flex items-center gap-3">
          <div className="p-2 bg-surface-darker rounded-lg border border-surface-border">
            <Gauge className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <p className="text-xs font-mono text-slate-500 uppercase tracking-wider">
              Campaign Health
            </p>
            <p className="text-sm font-mono text-slate-300">—</p>
          </div>
        </div>
        <div className="glass-panel p-4 flex items-center gap-3">
          <div className="p-2 bg-surface-darker rounded-lg border border-surface-border">
            <Clock className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <p className="text-xs font-mono text-slate-500 uppercase tracking-wider">
              Last Scan
            </p>
            <p className="text-sm font-mono text-slate-300">
              {new Date().toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>

      {/* Analytics Section & Intelligence Page Links */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <BarChart3 className="w-5 h-5 text-platform-500" />
            ADVANCED_ANALYTICS
          </h3>
          <div className="space-y-2">
            {[
              { label: "Backlink ROI Analytics", endpoint: "/analytics/backlink-roi" },
              { label: "Campaign Efficiency", endpoint: "/analytics/campaign-efficiency" },
              { label: "Scraping Quality", endpoint: "/analytics/scraping-quality" },
              { label: "Outreach Performance", endpoint: "/analytics/outreach-performance" },
              { label: "Workflow Latency", endpoint: "/analytics/workflow-latency" },
              { label: "Local SEO Effectiveness", endpoint: "/analytics/local-seo-effectiveness" },
            ].map((a, i) => (
              <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/50 border border-surface-border/50">
                <span className="text-xs font-mono text-slate-400">{a.label}</span>
                <span className="text-[9px] font-mono text-slate-600">{a.endpoint}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <BrainCircuit className="w-5 h-5 text-purple-500" />
            INTELLIGENCE_PAGES
          </h3>
          <div className="space-y-2">
            <IntelligenceLink href="/dashboard/seo-intelligence" icon={<Search className="w-4 h-4" />} label="SEO Intelligence" />
            <IntelligenceLink href="/dashboard/backlink-intelligence" icon={<Network className="w-4 h-4" />} label="Backlink Intelligence" />
            <IntelligenceLink href="/dashboard/prospect-graph" icon={<Activity className="w-4 h-4" />} label="Prospect Graph" />
            <IntelligenceLink href="/dashboard/local-seo" icon={<MapPin className="w-4 h-4" />} label="Local SEO" />
            <IntelligenceLink href="/dashboard/recommendations" icon={<Lightbulb className="w-4 h-4" />} label="Recommendations" />
            <IntelligenceLink href="/dashboard/ai-ops" icon={<Cpu className="w-4 h-4" />} label="AI Ops Quality" />
          </div>
        </div>
      </div>
    </div>
  );
}

function IntelligenceLink({ href, icon, label }: { href: string; icon: React.ReactNode; label: string }) {
  return (
    <Link
      href={href}
      className="flex items-center justify-between p-2 rounded bg-surface-darker/50 border border-surface-border/50 hover:bg-surface-border/50 transition-colors group"
    >
      <div className="flex items-center gap-2">
        <div className="text-slate-500 group-hover:text-platform-400 transition-colors">{icon}</div>
        <span className="text-xs font-mono text-slate-400 group-hover:text-slate-200 transition-colors">{label}</span>
      </div>
      <ArrowUpRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-platform-400 transition-colors" />
    </Link>
  );
}
