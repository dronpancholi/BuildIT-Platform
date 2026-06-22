"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { FileText, Download, Calendar, BarChart3, FileSpreadsheet } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface Report {
  id: string;
  title: string;
  report_type: string;
  status: string;
  created_at: string;
  total_keywords: number;
  total_prospects: number;
  total_opportunities: number;
}

function ReportTypeIcon({ type }: { type: string }) {
  const icons: Record<string, any> = {
    keyword: FileText,
    prospect: FileSpreadsheet,
    performance: BarChart3,
  };
  const Icon = icons[type] || FileText;
  return <Icon className="w-4 h-4 text-platform-400" />;
}

export function ReportsTab({ customerId }: { customerId: string }) {
  const tid = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data: reports = [], isLoading, error } = useQuery<Report[]>({
    queryKey: ["customer", customerId, "reports"],
    queryFn: async () => {
      const res = await fetchApi<any>(`/reports?tenant_id=${tid}`);
      return res?.data || [];
    },
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="p-6 text-center text-xs font-mono text-slate-500">Loading reports...</div>;
  if (error) return <div className="p-6 text-center text-xs font-mono text-red-400">Failed to load reports</div>;

  const byType = safeArr<Report>(reports).reduce<Record<string, number>>((acc, r) => {
    acc[r.report_type] = (acc[r.report_type] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <FileText className="w-3.5 h-3.5" /> Total Reports
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{safeArr<Report>(reports).length}</p>
        </div>
        {Object.entries(byType).slice(0, 3).map(([type, count]) => (
          <div key={type} className="glass-panel p-4">
            <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
              <ReportTypeIcon type={type} /> {type}
            </div>
            <p className="text-2xl font-bold font-mono text-slate-100">{count}</p>
          </div>
        ))}
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50">
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">All Reports</h3>
        </div>
        <div className="divide-y divide-surface-border">
          {safeArr<Report>(reports).length === 0 ? (
            <div className="p-8 text-center">
              <FileText className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Reports</h3>
              <p className="text-xs text-slate-500">Generate reports to track campaign performance</p>
            </div>
          ) : (
            safeArr<Report>(reports).map((report) => (
              <div key={report.id} className="p-4 hover:bg-surface-border/20 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="p-2 rounded-lg bg-platform-600/10 border border-platform-500/20">
                      <ReportTypeIcon type={report.report_type} />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold font-mono text-slate-200">{report.title || report.report_type}</h4>
                      <div className="flex items-center gap-3 mt-1 text-[10px] font-mono text-slate-500">
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" /> {new Date(report.created_at).toLocaleDateString()}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-slate-700/50 text-slate-400">{report.status}</span>
                      </div>
                      <div className="flex items-center gap-3 mt-2 text-[10px] font-mono text-slate-600">
                        <span>{report.total_keywords} keywords</span>
                        <span>{report.total_prospects} prospects</span>
                        <span>{report.total_opportunities} opportunities</span>
                      </div>
                    </div>
                  </div>
                  <button className="p-2 hover:bg-surface-border rounded transition-colors">
                    <Download className="w-4 h-4 text-slate-400" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
