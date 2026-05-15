"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertTriangle, Clock, RotateCcw, Cpu, Bug, Activity, Loader2,
  Plus, ChevronDown, ChevronRight, X, Send, CheckCircle2, Shield,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface Incident {
  id: string;
  title: string;
  severity: "critical" | "high" | "medium" | "low";
  status: "active" | "mitigated" | "resolved";
  detected_at: string;
  affected_components: string[];
  description?: string;
}

interface TimelineEntry {
  timestamp: string;
  actor: string;
  action: string;
  detail: string;
}

interface IncidentDetail extends Incident {
  timeline: TimelineEntry[];
}

interface SystemDiagnostics {
  health_summary: string;
  active_incidents: number;
  recent_events: { event: string; timestamp: string; severity: string }[];
  recommendations: { action: string; reason: string; priority: string }[];
}

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-500/10 text-red-400 border-red-500/20",
  high: "bg-orange-500/10 text-orange-400 border-orange-500/20",
  medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  low: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

const SEVERITY_DOT: Record<string, string> = {
  critical: "bg-red-500 animate-pulse",
  high: "bg-orange-500",
  medium: "bg-amber-500",
  low: "bg-slate-500",
};

const STATUS_BADGE: Record<string, string> = {
  active: "bg-red-500/10 text-red-400 border-red-500/20",
  mitigated: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  resolved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
};

