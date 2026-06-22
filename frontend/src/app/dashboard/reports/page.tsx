"use client";

import { useState } from "react";
import { useApiList, useApiCreate } from "@/services/hooks";
import { ENDPOINTS } from "@/services/endpoints";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { formatDate } from "@/lib/utils";
import { safeLocale } from "@/lib/safe";
import {
  FileText,
  Plus,
  Download,
  Eye,
  BarChart3,
  Calendar,
} from "lucide-react";
import type { Report, Client } from "@/types/models";

const REPORT_TYPES = [
  { label: "Monthly", value: "monthly" },
  { label: "Quarterly", value: "quarterly" },
  { label: "Custom", value: "custom" },
];

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
  completed: "success",
  generating: "warning",
  failed: "destructive",
  scheduled: "secondary",
};

export default function ReportsPage() {
  const [showGenerateDialog, setShowGenerateDialog] = useState(false);
  const [generateForm, setGenerateForm] = useState({
    report_type: "monthly",
    client_id: "",
  });
  const [viewingReport, setViewingReport] = useState<Report | null>(null);

  const { data: reports, isLoading, error } = useApiList<Report>(ENDPOINTS.REPORTS);
  const { data: clients } = useApiList<Client>(ENDPOINTS.CLIENTS);

  const createMutation = useApiCreate<Report, typeof generateForm>(
    `${ENDPOINTS.REPORTS}/generate`,
    {
      invalidateKeys: [ENDPOINTS.REPORTS],
      successMessage: "Report generation started",
    }
  );

  const handleGenerate = () => {
    createMutation.mutate(generateForm, {
      onSuccess: () => {
        setShowGenerateDialog(false);
        setGenerateForm({ report_type: "monthly", client_id: "" });
      },
    });
  };

  const handleExport = (format: string, report: Report) => {
    const r = report as any;
    const blob = format === "csv"
      ? new Blob([r.metrics ? Object.entries(r.metrics).map(([k, v]) => `${k},${v}`).join("\n") : "no metrics"], { type: "text/csv" })
      : new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${report.id}.${format}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const clientMap = new Map(clients?.map((c) => [c.id, c.name]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Reports</h1>
          <p className="text-slate-400 mt-1">Generate and manage campaign reports</p>
        </div>
        <Button onClick={() => setShowGenerateDialog(true)}>
          <Plus className="w-4 h-4" />
          Generate Report
        </Button>
      </div>

      {isLoading ? (
        <LoadingSpinner size="lg" className="py-20" />
      ) : error ? (
        <Card className="border-red-500/20 bg-red-500/5">
          <CardContent className="py-8 text-center">
            <p className="text-red-400 text-sm">Failed to load reports. Please try again.</p>
          </CardContent>
        </Card>
      ) : !reports || reports.length === 0 ? (
        <EmptyState
          icon={<FileText className="w-8 h-8" />}
          title="No reports yet"
          description="Generate your first report to see campaign performance analytics."
          action={{ label: "Generate Report", onClick: () => setShowGenerateDialog(true) }}
        />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Created</th>
                  <th className="text-right px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {reports.map((report) => (
                  <tr key={report.id} className="hover:bg-surface-card/50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-slate-200">{report.title}</p>
                      <p className="text-xs text-slate-500">
                        {clientMap.get(report.client_id) || "—"}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline" className="capitalize">
                        {report.report_type.replace(/_/g, " ")}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={STATUS_VARIANT[report.data?.status as string] || "outline"}>
                        {(report.data?.status as string) || "completed"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {formatDate(report.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => setViewingReport(report)}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8"
                          onClick={() => handleExport("pdf", report)}
                        >
                          <Download className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Dialog open={showGenerateDialog} onOpenChange={setShowGenerateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate Report</DialogTitle>
            <DialogDescription>Create a new campaign performance report</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="report-type">Report Type</Label>
              <Select
                id="report-type"
                options={REPORT_TYPES}
                value={generateForm.report_type}
                onChange={(e) => setGenerateForm({ ...generateForm, report_type: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="report-client">Client</Label>
              <Select
                id="report-client"
                placeholder="Select a client"
                options={clients?.map((c) => ({ label: c.name, value: c.id })) || []}
                value={generateForm.client_id}
                onChange={(e) => setGenerateForm({ ...generateForm, client_id: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowGenerateDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleGenerate}
              disabled={!generateForm.client_id || createMutation.isPending}
            >
              {createMutation.isPending ? "Generating..." : "Generate Report"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!viewingReport} onOpenChange={() => setViewingReport(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{viewingReport?.title}</DialogTitle>
            <DialogDescription>
              {viewingReport?.report_type.replace(/_/g, " ")} report · {formatDate(viewingReport?.created_at || "")}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {viewingReport?.data && Object.keys(viewingReport.data).length > 0 ? (
              <div className="grid grid-cols-2 gap-3">
                {Object.entries(viewingReport.data).map(([key, value]) => (
                  <div key={key} className="p-3 bg-surface-darker border border-surface-border rounded-lg">
                    <p className="text-xs text-slate-500 capitalize">{key.replace(/_/g, " ")}</p>
                    <p className="text-sm text-slate-200 font-medium mt-1">
                      {typeof value === "number" ? safeLocale(value) : String(value ?? "—")}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                icon={<BarChart3 className="w-8 h-8" />}
                title="No report data"
                description="This report does not contain any data yet."
              />
            )}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setViewingReport(null)}>
              Close
            </Button>
            <Button onClick={() => handleExport("pdf", viewingReport!)}>
              <Download className="w-4 h-4" />
              Export PDF
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
