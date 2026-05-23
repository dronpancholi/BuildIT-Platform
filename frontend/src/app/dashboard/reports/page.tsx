"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  FileText, Loader2, Download, TrendingUp, Target, Mail,
  Reply, Link2, Search, Users, BarChart3, Calendar,
  Bell, Clock, Plus, X, Edit2, Trash2
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface ReportMetrics {
  total_campaigns: number;
  active_campaigns: number;
  draft_campaigns: number;
  total_prospects: number;
  total_emails_sent: number;
  total_replies: number;
  total_follow_ups: number;
  links_acquired: number;
  target_links: number;
  acquisition_rate: number;
  reply_rate: number;
  avg_health_score: number;
  total_keywords: number;
  total_clusters: number;
}

interface CampaignReport {
  id: string;
  name: string;
  status: string;
  campaign_type: string;
  target_link_count: number;
  acquired_link_count: number;
  health_score: number;
}

interface ProspectReport {
  domain: string;
  domain_authority: number;
  relevance_score: number;
  composite_score: number;
  status: string;
}

interface EmailReport {
  prospect_domain: string;
  subject: string;
  status: string;
  sent_at: string | null;
  replied_at: string | null;
  follow_up_count: number;
}

interface FullReport {
  id: string;
  report_type: string;
  generated_at: string;
  metrics: ReportMetrics;
  campaigns: CampaignReport[];
  prospects: ProspectReport[];
  emails: EmailReport[];
  acquired_links: any[];
  keywords: any[];
  executive_summary: string;
}

function StatCard({ icon: Icon, label, value, color }: { icon: any; label: string; value: string | number; color: string }) {
  return (
    <div className="glass-panel p-4">
      <div className="flex items-center gap-2 mb-2">
        <Icon className={`w-4 h-4 ${color}`} />
        <span className="text-[10px] font-mono text-slate-500 uppercase">{label}</span>
      </div>
      <p className="text-2xl font-bold font-mono text-slate-100">{value}</p>
    </div>
  );
}