const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  transition: { duration: 0.4 },
};

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function IncidentsPage() {
  const queryClient = useQueryClient();
  const [selectedIncident, setSelectedIncident] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createTitle, setCreateTitle] = useState("");
  const [createSeverity, setCreateSeverity] = useState<string>("medium");
  const [createDescription, setCreateDescription] = useState("");
  const [createComponents, setCreateComponents] = useState("");
  const [timelineEntry, setTimelineEntry] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const { data: incidents, isLoading } = useQuery<Incident[]>({
    queryKey: ["incidents"],
    queryFn: () => fetchApi("/incident/incidents"),
    refetchInterval: 15000,
  });

  const { data: incidentDetail } = useQuery<IncidentDetail>({
    queryKey: ["incident-detail", selectedIncident],
    queryFn: () => fetchApi(`/incident/incidents/${selectedIncident}`),
    enabled: !!selectedIncident,
  });

  const { data: diagnostics } = useQuery<SystemDiagnostics>({
    queryKey: ["incident-diagnostics"],
    queryFn: () => fetchApi("/incident/diagnostics"),
    refetchInterval: 15000,
  });

  const createMutation = useMutation({
    mutationFn: (data: { title: string; severity: string; description: string; affected_components: string[] }) =>
      fetchApi("/incident/incidents", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      setShowCreateForm(false);
      setCreateTitle("");
      setCreateSeverity("medium");
      setCreateDescription("");
      setCreateComponents("");
      setFeedback("Incident created");
      setTimeout(() => setFeedback(null), 3000);
    },
  });

  const timelineMutation = useMutation({
    mutationFn: (data: { incident_id: string; action: string; detail: string }) =>
      fetchApi(`/incident/incidents/${data.incident_id}/timeline`, {
        method: "POST",
        body: JSON.stringify({ action: data.action, detail: data.detail, actor: "operator" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incident-detail", selectedIncident] });
      setTimelineEntry("");
      setFeedback("Timeline entry added");
      setTimeout(() => setFeedback(null), 3000);
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (incidentId: string) =>
      fetchApi(`/incident/incidents/${incidentId}/resolve`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incidents"] });
      setSelectedIncident(null);
      setFeedback("Incident resolved");
      setTimeout(() => setFeedback(null), 3000);
    },
  });

  const incidentList = incidents || [];
  const activeIncidents = incidentList.filter(i => i.status === "active");
  const resolvedCount = incidentList.filter(i => i.status === "resolved").length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">INCIDENTS</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Operational Incident Management Center</p>
        </div>
        <div className="flex items-center gap-3">
          {activeIncidents.length > 0 && (
            <span className="px-3 py-1.5 rounded-md bg-red-500/10 border border-red-500/20 text-xs font-mono text-red-400 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              {activeIncidents.length} ACTIVE
            </span>
          )}
          <button
            onClick={() => setShowCreateForm(true)}
            className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-mono flex items-center gap-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Incident
          </button>
          {feedback && (
            <motion.span initial={{ opacity: 0, y: -5 }} animate={{ opacity: 1, y: 0 }} className="text-xs font-mono text-emerald-400">
              &gt; {feedback}
            </motion.span>
          )}
        </div>
      </div>

      {isLoading && incidentList.length === 0 ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Active Incidents Panel */}
            <motion.div {...slideUp} className="glass-panel p-6">
              <div className="flex items-center gap-2 mb-4">
                <AlertTriangle className="w-5 h-5 text-red-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">ACTIVE_INCIDENTS</h3>
                {activeIncidents.length > 0 && (
                  <span className="ml-auto px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-xs font-mono text-red-400">
                    {activeIncidents.length}
                  </span>
                )}
              </div>
              <div className="space-y-2 max-h-[400px] overflow-auto custom-scrollbar">
                {incidentList.length === 0 ? (
                  <div className="flex flex-col items-center py-8">
                    <Shield className="w-8 h-8 text-emerald-500 mb-2" />
                    <span className="text-sm font-mono text-slate-500">NO_INCIDENTS</span>
                  </div>
                ) : (
                  incidentList.map((inc, i) => (
                    <motion.div
                      key={inc.id}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      onClick={() => setSelectedIncident(selectedIncident === inc.id ? null : inc.id)}
                      className={`p-3 rounded-md border cursor-pointer transition-all ${
                        selectedIncident === inc.id
                          ? "bg-surface-border/50 border-platform-500/30"
                          : "bg-surface-darker/50 border-surface-border/50 hover:border-surface-border"
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <span className={`w-2 h-2 rounded-full mt-1 flex-shrink-0 ${SEVERITY_DOT[inc.severity]}`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-mono text-slate-300 truncate">{inc.title}</span>
                            <span className={`ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded border ${SEVERITY_BADGE[inc.severity]}`}>
                              {inc.severity.toUpperCase()}
                            </span>
                          </div>
                          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-600">
                            <span className={`px-1 py-0.5 rounded border ${STATUS_BADGE[inc.status]}`}>{inc.status.toUpperCase()}</span>
                            <span>{new Date(inc.detected_at).toLocaleTimeString()}</span>
                          </div>
                          {inc.affected_components.length > 0 && (
                            <div className="flex flex-wrap gap-1 mt-1">
                              {inc.affected_components.map(c => (
                                <span key={c} className="px-1 py-0.5 rounded text-[9px] font-mono bg-slate-500/10 text-slate-500">{c}</span>
                              ))}
                            </div>
                          )}
                        </div>
                        <ChevronDown className={`w-4 h-4 text-slate-600 transition-transform ${selectedIncident === inc.id ? "rotate-180" : ""}`} />
                      </div>
                    </motion.div>
                  ))
                )}
              </div>
            </motion.div>

            {/* Incident Timeline View */}
            <motion.div {...slideUp} transition={{ delay: 0.05 }} className="glass-panel p-6 lg:col-span-2">
              <div className="flex items-center gap-2 mb-4">
                <Clock className="w-5 h-5 text-platform-500" />
                <h3 className="text-lg font-medium text-slate-200 font-mono">INCIDENT_TIMELINE</h3>
                {selectedIncident && (
                  <div className="ml-auto flex items-center gap-2">
                    <input
                      type="text"
                      value={timelineEntry}
                      onChange={e => setTimelineEntry(e.target.value)}
                      placeholder="Add timeline entry..."
                      className="w-48 px-3 py-1.5 bg-surface-darker border border-surface-border rounded text-xs font-mono text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500"
                    />
                    <button
                      onClick={() => selectedIncident && timelineEntry && timelineMutation.mutate({ incident_id: selectedIncident, action: "manual_entry", detail: timelineEntry })}
                      disabled={!timelineEntry || timelineMutation.isPending}
                      className="p-1.5 rounded bg-platform-600 hover:bg-platform-500 text-white disabled:opacity-50"
                    >
                      {timelineMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => selectedIncident && resolveMutation.mutate(selectedIncident)}
                      disabled={resolveMutation.isPending}
                      className="px-3 py-1.5 rounded bg-emerald-600/20 border border-emerald-500/30 text-emerald-400 text-xs font-mono flex items-center gap-1 hover:bg-emerald-600/30 transition-colors disabled:opacity-50"
                    >
                      {resolveMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                      Resolve
                    </button>
                  </div>
                )}
              </div>
              {!selectedIncident ? (
                <div className="flex flex-col items-center py-12">
                  <Clock className="w-10 h-10 text-slate-600 mb-3" />
                  <span className="text-sm font-mono text-slate-500">Select an incident to view timeline</span>
                </div>
              ) : !incidentDetail ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
                </div>
              ) : (
                <div className="relative">
                  <div className="absolute left-4 top-0 bottom-0 w-px bg-surface-border" />
                  <div className="space-y-4 relative">
                    {incidentDetail.timeline.length === 0 ? (
                      <div className="text-sm font-mono text-slate-500 py-8 text-center">No timeline entries yet</div>
                    ) : (
                      incidentDetail.timeline.map((entry, i) => (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.05 }}
                          className="flex items-start gap-4 pl-10 relative"
                        >
                          <div className="absolute left-[14px] top-1.5 w-[5px] h-[5px] rounded-full bg-platform-500" />
                          <div className="flex-1 p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] font-mono text-platform-400">{entry.actor}</span>
                              <span className="text-[9px] font-mono text-slate-600">{new Date(entry.timestamp).toLocaleTimeString()}</span>
                            </div>
                            <p className="text-xs font-mono text-slate-300">{entry.action.replace(/_/g, " ")}</p>
                            {entry.detail && (
                              <p className="text-[10px] font-mono text-slate-500 mt-1">{entry.detail}</p>
                            )}
                          </div>
                        </motion.div>
                      ))
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          </div>

          {/* System Diagnostics Dashboard */}
          <motion.div {...slideUp} transition={{ delay: 0.1 }} className="glass-panel p-6">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-5 h-5 text-emerald-500" />
              <h3 className="text-lg font-medium text-slate-200 font-mono">SYSTEM_DIAGNOSTICS</h3>
              {diagnostics && (
                <span className={`ml-auto text-xs font-mono px-2 py-0.5 rounded border ${
                  diagnostics.health_summary === "healthy" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
                  "bg-amber-500/10 text-amber-400 border-amber-500/20"
                }`}>
                  {diagnostics.health_summary.toUpperCase()}
                </span>
              )}
            </div>
            {!diagnostics ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div>
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Health Summary</p>
                  <p className="text-sm font-mono text-slate-300">{diagnostics.health_summary}</p>
                  <p className="text-[10px] font-mono text-slate-600 mt-1">{diagnostics.active_incidents} active incidents</p>
                </div>
                <div>
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Recent Events</p>
                  <div className="space-y-1">
                    {diagnostics.recent_events.slice(0, 5).map((e, i) => (
                      <div key={i} className="flex items-center gap-2 text-[10px] font-mono">
                        <span className={`w-1.5 h-1.5 rounded-full ${e.severity === "critical" ? "bg-red-500" : e.severity === "high" ? "bg-orange-500" : "bg-amber-500"}`} />
                        <span className="text-slate-400 truncate">{e.event}</span>
                        <span className="text-slate-600 ml-auto">{new Date(e.timestamp).toLocaleTimeString()}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div>
                  <p className="text-[10px] font-mono text-slate-500 uppercase mb-2">Recommendations</p>
                  <div className="space-y-1">
                    {diagnostics.recommendations.map((r, i) => (
                      <div key={i} className="flex items-start gap-2 text-[10px] font-mono">
                        <span className={`mt-0.5 px-1 py-0.5 rounded text-[8px] font-bold ${
                          r.priority === "P0" ? "bg-red-500/10 text-red-400" : r.priority === "P1" ? "bg-amber-500/10 text-amber-400" : "bg-slate-500/10 text-slate-500"
                        }`}>{r.priority}</span>
                        <div>
                          <span className="text-slate-300">{r.action.replace(/_/g, " ")}</span>
                          <p className="text-slate-600">{r.reason.replace(/_/g, " ")}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </motion.div>

          {/* Quick Actions */}
          <motion.div {...fadeIn} className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass-panel p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-surface-darker border border-surface-border">
                <RotateCcw className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="text-[10px] font-mono text-slate-500 uppercase">Rollback Checklist</p>
                <p className="text-xs font-mono text-slate-300">Ready</p>
              </div>
            </div>
            <div className="glass-panel p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-surface-darker border border-surface-border">
                <Cpu className="w-5 h-5 text-platform-400" />
              </div>
              <div>
                <p className="text-[10px] font-mono text-slate-500 uppercase">Queue Intervention</p>
                <p className="text-xs font-mono text-slate-300">Standing by</p>
              </div>
            </div>
            <div className="glass-panel p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-surface-darker border border-surface-border">
                <Activity className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <p className="text-[10px] font-mono text-slate-500 uppercase">Workflow Recovery</p>
                <p className="text-xs font-mono text-slate-300">Available</p>
              </div>
            </div>
            <div className="glass-panel p-4 flex items-center gap-3">
              <div className="p-2 rounded-lg bg-surface-darker border border-surface-border">
                <Bug className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <p className="text-[10px] font-mono text-slate-500 uppercase">Replay Debug</p>
                <p className="text-xs font-mono text-slate-300">Armed</p>
              </div>
            </div>
          </motion.div>
        </>
      )}

      {/* Create Incident Modal */}
      <AnimatePresence>
        {showCreateForm && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-panel w-full max-w-lg"
            >
              <div className="p-6 border-b border-surface-border flex justify-between items-center">
                <h2 className="text-lg font-bold text-slate-100 font-mono">Create Incident</h2>
                <button onClick={() => setShowCreateForm(false)} className="p-1 hover:bg-surface-border rounded-full">
                  <X className="w-5 h-5 text-slate-400" />
                </button>
              </div>
              <div className="p-6 space-y-4">
                <div>
                  <label className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Title</label>
                  <input
                    type="text"
                    value={createTitle}
                    onChange={e => setCreateTitle(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-darker border border-surface-border rounded text-sm font-mono text-slate-200 focus:outline-none focus:border-platform-500"
                    placeholder="Brief description"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Severity</label>
                  <div className="flex gap-2">
                    {["critical", "high", "medium", "low"].map(s => (
                      <button
                        key={s}
                        onClick={() => setCreateSeverity(s)}
                        className={`px-3 py-1.5 text-xs font-mono rounded border transition-colors ${
                          createSeverity === s
                            ? SEVERITY_BADGE[s]
                            : "bg-surface-darker border-surface-border text-slate-500"
                        }`}
                      >
                        {s.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Description</label>
                  <textarea
                    value={createDescription}
                    onChange={e => setCreateDescription(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-darker border border-surface-border rounded text-sm font-mono text-slate-200 focus:outline-none focus:border-platform-500 h-20"
                    placeholder="Detailed description"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-mono text-slate-500 uppercase block mb-1">Affected Components</label>
                  <input
                    type="text"
                    value={createComponents}
                    onChange={e => setCreateComponents(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-darker border border-surface-border rounded text-sm font-mono text-slate-200 focus:outline-none focus:border-platform-500"
                    placeholder="comma-separated: database, redis, kafka"
                  />
                </div>
              </div>
              <div className="p-6 border-t border-surface-border flex justify-end gap-3">
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={() => createMutation.mutate({
                    title: createTitle,
                    severity: createSeverity,
                    description: createDescription,
                    affected_components: createComponents.split(",").map(s => s.trim()).filter(Boolean),
                  })}
                  disabled={!createTitle || createMutation.isPending}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-md text-xs font-mono flex items-center gap-2 transition-colors disabled:opacity-50"
                >
                  {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <AlertTriangle className="w-4 h-4" />}
                  Create Incident
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
