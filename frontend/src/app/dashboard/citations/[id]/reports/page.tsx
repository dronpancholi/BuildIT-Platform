"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Download,
  FileText,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import {
  citationApi,
  type CitationProject,
  type ReportListItem,
} from "@/lib/api";

export default function ReportsListPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<CitationProject | null>(null);
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [proj, reportList] = await Promise.all([
        citationApi.getProject(projectId),
        citationApi.listReports(projectId),
      ]);
      setProject(proj);
      setReports(reportList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load reports");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId]);

  const handleGenerate = async () => {
    try {
      setIsGenerating(true);
      const result = await citationApi.generateReport(projectId);
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
      setIsGenerating(false);
    }
  };

  const handleDelete = async (reportId: string) => {
    if (!confirm("Delete this report?")) return;
    try {
      await citationApi.deleteReport(reportId);
      setReports((prev) => prev.filter((r) => r.id !== reportId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete report");
    }
  };

  const handleExport = async (format: "csv" | "txt") => {
    try {
      const blob = await citationApi.exportReport(projectId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.business_name || "report"}_export.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Export failed");
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="lg" className="py-20" />;
  }

  if (error || !project) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="p-6 text-center">
          <p className="text-red-400">{error || "Failed to load reports"}</p>
          <Button variant="outline" className="mt-4" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
          </Button>
        </CardContent>
      </Card>
    );
  }

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
              <h1 className="text-2xl font-bold text-slate-100 font-mono">REPORTS</h1>
              <span className="bg-surface-darker px-1.5 py-0.5 rounded text-xs text-slate-400">
                Phase 9
              </span>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              {project.business_name} — Saved reports and exports
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
            Export CSV
          </Button>
          <Button variant="outline" onClick={() => handleExport("txt")}>
            <Download className="w-4 h-4 mr-2" />
            Export TXT
          </Button>
          <Button onClick={handleGenerate} disabled={isGenerating}>
            <FileText className="w-4 h-4 mr-2" />
            {isGenerating ? "Generating..." : "Generate Report"}
          </Button>
        </div>
      </div>

      {/* Reports List */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
            Saved Reports ({reports.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {reports.length === 0 ? (
            <div className="p-8 text-center">
              <FileText className="w-8 h-8 text-slate-600 mx-auto" />
              <p className="text-slate-500 text-sm mt-2">
                No reports generated yet. Click &quot;Generate Report&quot; to create your first report.
              </p>
            </div>
          ) : (
            <div>
              {reports.map((report) => (
                <div
                  key={report.id}
                  className="flex items-center gap-4 px-4 py-4 border-b border-surface-border last:border-0 hover:bg-surface-darker/30"
                >
                  <FileText className="w-5 h-5 text-slate-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-slate-200 font-medium">
                      {report.report_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} Report
                    </div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      Generated {new Date(report.created_at || report.generated_at).toLocaleString()} by {report.generated_by || 'System'}
                    </div>
                    {(report.report_data as any)?.executive_summary && (
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">
                        {(report.report_data as any).executive_summary}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-slate-500 uppercase bg-surface-darker px-2 py-0.5 rounded">
                      {report.format}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        router.push(
                          `/dashboard/citations/${projectId}/reports/${report.id}`
                        )
                      }
                    >
                      View
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(report.id)}
                      className="text-red-400 hover:text-red-300"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
