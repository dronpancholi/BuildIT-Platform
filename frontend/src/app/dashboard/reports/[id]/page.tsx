"use client";

import { useParams, useRouter } from "next/navigation";
import { useMemo } from "react";
import { useApiDetail } from "@/services/hooks";
import { ENDPOINTS } from "@/services/endpoints";
import { ReportDetail, ReportCampaign, ReportProspect, ReportEmail, ReportAcquiredLink, ReportKeyword } from "@/types/models";
import { ErrorState, LoadingState } from "@/components/ui/error-state";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDate } from "@/lib/utils";
import { safeArr, safeNum, safeStr, safeObj, safeUpper, safeSlice, safeLocale } from "@/lib/safe";
import {
  ArrowLeft, FileDown, Download,
  TrendingUp, Search, Link2, Activity,
} from "lucide-react";
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area,
  PieChart, Pie, Cell,
  ResponsiveContainer, XAxis, YAxis, Tooltip, Legend, CartesianGrid,
} from "recharts";

const CHART_COLORS = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#3b82f6", "#8b5cf6"];

interface ChartCardProps {
  title: string;
  children: React.ReactNode;
}

function ChartCard({ title, children }: ChartCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-mono">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[280px]">
          {children}
        </div>
      </CardContent>
    </Card>
  );
}

interface SummaryCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  color: string;
}

function SummaryCard({ icon: Icon, label, value, color }: SummaryCardProps) {
  return (
    <div className="glass-panel p-4 rounded-xl border border-surface-border">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-[10px] font-mono text-slate-500 uppercase">{label}</span>
      </div>
      <p className="text-2xl font-bold font-mono text-slate-100">{value}</p>
    </div>
  );
}

function formatNumber(value: number): string {
  if (!Number.isFinite(value)) return "0";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return safeLocale(value);
  return String(value);
}

function formatPercent(value: number): string {
  if (!Number.isFinite(value)) return "0%";
  return `${(value * 100).toFixed(1)}%`;
}

function buildCampaignPerformanceData(report: ReportDetail) {
  return safeArr<ReportCampaign>(report.campaigns).map((c) => ({
    name: c.name,
    acquired: c.acquired_link_count,
    target: c.target_link_count,
    prospects: c.total_prospects,
  }));
}

function buildCampaignHealthData(report: ReportDetail) {
  return safeArr<ReportCampaign>(report.campaigns).map((c) => ({
    name: c.name,
    health: Math.round(safeNum(c.health_score) * 100),
  }));
}

function buildProspectStatusData(report: ReportDetail) {
  const counts = new Map<string, number>();
  for (const p of safeArr<ReportProspect>(report.prospects)) {
    counts.set(p.status, (counts.get(p.status) ?? 0) + 1);
  }
  return Array.from(counts.entries()).map(([name, value]) => ({ name, value }));
}

function buildOutreachStatusData(report: ReportDetail) {
  const counts = new Map<string, number>();
  for (const e of safeArr<ReportEmail>(report.emails)) {
    counts.set(e.status, (counts.get(e.status) ?? 0) + 1);
  }
  return Array.from(counts.entries()).map(([name, value]) => ({ name, value }));
}