export default function ReportsPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"overview" | "campaigns" | "prospects" | "emails" | "links" | "keywords">("overview");
  const [report, setReport] = useState<FullReport | null>(null);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleForm, setScheduleForm] = useState({
    name: "",
    reportType: "full",
    frequency: "weekly",
    dayOfWeek: "monday",
    time: "09:00",
    recipients: "",
  });

  const { data: savedReports = [], isLoading: loadingSaved } = useQuery<any[]>({
    queryKey: ["reports-list"],
    queryFn: () => fetchApi(`/reports?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 30000,
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      fetchApi("/reports/generate", {
        method: "POST",
        body: JSON.stringify({ tenant_id: MOCK_TENANT_ID, report_type: "full" }),
      }),
    onSuccess: (data: any) => {
      setReport(data);
      queryClient.invalidateQueries({ queryKey: ["reports-list"] });
    },
  });

  const m = report?.metrics;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">REPORTS</h1>
          <p className="text-slate-400 mt-1 font-mono text-xs uppercase tracking-wider">Campaign performance & outreach analytics</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowScheduleModal(true)}
            className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-2"
          >
            <Clock className="w-4 h-4" /> Schedule
          </button>
          <button
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className="px-4 py-2 bg-platform-600 hover:bg-platform-500 disabled:opacity-50 text-white rounded-md text-xs font-bold font-mono transition-colors flex items-center gap-2"
          >
            {generateMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileText className="w-4 h-4" />
            )}
            Generate Report
          </button>
        </div>
      </div>

      {generateMutation.isError && (
        <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
          Failed to generate report: {(generateMutation.error as Error)?.message || "Unknown error"}
        </div>
      )}

      {report && (
        <>
          {/* Executive Summary */}
          <div className="glass-panel p-6 border-emerald-500/20 bg-emerald-500/5">
            <h3 className="text-sm font-mono text-emerald-400 mb-2 flex items-center gap-2">
              <BarChart3 className="w-4 h-4" /> Executive Summary
            </h3>
            <p className="text-sm text-slate-300">{report.executive_summary}</p>
            <p className="text-[10px] font-mono text-slate-600 mt-2">
              Generated: {new Date(report.generated_at).toLocaleString()}
            </p>
          </div>

          {/* Key Metrics */}
          {m && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard icon={Target} label="Campaigns" value={`${m.active_campaigns}/${m.total_campaigns}`} color="text-emerald-400" />
              <StatCard icon={Users} label="Prospects" value={m.total_prospects} color="text-platform-400" />
              <StatCard icon={Mail} label="Emails Sent" value={m.total_emails_sent} color="text-amber-400" />
              <StatCard icon={Reply} label="Replies" value={m.total_replies} color="text-blue-400" />
              <StatCard icon={Link2} label="Links Acquired" value={m.links_acquired} color="text-purple-400" />
              <StatCard icon={TrendingUp} label="Acq. Rate" value={`${(m.acquisition_rate * 100).toFixed(1)}%`} color="text-emerald-400" />
              <StatCard icon={Reply} label="Reply Rate" value={`${(m.reply_rate * 100).toFixed(1)}%`} color="text-blue-400" />
              <StatCard icon={Search} label="Keywords" value={m.total_keywords} color="text-indigo-400" />
            </div>
          )}

          {/* Tabs */}
          <div className="flex items-center gap-1 bg-surface-darker rounded-lg border border-surface-border p-0.5 w-fit">
            {(["overview", "campaigns", "prospects", "emails", "links", "keywords"] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3 py-1.5 text-[10px] font-mono rounded-md transition-all ${
                  activeTab === tab
                    ? "bg-platform-500/10 text-platform-400 border border-platform-500/20"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {tab.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          {activeTab === "campaigns" && (
            <div className="glass-panel overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="text-[10px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
                  <tr>
                    <th className="px-5 py-3 font-mono">Campaign</th>
                    <th className="px-5 py-3 font-mono">Status</th>
                    <th className="px-5 py-3 font-mono text-right">Links</th>
                    <th className="px-5 py-3 font-mono text-right">Health</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {report.campaigns.map((c) => (
                    <tr key={c.id} className="hover:bg-surface-border/30 transition-colors">
                      <td className="px-5 py-3">
                        <p className="text-sm font-medium text-slate-200">{c.name}</p>
                        <p className="text-[10px] text-slate-500 font-mono capitalize">{c.campaign_type.replace("_", " ")}</p>
                      </td>
                      <td className="px-5 py-3">
                        <span className={`px-2 py-0.5 text-[9px] font-mono rounded-full border uppercase ${
                          c.status === "active" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                          c.status === "draft" ? "bg-slate-500/10 text-slate-400 border-slate-500/20" :
                          "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        }`}>
                          {c.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-sm">
                        {c.acquired_link_count}/{c.target_link_count}
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-sm">
                        {(c.health_score * 100).toFixed(0)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === "prospects" && (
            <div className="glass-panel overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="text-[10px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
                  <tr>
                    <th className="px-5 py-3 font-mono">Domain</th>
                    <th className="px-5 py-3 font-mono text-right">DA</th>
                    <th className="px-5 py-3 font-mono text-right">Relevance</th>
                    <th className="px-5 py-3 font-mono text-right">Score</th>
                    <th className="px-5 py-3 font-mono">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {report.prospects.map((p, i) => (
                    <tr key={i} className="hover:bg-surface-border/30 transition-colors">
                      <td className="px-5 py-3 font-mono text-sm text-slate-200">{p.domain}</td>
                      <td className="px-5 py-3 text-right font-mono text-sm">{p.domain_authority.toFixed(0)}</td>
                      <td className="px-5 py-3 text-right font-mono text-sm">{(p.relevance_score * 100).toFixed(0)}%</td>
                      <td className="px-5 py-3 text-right font-mono text-sm font-bold text-emerald-400">{(p.composite_score * 100).toFixed(0)}%</td>
                      <td className="px-5 py-3">
                        <span className="text-[9px] font-mono text-slate-500 uppercase">{p.status}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === "emails" && (
            <div className="glass-panel overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="text-[10px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
                  <tr>
                    <th className="px-5 py-3 font-mono">Domain</th>
                    <th className="px-5 py-3 font-mono">Subject</th>
                    <th className="px-5 py-3 font-mono">Status</th>
                    <th className="px-5 py-3 font-mono text-right">Follow-ups</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {report.emails.map((e, i) => (
                    <tr key={i} className="hover:bg-surface-border/30 transition-colors">
                      <td className="px-5 py-3 font-mono text-sm text-slate-200">{e.prospect_domain}</td>
                      <td className="px-5 py-3 text-sm text-slate-400 truncate max-w-[300px]">{e.subject}</td>
                      <td className="px-5 py-3">
                        <span className={`px-2 py-0.5 text-[9px] font-mono rounded-full border uppercase ${
                          e.status === "sent" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                          e.status === "replied" ? "bg-blue-500/10 text-blue-400 border-blue-500/20" :
                          e.status === "link_acquired" ? "bg-purple-500/10 text-purple-400 border-purple-500/20" :
                          "bg-slate-500/10 text-slate-400 border-slate-500/20"
                        }`}>
                          {e.status}
                        </span>
                      </td>
                      <td className="px-5 py-3 text-right font-mono text-sm">{e.follow_up_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeTab === "links" && (
            <div className="glass-panel overflow-hidden">
              {report.acquired_links.length === 0 ? (
                <div className="p-12 text-center">
                  <Link2 className="w-8 h-8 text-slate-700 mx-auto mb-2" />
                  <p className="text-xs font-mono text-slate-500">No links acquired yet.</p>
                </div>
              ) : (
                <table className="w-full text-sm text-left">
                  <thead className="text-[10px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
                    <tr>
                      <th className="px-5 py-3 font-mono">Source URL</th>
                      <th className="px-5 py-3 font-mono">Anchor Text</th>
                      <th className="px-5 py-3 font-mono">Type</th>
                      <th className="px-5 py-3 font-mono text-right">DA</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border">
                    {report.acquired_links.map((l, i) => (
                      <tr key={i} className="hover:bg-surface-border/30 transition-colors">
                        <td className="px-5 py-3 font-mono text-xs text-platform-400 truncate max-w-[400px]">{l.source_url}</td>
                        <td className="px-5 py-3 text-sm text-slate-300">{l.anchor_text || "—"}</td>
                        <td className="px-5 py-3 text-sm text-slate-400">{l.link_type}</td>
                        <td className="px-5 py-3 text-right font-mono text-sm">{l.domain_authority?.toFixed(0) || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {activeTab === "keywords" && (
            <div className="glass-panel overflow-hidden">
              <table className="w-full text-sm text-left">
                <thead className="text-[10px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
                  <tr>
                    <th className="px-5 py-3 font-mono">Keyword</th>
                    <th className="px-5 py-3 font-mono text-right">Volume</th>
                    <th className="px-5 py-3 font-mono text-right">Difficulty</th>
                    <th className="px-5 py-3 font-mono text-right">CPC</th>
                    <th className="px-5 py-3 font-mono">Intent</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {report.keywords.slice(0, 30).map((k, i) => (
                    <tr key={i} className="hover:bg-surface-border/30 transition-colors">
                      <td className="px-5 py-3 font-mono text-sm text-slate-200">{k.keyword}</td>
                      <td className="px-5 py-3 text-right font-mono text-sm">{k.search_volume?.toLocaleString() || "—"}</td>
                      <td className="px-5 py-3 text-right font-mono text-sm">{k.difficulty?.toFixed(0) || "—"}</td>
                      <td className="px-5 py-3 text-right font-mono text-sm">${k.cpc?.toFixed(2) || "0.00"}</td>
                      <td className="px-5 py-3 text-xs text-slate-400 capitalize">{k.intent || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {/* Saved Reports */}
      <div className="glass-panel p-6">
        <h3 className="text-sm font-mono text-slate-400 mb-4 flex items-center gap-2">
          <Calendar className="w-4 h-4" /> Saved Reports
        </h3>
        {loadingSaved ? (
          <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
        ) : savedReports.length === 0 ? (
          <div className="text-center py-8">
            <Calendar className="w-8 h-8 text-slate-700 mx-auto mb-2" />
            <p className="text-xs text-slate-500">No saved reports yet. Generate your first report above.</p>
            <button
              onClick={() => setShowScheduleModal(true)}
              className="mt-3 px-4 py-2 bg-platform-600/20 hover:bg-platform-600/30 text-platform-400 border border-platform-500/20 rounded-lg text-xs font-mono transition-colors"
            >
              Schedule First Report
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {savedReports.map((r: any) => (
              <div key={r.id} className="flex items-center justify-between p-3 rounded-lg bg-surface-darker/50 border border-surface-border/50">
                <div>
                  <p className="text-sm font-mono text-slate-200 capitalize">{r.report_type} Report</p>
                  <p className="text-[10px] text-slate-500 font-mono">{new Date(r.generated_at).toLocaleString()}</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-0.5 text-[9px] font-mono rounded-full border uppercase ${
                    r.status === "scheduled" 
                      ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                      : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  }`}>
                    {r.status}
                  </span>
                  <button className="p-1 hover:bg-surface-border rounded transition-colors">
                    <Download className="w-4 h-4 text-slate-400" />
                  </button>
                  <button className="p-1 hover:bg-surface-border rounded transition-colors">
                    <Edit2 className="w-4 h-4 text-slate-400" />
                  </button>
                  <button className="p-1 hover:bg-red-500/10 rounded transition-colors">
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Schedule Report Modal */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="glass-panel w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-6 border-b border-surface-border bg-surface-darker/50 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-slate-100">Schedule Report</h2>
                <p className="text-sm text-slate-400">Set up automated report delivery</p>
              </div>
              <button
                onClick={() => setShowScheduleModal(false)}
                className="p-2 hover:bg-surface-border rounded-lg transition-colors"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Report Name</label>
                <input
                  type="text"
                  placeholder="e.g., Weekly Campaign Summary"
                  value={scheduleForm.name}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, name: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Report Type</label>
                <select
                  value={scheduleForm.reportType}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, reportType: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                >
                  <option value="full">Full Report</option>
                  <option value="campaigns">Campaigns Only</option>
                  <option value="prospects">Prospects Only</option>
                  <option value="emails">Email Performance</option>
                  <option value="links">Links Acquired</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Frequency</label>
                <select
                  value={scheduleForm.frequency}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, frequency: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>

              {scheduleForm.frequency === "weekly" && (
                <div>
                  <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Day of Week</label>
                  <select
                    value={scheduleForm.dayOfWeek}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, dayOfWeek: e.target.value })}
                    className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                  >
                    <option value="monday">Monday</option>
                    <option value="tuesday">Tuesday</option>
                    <option value="wednesday">Wednesday</option>
                    <option value="thursday">Thursday</option>
                    <option value="friday">Friday</option>
                    <option value="saturday">Saturday</option>
                    <option value="sunday">Sunday</option>
                  </select>
                </div>
              )}

              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Time</label>
                <input
                  type="time"
                  value={scheduleForm.time}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, time: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-400 uppercase mb-2">Recipients (comma-separated emails)</label>
                <input
                  type="text"
                  placeholder="team@company.com, manager@company.com"
                  value={scheduleForm.recipients}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, recipients: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-900 border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
                />
              </div>
            </div>

            <div className="p-6 border-t border-surface-border bg-surface-darker/50 flex gap-3">
              <button
                onClick={() => setShowScheduleModal(false)}
                className="px-4 py-2 bg-surface-darker hover:bg-surface-border border border-surface-border text-slate-300 rounded-lg text-xs font-mono transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  // Would call schedule mutation
                  setShowScheduleModal(false);
                  setScheduleForm({
                    name: "",
                    reportType: "full",
                    frequency: "weekly",
                    dayOfWeek: "monday",
                    time: "09:00",
                    recipients: "",
                  });
                }}
                className="flex-1 px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-lg text-xs font-bold font-mono transition-colors flex items-center justify-center gap-2"
              >
                <Bell className="w-4 h-4" /> Schedule Report
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
