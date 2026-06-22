"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { FileText, Download, Upload, Trash2, Eye, FileSpreadsheet, Image, File, Archive, Search } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface Asset {
  id: string;
  name: string;
  type: string;
  size?: number;
  url?: string;
  created_at: string;
  status: string;
}

const FILE_ICONS: Record<string, any> = {
  pdf: FileText,
  csv: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  png: Image,
  jpg: Image,
  jpeg: Image,
  zip: Archive,
  report: FileText,
  export: FileSpreadsheet,
};

function formatSize(bytes?: number) {
  if (!bytes) return "";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function AssetsTab({ customerId }: { customerId: string }) {
  const tid = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";
  const [search, setSearch] = useState("");

  const { data: assets = [], isLoading, error } = useQuery<Asset[]>({
    queryKey: ["customer", customerId, "assets"],
    queryFn: async () => {
      const res = await fetchApi<any>(`/reports?tenant_id=${tid}`);
      const reports = res?.data || [];
      return safeArr<any>(reports).map((r: any) => ({
        id: r.id,
        name: r.title || `${r.report_type}_report`,
        type: r.report_type || "report",
        size: undefined,
        url: undefined,
        created_at: r.created_at,
        status: r.status,
      }));
    },
    refetchInterval: 60000,
  });

  const filtered = search
    ? safeArr<Asset>(assets).filter((a) => safeLower(a.name, "").includes(safeLower(search, "")))
    : assets;

  const byType = safeArr<Asset>(assets).reduce<Record<string, number>>((acc, a) => {
    acc[a.type] = (acc[a.type] || 0) + 1;
    return acc;
  }, {});

  if (isLoading) return <div className="p-6 text-center text-xs font-mono text-slate-500">Loading assets...</div>;
  if (error) return <div className="p-6 text-center text-xs font-mono text-red-400">Failed to load assets</div>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search assets..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-48 bg-surface-darker border border-surface-border rounded-md pl-8 pr-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500/50"
            />
          </div>
        </div>
        <button className="flex items-center gap-1.5 px-3 py-1.5 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors">
          <Upload className="w-3.5 h-3.5" /> Upload
        </button>
      </div>

      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <FileText className="w-3.5 h-3.5" /> Total Assets
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{safeArr<Asset>(assets).length}</p>
        </div>
        {Object.entries(byType).slice(0, 3).map(([type, count]) => {
          const FileIcon = FILE_ICONS[type] || File;
          return (
            <div key={type} className="glass-panel p-4">
              <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
                <FileIcon className="w-3.5 h-3.5" />
                {type}
              </div>
              <p className="text-2xl font-bold font-mono text-slate-100">{count}</p>
            </div>
          );
        })}
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50">
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">Assets</h3>
        </div>
        <div className="divide-y divide-surface-border max-h-[500px] overflow-y-auto">
          {safeArr<Asset>(filtered).length === 0 ? (
            <div className="p-8 text-center">
              <FileText className="w-12 h-12 text-slate-700 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Assets</h3>
              <p className="text-xs text-slate-500">Upload files or generate reports to create assets</p>
            </div>
          ) : (
            safeArr<Asset>(filtered).map((asset) => {
              const Icon = FILE_ICONS[asset.type] || File;
              return (
                <div key={asset.id} className="p-3 flex items-center justify-between hover:bg-surface-border/20 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="p-1.5 rounded-lg bg-platform-600/10 border border-platform-500/20">
                      <Icon className="w-4 h-4 text-platform-400" />
                    </div>
                    <div>
                      <p className="text-sm font-mono text-slate-200">{asset.name}</p>
                      <div className="flex items-center gap-2 text-[10px] font-mono text-slate-600 mt-0.5">
                        <span>{asset.type}</span>
                        {asset.size && <span>{formatSize(asset.size)}</span>}
                        <span>{new Date(asset.created_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <button className="p-1.5 hover:bg-surface-border rounded transition-colors" title="Preview">
                      <Eye className="w-3.5 h-3.5 text-slate-500" />
                    </button>
                    <button className="p-1.5 hover:bg-surface-border rounded transition-colors" title="Download">
                      <Download className="w-3.5 h-3.5 text-slate-500" />
                    </button>
                    <button className="p-1.5 hover:bg-surface-border rounded transition-colors" title="Delete">
                      <Trash2 className="w-3.5 h-3.5 text-red-400/70 hover:text-red-400" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
