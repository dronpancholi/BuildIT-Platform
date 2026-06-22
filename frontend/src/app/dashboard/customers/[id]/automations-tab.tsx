"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Zap, Activity, AlertTriangle, CheckCircle2, Clock, Play, Pause, RotateCcw } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface AutomationRule {
  id: string;
  name: string;
  trigger_type: string;
  status: string;
  run_count: number;
  last_run_at: string | null;
  created_at: string;
}

export function AutomationsTab({ customerId }: { customerId: string }) {
  const tid = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data: rules = [], isLoading, error } = useQuery<AutomationRule[]>({
    queryKey: ["customer", customerId, "automations"],
    queryFn: async () => {
      const res = await fetchApi<any>(`/automation/rules?tenant_id=${tid}`);
      return res?.data || [];
    },
    refetchInterval: 60000,
  });

  const { data: stats } = useQuery<any>({
    queryKey: ["customer", customerId, "automations", "stats"],
    queryFn: async () => {
      const res = await fetchApi<any>(`/automation/stats?tenant_id=${tid}`);
      return res?.data;
    },
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="p-6 text-center text-xs font-mono text-slate-500">Loading automations...</div>;
  if (error) return <div className="p-6 text-center text-xs font-mono text-red-400">Failed to load automations</div>;

  const active = safeArr<AutomationRule>(rules).filter((r) => r.status === "active").length;
  const paused = safeArr<AutomationRule>(rules).filter((r) => r.status === "paused").length;
  const totalRuns = stats?.total_runs || safeArr<AutomationRule>(rules).reduce((s, r) => s + (r.run_count || 0), 0);
  const failureRate = stats?.failure_rate != null ? (stats.failure_rate * 100) : null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <Zap className="w-3.5 h-3.5" /> Total Rules
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{safeArr<AutomationRule>(rules).length}</p>
        </div>
        <div className="glass-panel p-4 border-emerald-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-emerald-500 uppercase mb-2">
            <Play className="w-3.5 h-3.5" /> Active
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400">{active}</p>
        </div>
        <div className="glass-panel p-4 border-amber-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-amber-500 uppercase mb-2">
            <Pause className="w-3.5 h-3.5" /> Paused
          </div>
          <p className="text-2xl font-bold font-mono text-amber-400">{paused}</p>
        </div>
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <RotateCcw className="w-3.5 h-3.5" /> Total Runs
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{safeLocale(totalRuns)}</p>
        </div>
      </div>

      {failureRate != null && (
        <div className="glass-panel p-3 flex items-center gap-3">
          <div className={`p-1.5 rounded-lg ${failureRate > 10 ? "bg-red-500/10" : "bg-emerald-500/10"}`}>
            <AlertTriangle className={`w-4 h-4 ${failureRate > 10 ? "text-red-400" : "text-emerald-400"}`} />
          </div>
          <div className="flex-1">
            <div className="flex justify-between items-center">
              <span className="text-xs font-mono text-slate-400">Failure Rate</span>
              <span className={`text-xs font-mono font-bold ${failureRate > 10 ? "text-red-400" : "text-emerald-400"}`}>
                {failureRate.toFixed(1)}%
              </span>
            </div>
            <div className="w-full h-1.5 bg-surface-darker rounded-full mt-1 overflow-hidden">
              <div
                className={`h-full rounded-full ${failureRate > 10 ? "bg-red-500" : "bg-emerald-500"}`}
                style={{ width: `${Math.min(failureRate, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50">
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">Automation Rules</h3>
        </div>
        <div className="divide-y divide-surface-border max-h-[500px] overflow-y-auto">
          {safeArr<AutomationRule>(rules).slice(0, 50).map((rule) => (
            <div key={rule.id} className="p-3 hover:bg-surface-border/20 transition-colors">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {rule.status === "active" ? (
                    <Play className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Pause className="w-3.5 h-3.5 text-amber-400" />
                  )}
                  <span className="text-sm font-mono text-slate-200">{rule.name}</span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    rule.status === "active"
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                      : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                  }`}>
                    {rule.status}
                  </span>
                </div>
                <div className="flex items-center gap-3 text-[10px] font-mono text-slate-600">
                  <span>{rule.run_count} runs</span>
                  <span>{rule.trigger_type}</span>
                  {rule.last_run_at && (
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {new Date(rule.last_run_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
