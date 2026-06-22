"use client";

import { useState } from "react";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Loader2, RefreshCw, LayoutDashboard, Users, Target, DollarSign, BarChart3, Activity, Mail, MessageSquare, Link2, AlertTriangle, Clock, CheckCircle2, AlertCircle, Info, ArrowUpRight, ArrowDownRight, Shield, Bell, TrendingUp, TrendingDown } from "lucide-react";
import { safeArr, safeStr, safeNum, safeFixed, safeLocale, safeUpper, safeReplace, safeDate, safeDateTime } from "@/lib/safe";

function StatCard(p: { label: string; value: string; icon: any; color: string; subtitle?: string; trend?: string }) {
  return (
    <div className="glass-panel rounded-xl p-4 border border-surface-border">
      <div className="flex items-start justify-between">
        <div className={"p-2 rounded-lg " + p.color}>{p.icon}</div>
        {p.trend && (
          <div className={"flex items-center gap-1 text-xs " + (p.trend.startsWith("+") ? "text-emerald-400" : "text-red-400")}>
            {p.trend.startsWith("+") ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
            {p.trend.replace("+", "").replace("-", "")}%
          </div>
        )}
      </div>
      <div className="mt-3">
        <div className="text-2xl font-bold text-white">{p.value}</div>
        <div className="text-xs text-gray-400 mt-1">{p.label}</div>
        {p.subtitle && <div className="text-xs text-gray-500 mt-0.5">{p.subtitle}</div>}
      </div>
    </div>
  );
}

function CustomBadge(p: { text: string; colors: string }) {
  return <span className={"px-2 py-0.5 rounded text-xs font-medium " + p.colors}>{p.text}</span>;
}

export default function ExecutivePage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState("overview");

  const overviewQ = useQuery({ queryKey: ["exec-overview"], queryFn: () => fetchApi("/executive/overview"), refetchInterval: 60000 });
  const healthQ = useQuery({ queryKey: ["exec-health"], queryFn: () => fetchApi("/executive/health-matrix") });
  const risksQ = useQuery({ queryKey: ["exec-risks"], queryFn: () => fetchApi("/executive/risks"), refetchInterval: 30000 });
  const alertsQ = useQuery({ queryKey: ["exec-alerts"], queryFn: () => fetchApi("/executive/alerts"), refetchInterval: 30000 });
  const trendsQ = useQuery({ queryKey: ["exec-trends"], queryFn: () => fetchApi("/executive/trends?days=30") });
  const slaQ = useQuery({ queryKey: ["exec-sla"], queryFn: () => fetchApi("/executive/sla/summary") });
  const revQ = useQuery({ queryKey: ["exec-revenue"], queryFn: () => fetchApi("/executive/revenue") });
  const revHistQ = useQuery({ queryKey: ["exec-revenue-hist"], queryFn: () => fetchApi("/executive/revenue/history?days=30") });

  const ackM = useMutation({ mutationFn: (id: string) => fetchApi("/executive/alerts/" + id + "/acknowledge?assigned_to=Executive", { method: "POST" }), onSuccess: () => qc.invalidateQueries({ queryKey: ["exec-alerts"] }) });
  const resM = useMutation({ mutationFn: (id: string) => fetchApi("/executive/alerts/" + id + "/resolve?notes=Resolved", { method: "POST" }), onSuccess: () => qc.invalidateQueries({ queryKey: ["exec-alerts"] }) });
  const disM = useMutation({ mutationFn: (id: string) => fetchApi("/executive/alerts/" + id + "/dismiss", { method: "POST" }), onSuccess: () => qc.invalidateQueries({ queryKey: ["exec-alerts"] }) });

  const o = overviewQ.data as any;
  const h = healthQ.data as any;
  const risks = risksQ.data as any;
  const alerts = alertsQ.data as any;
  const trends = trendsQ.data as any;
  const sla = slaQ.data as any;
  const revHist = revHistQ.data as any;

  const tabs = [
    { id: "overview", label: "Executive Overview", icon: LayoutDashboard },
    { id: "health", label: "Customer Health", icon: Activity },
    { id: "risks", label: "Risk Engine", icon: Shield },
    { id: "alerts", label: "Alerts Center", icon: Bell },
    { id: "trends", label: "Strategic Trends", icon: BarChart3 },
    { id: "sla", label: "SLA Monitor", icon: Clock },
  ];

  if (overviewQ.isLoading) {
    return <div className="p-6 flex justify-center py-20"><Loader2 className="animate-spin text-platform-400" size={32} /></div>;
  }

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <LayoutDashboard className="text-platform-400" size={28} />
            Executive Control Center
          </h1>
          <p className="text-gray-400 text-sm mt-1">Real-time executive overview of BuildIT operations</p>
        </div>
        <button onClick={() => qc.invalidateQueries()} className="glass-panel px-4 py-2 rounded-lg text-sm text-gray-300 hover:text-white flex items-center gap-2 border border-surface-border">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className="flex gap-1 mb-6 overflow-x-auto pb-1">
        {tabs.map((t) => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className={"px-4 py-2 rounded-lg text-sm font-medium flex items-center gap-2 whitespace-nowrap transition-all " + (tab === t.id ? "bg-platform-600 text-white shadow-lg" : "text-gray-400 hover:text-white hover:bg-white/5")}>
            <t.icon size={14} /> {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && o && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            <StatCard label="Total Customers" value={String(o.total_customers)} icon={<Users size={18} />} color="bg-blue-500/20 text-blue-400" />
            <StatCard label="Active Campaigns" value={String(o.active_campaigns)} icon={<Target size={18} />} color="bg-emerald-500/20 text-emerald-400" subtitle={String(o.total_campaigns) + " total"} />
            <StatCard label="MRR" value={"$" + safeFixed(o.mrr / 1000, 0) + "k"} icon={<DollarSign size={18} />} color="bg-purple-500/20 text-purple-400" />
            <StatCard label="ARR" value={"$" + safeFixed(o.arr / 1000, 0) + "k"} icon={<BarChart3 size={18} />} color="bg-indigo-500/20 text-indigo-400" />
            <StatCard label="Campaign Health" value={safeFixed(o.avg_campaign_health * 100, 1) + "%"} icon={<Activity size={18} />} color="bg-teal-500/20 text-teal-400" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
            <StatCard label="Emails Sent" value={String(o.total_emails_sent)} icon={<Mail size={18} />} color="bg-cyan-500/20 text-cyan-400" />
            <StatCard label="Replies" value={String(o.total_replies)} icon={<MessageSquare size={18} />} color="bg-green-500/20 text-green-400" subtitle={safeFixed(o.avg_reply_rate * 100, 1) + "% rate"} />
            <StatCard label="Links Acquired" value={String(o.total_links_acquired)} icon={<Link2 size={18} />} color="bg-yellow-500/20 text-yellow-400" subtitle={safeFixed(o.avg_acquisition_rate * 100, 1) + "% rate"} />
            <StatCard label="Open Risks" value={String(o.open_risks)} icon={<AlertTriangle size={18} />} color="bg-red-500/20 text-red-400" />
            <StatCard label="Pending Approvals" value={String(o.pending_approvals)} icon={<Clock size={18} />} color="bg-orange-500/20 text-orange-400" />
          </div>
          {revHist && Array.isArray(revHist) && revHist.length > 0 && (
            <div className="glass-panel rounded-xl p-5 border border-surface-border">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">MRR Trend (30 days)</h3>
              <div className="flex items-end gap-[2px] h-32">
                {safeArr<any>(revHist).slice().reverse().map((d: any, i: number) => {
                  const vals = safeArr<any>(revHist).map((r: any) => r.mrr);
                  const mx = Math.max(...vals);
                  const ht = (safeNum(d.mrr) / mx) * 100;
                  return (
                    <div key={i} className="flex-1 flex flex-col items-center" title={safeStr(d.date) + ": $" + safeLocale(d.mrr)}>
                      <div className="w-full rounded-t bg-platform-600 hover:bg-platform-500 transition-all min-h-[2px]" style={{ height: String(Math.max(ht, 2)) + "%" }} />
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="glass-panel rounded-xl p-5 border border-surface-border lg:col-span-2">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Customer Health Distribution</h3>
              {h && (
                <div className="flex gap-3">
                  {["healthy","watch","at_risk","critical"].map((cat) => (
                    <div key={cat} className="flex-1 text-center">
                      <div className={"text-2xl font-bold " + (cat === "healthy" ? "text-emerald-400" : cat === "watch" ? "text-amber-400" : cat === "at_risk" ? "text-orange-400" : "text-red-400")}>
                        {(h.totals && h.totals[cat]) || 0}
                      </div>
                      <div className="text-xs text-gray-400 capitalize mt-1">{cat.replace("_", " ")}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="glass-panel rounded-xl p-5 border border-surface-border">
              <h3 className="text-sm font-semibold text-gray-300 mb-3">Quick Actions</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs"><span className="text-gray-400">Open Risks</span><span className="text-red-400 font-semibold">{String(o.open_risks)}</span></div>
                <div className="flex items-center justify-between text-xs"><span className="text-gray-400">Pending Approvals</span><span className="text-amber-400 font-semibold">{String(o.pending_approvals)}</span></div>
                <div className="flex items-center justify-between text-xs"><span className="text-gray-400">Active Customers</span><span className="text-emerald-400 font-semibold">{String(o.active_customers)}</span></div>
                <div className="flex items-center justify-between text-xs"><span className="text-gray-400">Avg Customer Health</span><span className="text-platform-400 font-semibold">{safeFixed(o.avg_customer_health * 100, 0) + "%"}</span></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === "health" && h && (
        <div>
          <div className="glass-panel rounded-xl border border-surface-border overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border text-gray-400 text-xs">
                  <th className="text-left p-3 font-medium">Customer</th>
                  <th className="text-left p-3 font-medium">Health</th>
                  <th className="text-left p-3 font-medium">Category</th>
                  <th className="text-right p-3 font-medium">Campaigns</th>
                  <th className="text-right p-3 font-medium">Campaign Health</th>
                  <th className="text-right p-3 font-medium">Response Rate</th>
                  <th className="text-right p-3 font-medium">Delivery Rate</th>
                  <th className="text-right p-3 font-medium">Issues</th>
                  <th className="text-right p-3 font-medium">Trend</th>
                </tr>
              </thead>
              <tbody>
                {(h.customers || []).slice(0, 50).map((c: any) => (
                  <tr key={c.client_id} className="border-b border-surface-border/50 hover:bg-white/5 transition-colors">
                    <td className="p-3 text-white font-medium">{c.customer_name}</td>
                    <td className="p-3">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 rounded-full bg-gray-700 overflow-hidden">
                          <div className={"h-full rounded-full " + (c.health_score >= 0.7 ? "bg-emerald-500" : c.health_score >= 0.5 ? "bg-amber-500" : c.health_score >= 0.3 ? "bg-orange-500" : "bg-red-500")} style={{ width: (c.health_score * 100) + "%" }} />
                        </div>
                        <span className="text-xs text-gray-300">{safeFixed(c.health_score * 100, 0)}%</span>
                      </div>
                    </td>
                    <td className="p-3"><CustomBadge text={c.health_category.replace("_", " ")} colors={c.health_category === "healthy" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : c.health_category === "watch" ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" : c.health_category === "at_risk" ? "bg-orange-500/20 text-orange-400 border border-orange-500/30" : "bg-red-500/20 text-red-400 border border-red-500/30"} /></td>
                    <td className="p-3 text-right text-gray-300">{c.campaign_count}</td>
                    <td className="p-3 text-right text-gray-300">{safeFixed(c.campaign_health_avg * 100, 0)}%</td>
                    <td className="p-3 text-right text-gray-300">{safeFixed(c.response_rate * 100, 1)}%</td>
                    <td className="p-3 text-right text-gray-300">{safeFixed(c.delivery_rate * 100, 1)}%</td>
                    <td className="p-3 text-right text-gray-300">{c.issue_count}</td>
                    <td className="p-3 text-right">
                      <span className={"text-xs " + (c.trend_direction === "improving" ? "text-emerald-400" : c.trend_direction === "declining" ? "text-red-400" : "text-gray-400")}>{c.trend_direction}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "risks" && risks && (
        <div className="space-y-2">
          {risks.filter((r: any) => !r.resolved).map((risk: any) => (
            <div key={risk.id} className="glass-panel rounded-xl p-4 border border-surface-border flex items-start gap-4">
              <div className="mt-0.5">{risk.risk_level === "critical" ? <AlertCircle size={14} className="text-red-400" /> : <AlertTriangle size={14} className="text-orange-400" />}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <CustomBadge text={risk.risk_level} colors={risk.risk_level === "critical" ? "bg-red-500/20 text-red-400" : risk.risk_level === "high" ? "bg-orange-500/20 text-orange-400" : risk.risk_level === "warning" ? "bg-amber-500/20 text-amber-400" : "bg-blue-500/20 text-blue-400"} />
                  <span className="text-sm font-medium text-white">{risk.title}</span>
                </div>
                <p className="text-xs text-gray-400">{risk.description}</p>
                {risk.customer_name && <p className="text-xs text-gray-500 mt-1">Customer: {risk.customer_name}</p>}
              </div>
              <div className="text-xs text-gray-500 whitespace-nowrap">{safeDate(risk.detected_at)}</div>
            </div>
          ))}
          {risks.filter((r: any) => !r.resolved).length === 0 && <div className="text-center py-8 text-gray-500">No active risks</div>}
        </div>
      )}

      {tab === "alerts" && alerts && (
        <div className="space-y-2">
          {alerts.map((alert: any) => (
            <div key={alert.id} className={"glass-panel rounded-xl p-4 border flex items-start gap-4 " + (alert.dismissed ? "opacity-40 border-surface-border" : alert.resolved ? "border-emerald-500/20" : "border-surface-border")}>
              <div className="mt-0.5">{alert.severity === "critical" ? <AlertCircle size={14} className="text-red-400" /> : alert.severity === "high" ? <AlertTriangle size={14} className="text-orange-400" /> : <Info size={14} className="text-blue-400" />}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <CustomBadge text={alert.severity} colors={alert.severity === "critical" ? "bg-red-500/20 text-red-400" : alert.severity === "high" ? "bg-orange-500/20 text-orange-400" : alert.severity === "warning" ? "bg-amber-500/20 text-amber-400" : "bg-blue-500/20 text-blue-400"} />
                  <span className={"text-sm font-medium " + (alert.resolved ? "text-gray-400" : "text-white")}>{alert.title}</span>
                  {alert.resolved && <CheckCircle2 size={12} className="text-emerald-400" />}
                </div>
                <p className="text-xs text-gray-400">{alert.description}</p>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                  <span>Source: {alert.source}</span>
                  {alert.entity_name && <span>Entity: {alert.entity_name}</span>}
                  <span>{safeDateTime(alert.occurred_at)}</span>
                </div>
              </div>
              {!alert.resolved && !alert.dismissed && (
                <div className="flex gap-1">
                  <button onClick={() => ackM.mutate(alert.id)} className="px-2 py-1 text-xs rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30">Ack</button>
                  <button onClick={() => resM.mutate(alert.id)} className="px-2 py-1 text-xs rounded bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30">Resolve</button>
                  <button onClick={() => disM.mutate(alert.id)} className="px-2 py-1 text-xs rounded bg-gray-500/20 text-gray-400 hover:bg-gray-500/30">Dismiss</button>
                </div>
              )}
            </div>
          ))}
          {alerts.length === 0 && <div className="text-center py-8 text-gray-500">No alerts</div>}
        </div>
      )}

      {tab === "trends" && trends && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {(trends.series || []).map((s: any) => {
            const vals = (s.data || []).map((p: any) => p.value);
            const mn = Math.min(...vals, 0);
            const mx = Math.max(...vals, 1);
            const rng = mx - mn || 1;
            return (
              <div key={s.metric} className="glass-panel rounded-xl p-5 border border-surface-border">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-semibold text-gray-300 capitalize">{s.metric.replace(/_/g, " ")}</h3>
                  <span className={"text-xs font-medium flex items-center gap-1 " + (s.trend_pct >= 0 ? "text-emerald-400" : "text-red-400")}>
                    {s.trend_pct >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                    {safeFixed(Math.abs(s.trend_pct), 1)}%
                  </span>
                </div>
                <div className="flex items-end gap-[2px] h-24">
                  {(s.data || []).map((p: any, i: number) => {
                    const ht = ((p.value - mn) / rng) * 100;
                    return (
                      <div key={i} className="flex-1 flex flex-col items-end justify-end" title={p.date + ": " + safeLocale(p.value)}>
                        <div className="w-full rounded-t transition-all min-h-[2px] opacity-70 hover:opacity-100"
                          style={{ height: String(Math.max(ht, 2)) + "%", backgroundColor: s.metric.includes("health") ? "#34d399" : s.metric.includes("risk") ? "#f87171" : s.metric.includes("mrr") ? "#a78bfa" : "#60a5fa" }} />
                      </div>
                    );
                  })}
                </div>
                <div className="mt-2 text-xs text-gray-500">Current: {s.data.length > 0 ? safeLocale(s.data[s.data.length - 1].value) : "-"}</div>
              </div>
            );
          })}
        </div>
      )}

      {tab === "sla" && sla && (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sla.map((s: any) => (
              <div key={s.sla_type} className="glass-panel rounded-xl p-5 border border-surface-border">
                <h3 className="text-sm font-semibold text-gray-300 capitalize mb-3">{s.sla_type.replace(/_/g, " ")}</h3>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs"><span className="text-gray-400">Total</span><span className="text-white">{s.total}</span></div>
                  <div className="flex items-center justify-between text-xs"><span className="text-gray-400">Breaches</span><span className={s.breaches > 0 ? "text-red-400 font-semibold" : "text-emerald-400"}>{s.breaches}</span></div>
                  <div className="flex items-center justify-between text-xs"><span className="text-gray-400">Warnings</span><span className={s.warnings > 0 ? "text-amber-400 font-semibold" : "text-gray-400"}>{s.warnings}</span></div>
                  <div className="flex items-center justify-between text-xs"><span className="text-gray-400">Avg Remaining</span><span className="text-gray-300">{safeFixed(s.avg_remaining_hours, 1)}h</span></div>
                </div>
                {(s.breaches > 0 || s.warnings > 0) && (
                  <div className="mt-3 pt-3 border-t border-surface-border">
                    <div className={"text-xs flex items-center gap-1 " + (s.breaches > 0 ? "text-red-400" : "text-amber-400")}>
                      <AlertTriangle size={12} />
                      {s.breaches > 0 ? s.breaches + " SLA breach(es) detected" : s.warnings + " approaching SLA deadline"}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
