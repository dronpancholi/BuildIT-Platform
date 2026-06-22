"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  Globe,
  RefreshCw,
  TrendingUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { GrowthChart } from "@/components/citations/growth-chart";
import { StatusPie } from "@/components/citations/status-pie";
import {
  citationApi,
  type CitationProject,
  type ProjectAnalytics,
  type GrowthDataPoint,
  type ReportListItem,
  type StatusBreakdown,
} from "@/lib/api";

export default function AnalyticsPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<CitationProject | null>(null);
  const [analytics, setAnalytics] = useState<ProjectAnalytics | null>(null);
  const [growthData, setGrowthData] = useState<GrowthDataPoint[]>([]);
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [growthDays, setGrowthDays] = useState(30);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [proj, analyticsData, growth, reportList] = await Promise.all([
        citationApi.getProject(projectId),
        citationApi.getAnalytics(projectId),
        citationApi.getGrowthData(projectId, growthDays),
        citationApi.listReports(projectId),
      ]);
      setProject(proj);
      setAnalytics(analyticsData);
      setGrowthData(growth);
      setReports(reportList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load analytics");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId, growthDays]);

  const handleGenerateReport = async () => {
    try {
      setIsGeneratingReport(true);
      const result = await citationApi.generateReport(projectId);
      // Add the new report to the list
      const newReport: ReportListItem = {
        id: result.report_id,
        project_id: projectId,
        report_type: "monthly",
        report_name: "Monthly Report",
        period_start: "",
        period_end: "",
        total_citations_start: 0,
        total_citations_end: result.report_data?.summary?.total_citations || 0,
        citations_added: 0,
        nap_consistency_score: result.report_data?.summary?.nap_consistency_score || 0,
        avg_domain_authority: result.report_data?.summary?.avg_domain_authority || 0,
        status_breakdown: result.report_data?.breakdown?.statuses || {},
        competitor_summary: (result.report_data?.competitors || {}) as unknown as Record<string, unknown>,
        top_sites: result.report_data?.top_sites || [],
        report_data: result.report_data,
        generated_at: new Date().toISOString(),
      };
      setReports((prev) => [newReport, ...prev]);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to generate report");
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const handleExport = async (format: "csv" | "txt") => {
    try {
      const blob = await citationApi.exportReport(projectId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.business_name || "report"}_report.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Export failed");
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="lg" className="py-20" />;
  }

  if (error || !project || !analytics) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="p-6 text-center">
          <p className="text-red-400">{error || "Failed to load analytics"}</p>
          <Button variant="outline" className="mt-4" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
          </Button>
        </CardContent>
      </Card>
    );
  }

  const { summary, breakdown, quality, top_sites } = analytics;

  // Build status breakdown for pie chart
  const statusBreakdown: StatusBreakdown[] = breakdown.statuses
    ? Object.entries(breakdown.statuses).map(([status, count]) => ({
        status,
        count: count as number,
        percentage: breakdown.percentages?.[status] || 0,
      }))
    : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/dashboard/citations/${projectId}`)}
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-100 font-mono">
                ANALYTICS
              </h1>
              <span className="bg-surface-darker px-1.5 py-0.5 rounded text-xs text-slate-400">
                Phase 9
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              {project.business_name} — Citation performance analytics
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button variant="outline" onClick={() => handleExport("csv")}>
            <Download className="w-4 h-4 mr-2" />
            CSV
          </Button>
          <Button variant="outline" onClick={() => handleExport("txt")}>
            <Download className="w-4 h-4 mr-2" />
            TXT
          </Button>
          <Button onClick={handleGenerateReport} disabled={isGeneratingReport}>
            <FileText className="w-4 h-4 mr-2" />
            {isGeneratingReport ? "Generating..." : "Generate Report"}
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-6 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-slate-200">{summary.total_citations}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Total Sites</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-emerald-400">{summary.live_citations}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Live</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-blue-400">{summary.pending_citations}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Pending</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-amber-400">{summary.already_exists_citations}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Already Exists</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-red-400">{summary.failed_citations}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Failed</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-indigo-400">{summary.growth_last_30_days}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Growth (30d)</div>
          </CardContent>
        </Card>
      </div>

      {/* Quality Metrics */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-indigo-400">{summary.nap_consistency_score}%</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">NAP Consistency</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-cyan-400">{summary.avg_domain_authority.toFixed(1)}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Avg Domain Authority</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-emerald-400">{quality.premium_sites_count}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Premium Sites</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-amber-400">{quality.quality_score}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Quality Score</div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
                <TrendingUp className="w-4 h-4" />
                Citation Growth
              </CardTitle>
              <select
                value={growthDays}
                onChange={(e) => setGrowthDays(Number(e.target.value))}
                className="bg-surface-darker border border-surface-border rounded px-2 py-1 text-xs text-slate-300"
              >
                <option value={7}>7 Days</option>
                <option value={30}>30 Days</option>
                <option value={90}>90 Days</option>
              </select>
            </div>
          </CardHeader>
          <CardContent>
            <GrowthChart data={growthData} height={280} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" />
              Status Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <StatusPie data={statusBreakdown} height={280} />
          </CardContent>
        </Card>
      </div>

      {/* Top Sites */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
            Top Performing Sites
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {top_sites.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-slate-500 text-sm">No site data available yet</p>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="text-left text-[10px] font-mono uppercase tracking-wider text-slate-500 px-4 py-2">Site</th>
                  <th className="text-left text-[10px] font-mono uppercase tracking-wider text-slate-500 px-4 py-2">Category</th>
                  <th className="text-left text-[10px] font-mono uppercase tracking-wider text-slate-500 px-4 py-2">DA</th>
                  <th className="text-left text-[10px] font-mono uppercase tracking-wider text-slate-500 px-4 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {top_sites.slice(0, 10).map((site, i) => (
                  <tr key={i} className="border-b border-surface-border last:border-0 hover:bg-surface-darker/30">
                    <td className="px-4 py-3">
                      <div className="text-sm text-slate-200">{site.site_name}</div>
                      <div className="text-xs text-slate-500">{site.site_url}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">{site.category}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">{site.domain_authority}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        site.status === "completed" || site.status === "verified"
                          ? "bg-emerald-500/10 text-emerald-400"
                          : site.status === "in_progress"
                          ? "bg-blue-500/10 text-blue-400"
                          : site.status === "failed"
                          ? "bg-red-500/10 text-red-400"
                          : "bg-slate-500/10 text-slate-400"
                      }`}>
                        {site.status.replace(/_/g, " ")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Recent Reports */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
              Recent Reports ({reports.length})
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/dashboard/citations/${projectId}/reports`)}
            >
              View All
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {reports.length === 0 ? (
            <div className="p-6 text-center">
              <p className="text-slate-500 text-sm">No reports generated yet. Click &quot;Generate Report&quot; to create one.</p>
            </div>
          ) : (
            <div>
              {reports.slice(0, 5).map((report) => (
                <div
                  key={report.id}
                  className="flex items-center gap-4 px-4 py-3 border-b border-surface-border last:border-0 hover:bg-surface-darker/30 cursor-pointer"
                  onClick={() => router.push(`/dashboard/citations/${projectId}/reports/${report.id}`)}
                >
                  <FileText className="w-4 h-4 text-slate-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-slate-200">
                      {report.report_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} Report
                    </div>
                    <div className="text-xs text-slate-500">
                      Generated {new Date(report.created_at || report.generated_at).toLocaleDateString()} by {report.generated_by || 'System'}
                    </div>
                  </div>
                  <span className="text-xs text-slate-500 uppercase">{report.format}</span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