function buildAcquiredLinksByCampaignData(report: ReportDetail) {
  const counts = new Map<string, number>();
  for (const link of safeArr<ReportAcquiredLink>(report.acquired_links)) {
    const source = link.source_url || "unknown";
    counts.set(source, (counts.get(source) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);
}

function buildKeywordDifficultyData(report: ReportDetail) {
  const buckets = [
    { name: "0-20", min: 0, max: 20, value: 0 },
    { name: "21-40", min: 21, max: 40, value: 0 },
    { name: "41-60", min: 41, max: 60, value: 0 },
    { name: "61-80", min: 61, max: 80, value: 0 },
    { name: "81-100", min: 81, max: 100, value: 0 },
  ];
  for (const k of safeArr<ReportKeyword>(report.keywords)) {
    const bucket = buckets.find((b) => safeNum(k.difficulty) >= b.min && safeNum(k.difficulty) <= b.max);
    if (bucket) bucket.value += 1;
  }
  return buckets.map(({ name, value }) => ({ name, value }));
}

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const reportId = params.id as string;

  const { data: report, isLoading, error } = useApiDetail<ReportDetail>(ENDPOINTS.REPORTS, reportId);

  const campaignPerformance = useMemo(
    () => (report ? buildCampaignPerformanceData(report) : []),
    [report]
  );
  const campaignHealth = useMemo(
    () => (report ? buildCampaignHealthData(report) : []),
    [report]
  );
  const prospectStatus = useMemo(
    () => (report ? buildProspectStatusData(report) : []),
    [report]
  );
  const outreachStatus = useMemo(
    () => (report ? buildOutreachStatusData(report) : []),
    [report]
  );
  const acquiredLinksBySource = useMemo(
    () => (report ? buildAcquiredLinksByCampaignData(report) : []),
    [report]
  );
  const keywordDifficulty = useMemo(
    () => (report ? buildKeywordDifficultyData(report) : []),
    [report]
  );

  if (isLoading) {
    return (
      <div className="p-6">
        <LoadingState message="Loading report..." size="lg" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-6">
        <button onClick={() => router.push("/dashboard/reports")} className="flex items-center gap-2 text-slate-500 hover:text-slate-300 mb-4">
          <ArrowLeft className="w-4 h-4" /> Back to Reports
        </button>
        <ErrorState error={error} message="Failed to load report" onRetry={() => window.location.reload()} />
      </div>
    );
  }

  const reportTypeVariant = (type: string) => {
    if (type === "full") return "default" as const;
    if (type === "performance") return "success" as const;
    if (type === "backlink") return "warning" as const;
    return "secondary" as const;
  };

  const metrics = report.metrics;
  const hasAnyChartData =
    campaignPerformance.length > 0 ||
    campaignHealth.length > 0 ||
    prospectStatus.length > 0 ||
    outreachStatus.length > 0 ||
    acquiredLinksBySource.length > 0 ||
    keywordDifficulty.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => router.push("/dashboard/reports")} className="p-2 hover:bg-surface-border rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-100 tracking-tight font-mono">
                {report.title || `Report ${safeSlice(report.id, 0, 8)}`}
              </h1>
              <Badge variant={reportTypeVariant(report.report_type)}>{safeUpper(report.report_type)}</Badge>
            </div>
            <p className="text-xs font-mono text-slate-500 mt-1">
              Generated {formatDate(report.generated_at || report.created_at)}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => {
            const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${safeStr(report.id)}.json`;
            a.click();
            URL.revokeObjectURL(url);
          }}>
            <FileDown className="w-3.5 h-3.5" /> JSON
          </Button>
          <Button variant="outline" size="sm" onClick={() => {
            const rows = ["metric,value"];
            const metrics = safeObj(report.metrics);
            Object.entries(metrics).forEach(([k, v]) => rows.push(`${k},${typeof v === "object" ? JSON.stringify(v) : v}`));
            const blob = new Blob([rows.join("\n")], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `${safeStr(report.id)}.csv`;
            a.click();
            URL.revokeObjectURL(url);
          }}>
            <Download className="w-3.5 h-3.5" /> CSV
          </Button>
        </div>
      </div>

      {report.executive_summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-mono">Executive Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-300 leading-relaxed whitespace-pre-wrap">
              {report.executive_summary}
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <SummaryCard
          icon={Search}
          label="Total Keywords"
          value={formatNumber(metrics.total_keywords)}
          color="text-platform-400"
        />
        <SummaryCard
          icon={Link2}
          label="Acquired Links"
          value={`${formatNumber(metrics.links_acquired)} / ${formatNumber(metrics.target_links)}`}
          color="text-emerald-400"
        />
        <SummaryCard
          icon={TrendingUp}
          label="Acquisition Rate"
          value={formatPercent(metrics.acquisition_rate)}
          color="text-blue-400"
        />
        <SummaryCard
          icon={Activity}
          label="Reply Rate"
          value={formatPercent(metrics.reply_rate)}
          color="text-amber-400"
        />
      </div>

      {hasAnyChartData ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ChartCard title="Campaign Link Performance">
            {campaignPerformance.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={campaignPerformance}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="acquired" fill="#10b981" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="target" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No campaign data"
                description="This report does not include campaign performance data."
              />
            )}
          </ChartCard>

          <ChartCard title="Campaign Health Scores">
            {campaignHealth.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={campaignHealth} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10, fill: "#64748b" }} />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} width={100} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="health" fill="#6366f1" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No campaign data"
                description="This report does not include campaign health scores."
              />
            )}
          </ChartCard>

          <ChartCard title="Prospect Status Distribution">
            {prospectStatus.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={prospectStatus}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                  >
                    {prospectStatus.map((_, index) => (
                      <Cell key={`prospect-cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No prospect data"
                description="This report does not include prospect status information."
              />
            )}
          </ChartCard>

          <ChartCard title="Outreach Thread Status">
            {outreachStatus.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={outreachStatus}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={3}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`}
                  >
                    {outreachStatus.map((_, index) => (
                      <Cell key={`outreach-cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No outreach data"
                description="This report does not include outreach thread information."
              />
            )}
          </ChartCard>

          <ChartCard title="Acquired Links by Source">
            {acquiredLinksBySource.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={acquiredLinksBySource}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} angle={-30} textAnchor="end" height={60} />
                  <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }} />
                  <Bar dataKey="value" fill="#10b981" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No acquired links"
                description="This report does not include acquired link data."
              />
            )}
          </ChartCard>

          <ChartCard title="Keyword Difficulty Distribution">
            {keywordDifficulty.some((b) => b.value > 0) ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={keywordDifficulty}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                  <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 8, fontSize: 12 }} />
                  <Area type="monotone" dataKey="value" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="No keyword data"
                description="This report does not include keyword difficulty data."
              />
            )}
          </ChartCard>
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              title="No chart data available"
              description="This report does not contain any chart-eligible data. Try generating a report that includes campaigns, prospects, emails, acquired links, or keywords."
            />
          </CardContent>
        </Card>
      )}

      {report.data && Object.keys(safeObj(report.data)).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-mono">Raw Report Data</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-[10px] font-mono text-slate-400 bg-surface-darker p-4 rounded-lg overflow-x-auto max-h-64">
              {JSON.stringify(report.data, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
