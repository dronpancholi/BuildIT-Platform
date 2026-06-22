"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Download,
  FileText,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { GrowthChart } from "@/components/citations/growth-chart";
import { StatusPie } from "@/components/citations/status-pie";
import {
  citationApi,
  type CitationProject,
  type ReportListItem,
  type GrowthDataPoint,
  type StatusBreakdown,
} from "@/lib/api";

export default function ReportDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;
  const reportId = params.reportId as string;

  const [project, setProject] = useState<CitationProject | null>(null);
  const [report, setReport] = useState<ReportListItem | null>(null);
  const [growthData, setGrowthData] = useState<GrowthDataPoint[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [proj, reportData, growth] = await Promise.all([
        citationApi.getProject(projectId),
        citationApi.getReport(reportId),
        citationApi.getGrowthData(projectId, 30),
      ]);
      setProject(proj);
      setReport(reportData);
      setGrowthData(growth);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load report");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (projectId && reportId) loadData();
  }, [projectId, reportId]);

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

  if (error || !project || !report) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="p-6 text-center">
          <p className="text-red-400">{error || "Report not found"}</p>
          <Button variant="outline" className="mt-4" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
          </Button>
        </CardContent>
      </Card>
    );
  }

  const report_data = report.report_data as any;
  const summary = report_data?.summary;
  const quality = report_data?.quality;
  const topSites = report_data?.top_sites || report.top_sites || [];
  const napConsistency = report_data?.nap;

  // Build status breakdown for pie chart from report_data or status_breakdown
  const statusBreakdownData = report_data?.breakdown?.statuses || report.status_breakdown || {};
  const statusBreakdown: StatusBreakdown[] = Object.entries(statusBreakdownData).map(([status, count]) => ({
    status,
    count: count as number,
    percentage: report.total_citations_end ? ((count as number) / report.total_citations_end) * 100 : 0,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/dashboard/citations/${projectId}/reports`)}
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-100 font-mono">
                REPORT_DETAIL
              </h1>
              <span className="bg-surface-darker px-1.5 py-0.5 rounded text-xs text-slate-400">
                {report.report_type.replace(/_/g, " ").toUpperCase()}
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              Generated {new Date(report.created_at || report.generated_at).toLocaleString()} by {report.generated_by || 'System'}
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
        </div>
      </div>

      {/* Executive Summary */}
      {(report_data as any)?.executive_summary && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
              Executive Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-slate-300 whitespace-pre-wrap">
              {(report_data as any).executive_summary}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Summary Stats */}
      {summary && (
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
      )}

      {/* Quality Metrics */}
      {quality && (
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-mono font-bold text-indigo-400">{summary?.nap_consistency_score || 0}%</div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">NAP Consistency</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-mono font-bold text-cyan-400">{quality.avg_domain_authority || 0}</div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Avg Domain Authority</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-mono font-bold text-emerald-400">{quality.premium_sites_count || 0}</div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Premium Sites</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-mono font-bold text-amber-400">{quality.quality_score || 0}</div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Quality Score</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
              Citation Growth (30d)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <GrowthChart data={growthData} height={250} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
              Status Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <StatusPie data={statusBreakdown} height={250} />
          </CardContent>
        </Card>
      </div>

      {/* NAP Consistency */}
      {napConsistency && napConsistency.fields && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
              NAP Consistency — Overall Score: {napConsistency.score}%
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="text-left text-[10px] font-mono uppercase tracking-wider text-slate-500 px-4 py-2">Field</th>
                  <th className="text-left text-[10px] font-mono uppercase tracking-wider text-slate-500 px-4 py-2">Consistency</th>
                  <th className="text-left text-[10px] font-mono uppercase tracking-wider text-slate-500 px-4 py-2">Issues</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(napConsistency.fields).map(([field, fieldData]) => (
                  <tr key={field} className="border-b border-surface-border last:border-0">
                    <td className="px-4 py-3 text-sm text-slate-200 capitalize">{field.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                          <div
                            className="h-full bg-emerald-500 rounded-full"
                            style={{ width: `${(fieldData as { score: number }).score}%` }}
                          />
                        </div>
                        <span className="text-sm text-slate-400">{(fieldData as { score: number }).score}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {(fieldData as { issues: unknown[] }).issues.length === 0 ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      ) : (
                        <div className="flex items-center gap-1">
                          <XCircle className="w-4 h-4 text-red-400" />
                          <span className="text-xs text-red-400">{(fieldData as { issues: unknown[] }).issues.length}</span>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}

      {/* Top Sites */}
      {topSites.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
              Top Performing Sites
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
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
                {topSites.map((site: any, i: number) => (
                  <tr key={i} className="border-b border-surface-border last:border-0 hover:bg-surface-darker/30">
                    <td className="px-4 py-3">
                      <div className="text-sm text-slate-200">{site.site_name || (site as Record<string, unknown>).name}</div>
                      <div className="text-xs text-slate-500">{site.site_url || ""}</div>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-400">{site.category || ""}</td>
                    <td className="px-4 py-3 text-sm text-slate-400">{site.domain_authority || (site as Record<string, unknown>).da || 0}</td>
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
                        {(site.status || "unknown").replace(/_/g, " ")}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
