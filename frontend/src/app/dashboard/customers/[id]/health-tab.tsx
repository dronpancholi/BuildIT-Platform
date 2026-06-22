"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Activity, TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle2, Clock, Mail, Shield } from "lucide-react";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface HealthData {
  current_score: number;
  category: string;
  trend: string;
  velocity: number;
  history: Array<{ score: number; category: string; captured_at: string }>;
}

interface Alert {
  id: string;
  title: string;
  severity: string;
  category: string;
  message: string;
  is_active: boolean;
  created_at: string;
}

interface SLA {
  sla_type: string;
  total: number;
  breaches: number;
  warnings: number;
  avg_remaining_hours: number;
}

interface CommData {
  total: number;
  replied: number;
  reply_rate: number;
  avg_response_hours: number;
}

export function HealthTab({ customerId }: { customerId: string }) {
  const tid = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data, isLoading, error } = useQuery<any>({
    queryKey: ["customer", customerId, "health-risk"],
    queryFn: async () => {
      const res = await fetchApi<any>(`/customers/${customerId}/health-risk?tenant_id=${tid}`);
      return res;
    },
    refetchInterval: 60000,
  });

  if (isLoading) return <div className="p-6 text-center text-xs font-mono text-slate-500">Loading health data...</div>;
  if (error) return <div className="p-6 text-center text-xs font-mono text-red-400">Failed to load health data</div>;

  const health: HealthData = data?.health || {};
  const alerts: Alert[] = data?.alerts?.items || [];
  const sla: SLA[] = data?.sla || [];
  const comm: CommData = data?.communication || {};

  const score = health.current_score || 0;
  const category = health.category || "unknown";
  const trend = health.trend || "stable";

  const getScoreColor = (s: number) => {
    if (s >= 0.7) return "text-emerald-400";
    if (s >= 0.4) return "text-amber-400";
    return "text-red-400";
  };
  const getScoreBg = (s: number) => {
    if (s >= 0.7) return "bg-emerald-500";
    if (s >= 0.4) return "bg-amber-500";
    return "bg-red-500";
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="glass-panel p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-platform-400" />
              <h2 className="text-sm font-bold font-mono text-slate-200 uppercase">Health Score</h2>
            </div>
            <span className={`px-2 py-1 text-[10px] font-mono rounded-full border ${
              category === "healthy" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
              category === "at_risk" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
              "bg-red-500/10 text-red-400 border-red-500/20"
            }`}>
              {safeReplace(safeUpper(category), "_", " ")}
            </span>
          </div>
          <div className="flex items-end gap-3 mb-3">
            <span className={`text-5xl font-bold font-mono ${getScoreColor(score)}`}>
              {(score * 100).toFixed(0)}%
            </span>
            <div className="flex items-center gap-1 mb-1 text-sm">
              {trend === "up" ? <TrendingUp className="w-4 h-4 text-emerald-400" /> :
               trend === "down" ? <TrendingDown className="w-4 h-4 text-red-400" /> :
               <Minus className="w-4 h-4 text-slate-400" />}
              <span className={`text-xs font-mono ${
                trend === "up" ? "text-emerald-400" :
                trend === "down" ? "text-red-400" : "text-slate-400"
              }`}>
                {safeUpper(trend)}
              </span>
            </div>
          </div>
          <div className="w-full h-2.5 bg-surface-darker rounded-full overflow-hidden">
            <div className={`h-full rounded-full transition-all ${getScoreBg(score)}`} style={{ width: `${score * 100}%` }} />
          </div>
          <p className="text-xs text-slate-500 mt-2">Velocity: {health.velocity?.toFixed(2) || "0.00"}</p>
        </div>

        <div className="glass-panel p-6">
          <h3 className="text-sm font-bold font-mono text-slate-200 uppercase mb-4 flex items-center gap-2">
            <Clock className="w-4 h-4 text-platform-400" /> SLA Status
          </h3>
          <div className="space-y-3">
            {safeArr<SLA>(sla).length === 0 ? (
              <p className="text-xs text-slate-500">No SLA data</p>
            ) : (
              safeArr<SLA>(sla).slice(0, 5).map((s) => (
                <div key={s.sla_type} className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-mono text-slate-300">{safeUpper(safeReplace(s.sla_type, "_", " "))}</span>
                    <span className="text-[10px] font-mono text-slate-600 ml-2">({s.total} total)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {s.breaches > 0 && (
                      <span className="text-[10px] font-mono text-red-400">{s.breaches} breached</span>
                    )}
                    <span className={`text-xs font-mono ${s.breaches > 0 ? "text-red-400" : "text-emerald-400"}`}>
                      {s.breaches > 0 ? "⚠" : "✓"}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
          <div className="mt-4 pt-3 border-t border-surface-border">
            <h4 className="text-xs font-mono text-slate-500 mb-2">Communication Health</h4>
            <div className="flex items-center gap-4">
              <div>
                <p className="text-lg font-bold font-mono text-slate-100">{(comm.reply_rate || 0) * 100}%</p>
                <p className="text-[10px] font-mono text-slate-600">Reply Rate</p>
              </div>
              <div>
                <p className="text-lg font-bold font-mono text-slate-100">{comm.avg_response_hours?.toFixed(1) || "-"}h</p>
                <p className="text-[10px] font-mono text-slate-600">Avg Response</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-platform-400" />
            <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">Executive Alerts</h3>
          </div>
        </div>
        <div className="divide-y divide-surface-border max-h-[400px] overflow-y-auto">
          {safeArr<Alert>(alerts).length === 0 ? (
            <div className="p-8 text-center">
              <CheckCircle2 className="w-12 h-12 text-emerald-500/50 mx-auto mb-3" />
              <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Active Alerts</h3>
              <p className="text-xs text-slate-500">Customer health is stable</p>
            </div>
          ) : (
            safeArr<Alert>(alerts).slice(0, 20).map((alert) => (
              <div key={alert.id} className="p-3 hover:bg-surface-border/20 transition-colors">
                <div className="flex items-start gap-2">
                  <AlertTriangle className={`w-4 h-4 mt-0.5 ${
                    alert.severity === "critical" ? "text-red-400" :
                    alert.severity === "warning" ? "text-amber-400" : "text-slate-400"
                  }`} />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-mono text-slate-200">{alert.title}</span>
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        alert.severity === "critical" ? "bg-red-500/10 text-red-400" :
                        alert.severity === "warning" ? "bg-amber-500/10 text-amber-400" :
                        "bg-slate-500/10 text-slate-400"
                      }`}>
                        {alert.severity}
                      </span>
                    </div>
                    <p className="text-[10px] text-slate-500 mt-0.5">{alert.message}</p>
                    <p className="text-[9px] font-mono text-slate-600 mt-1">{new Date(alert.created_at).toLocaleString()}</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Health History */}
      {health.history && safeArr<{ score: number; category: string; captured_at: string }>(health.history).length > 1 && (
        <div className="glass-panel p-4">
          <h3 className="text-xs font-bold font-mono text-slate-200 uppercase mb-3 flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-platform-400" /> Health History
          </h3>
          <div className="flex items-end gap-1 h-20">
            {safeArr<{ score: number; category: string; captured_at: string }>(health.history).map((h, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={`w-full rounded-t ${h.score >= 0.7 ? "bg-emerald-500" : h.score >= 0.4 ? "bg-amber-500" : "bg-red-500"}`}
                  style={{ height: `${h.score * 100}%` }}
                />
                <span className="text-[8px] font-mono text-slate-600">{new Date(h.captured_at).toLocaleDateString().slice(0, 5)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
