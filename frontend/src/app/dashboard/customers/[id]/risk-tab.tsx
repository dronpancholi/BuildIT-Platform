"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { AlertTriangle, Shield, AlertCircle, Clock, CheckCircle2, Filter } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface Risk {
  id: string;
  title: string;
  category: string;
  severity: string;
  status: string;
  description: string;
  created_at: string;
  resolved_at?: string;
}

export function RiskTab({ customerId }: { customerId: string }) {
  const tid = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data, isLoading, error } = useQuery<any>({
    queryKey: ["customer", customerId, "health-risk"],
    queryFn: async () => {
      const res = await fetchApi<any>(`/customers/${customerId}/health-risk?tenant_id=${tid}`);
      return res;
    },
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="p-6 text-center text-xs font-mono text-slate-500">Loading risk data...</div>;
  if (error) return <div className="p-6 text-center text-xs font-mono text-red-400">Failed to load risk data</div>;

  const risks: Risk[] = data?.risks?.items || [];
  const total = safeNum(data?.risks?.total) || safeArr<Risk>(risks).length;
  const unresolved = safeNum(data?.risks?.unresolved) || safeArr<Risk>(risks).filter((r) => r.status !== "resolved").length;

  const bySeverity = safeArr<Risk>(risks).reduce<Record<string, number>>((acc, r) => {
    acc[r.severity] = (acc[r.severity] || 0) + 1;
    return acc;
  }, {});
  const byCategory = safeArr<Risk>(risks).reduce<Record<string, number>>((acc, r) => {
    acc[r.category] = (acc[r.category] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4 border-red-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-red-400 uppercase mb-2">
            <AlertTriangle className="w-3.5 h-3.5" /> Total Risks
          </div>
          <p className="text-2xl font-bold font-mono text-red-400">{total}</p>
        </div>
        <div className="glass-panel p-4 border-amber-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-amber-400 uppercase mb-2">
            <AlertCircle className="w-3.5 h-3.5" /> Unresolved
          </div>
          <p className="text-2xl font-bold font-mono text-amber-400">{unresolved}</p>
        </div>
        {bySeverity.critical && (
          <div className="glass-panel p-4 border-red-500/40">
            <div className="flex items-center gap-2 text-[10px] font-mono text-red-500 uppercase mb-2">
              <Shield className="w-3.5 h-3.5" /> Critical
            </div>
            <p className="text-2xl font-bold font-mono text-red-500">{bySeverity.critical}</p>
          </div>
        )}
        {bySeverity.warning && (
          <div className="glass-panel p-4 border-amber-500/20">
            <div className="flex items-center gap-2 text-[10px] font-mono text-amber-400 uppercase mb-2">
              <Shield className="w-3.5 h-3.5" /> Warnings
            </div>
            <p className="text-2xl font-bold font-mono text-amber-400">{bySeverity.warning}</p>
          </div>
        )}
        {!bySeverity.warning && !bySeverity.critical && (
          <div className="glass-panel p-4 border-emerald-500/20">
            <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-400 uppercase mb-2">
              <CheckCircle2 className="w-3.5 h-3.5" /> Resolved
            </div>
            <p className="text-2xl font-bold font-mono text-emerald-400">{total - unresolved}</p>
          </div>
        )}
      </div>

      {Object.keys(byCategory).length > 0 && (
        <div className="glass-panel p-4">
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase mb-3">By Category</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(byCategory).map(([cat, count]) => (
              <div key={cat} className="flex items-center justify-between p-2 rounded bg-surface-darker/50">
                <span className="text-xs font-mono text-slate-400">{cat}</span>
                <span className="text-xs font-mono text-slate-200">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50">
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">Risk Items</h3>
        </div>
        <div className="divide-y divide-surface-border max-h-[600px] overflow-y-auto">
          {safeArr<Risk>(risks).length === 0 ? (
            <div className="p-8 text-center">
              <CheckCircle2 className="w-12 h-12 text-emerald-500/50 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Risks</h3>
              <p className="text-xs text-slate-500">No risk items identified for this customer</p>
            </div>
          ) : (
            safeArr<Risk>(risks).map((risk) => (
              <div key={risk.id} className="p-4 hover:bg-surface-border/20 transition-colors">
                <div className="flex items-start gap-3">
                  <div className={`p-1.5 rounded-lg border mt-0.5 ${
                    risk.severity === "critical" ? "bg-red-500/10 border-red-500/20" :
                    risk.severity === "warning" ? "bg-amber-500/10 border-amber-500/20" :
                    "bg-slate-500/10 border-slate-500/20"
                  }`}>
                    <AlertTriangle className={`w-4 h-4 ${
                      risk.severity === "critical" ? "text-red-400" :
                      risk.severity === "warning" ? "text-amber-400" : "text-slate-400"
                    }`} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-mono text-slate-200">{risk.title}</span>
                      <span className={`px-1.5 py-0.5 text-[10px] font-mono rounded ${
                        risk.severity === "critical" ? "bg-red-500/10 text-red-400" :
                        risk.severity === "warning" ? "bg-amber-500/10 text-amber-400" :
                        "bg-slate-500/10 text-slate-400"
                      }`}>
                        {risk.severity}
                      </span>
                      <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-platform-600/10 text-platform-400">
                        {risk.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500">{risk.description}</p>
                    <div className="flex items-center gap-2 mt-1.5 text-[10px] font-mono text-slate-600">
                      <span>{risk.category}</span>
                      <span>·</span>
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {new Date(risk.created_at).toLocaleDateString()}
                      </span>
                      {risk.resolved_at && (
                        <>
                          <span>·</span>
                          <span className="text-emerald-500">Resolved {new Date(risk.resolved_at).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
