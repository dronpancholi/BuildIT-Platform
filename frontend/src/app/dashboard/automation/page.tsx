"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { cn } from "@/lib/utils";
import {
  Activity, RefreshCw, CheckCircle2, XCircle, Clock,
  Play, AlertCircle, Loader2, Zap, FileText, Settings,
  Shield, Mail, Building, ChevronDown, ChevronUp,
} from "lucide-react";

interface AutomationRule {
  id: string;
  name: string;
  description: string;
  source: string;
  threshold: number | null;
  days_threshold: number | null;
  enabled: boolean;
}

interface ScanResult {
  scanned_at: string;
  campaigns_scanned: number;
  citations_scanned: number;
  outreach_scanned: number;
  profiles_scanned: number;
  tasks_created: number;
  tasks_skipped: number;
  tasks_by_category: Record<string, number>;
}

interface AuditEntry {
  timestamp: string;
  rule_id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  task_created: boolean;
  task_id: string | null;
  skipped: boolean;
  skip_reason: string | null;
}

function getSourceIcon(source: string) {
  switch (source) {
    case "campaign_health": return <Activity className="w-4 h-4 text-blue-400" />;
    case "citation_failure": return <XCircle className="w-4 h-4 text-red-400" />;
    case "outreach_followup": return <Mail className="w-4 h-4 text-amber-400" />;
    case "stale_campaign": return <Clock className="w-4 h-4 text-slate-400" />;
    case "incomplete_profile": return <Building className="w-4 h-4 text-purple-400" />;
    default: return <Zap className="w-4 h-4 text-platform-400" />;
  }
}

function StatusBadge({ enabled }: { enabled: boolean }) {
  return (
    <span className={cn("px-2 py-0.5 text-[10px] font-mono rounded-full border uppercase",
      enabled ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" : "bg-slate-500/20 text-slate-400 border-slate-500/30")}>
      {enabled ? "Enabled" : "Disabled"}
    </span>
  );
}

export default function WorkflowAutomationPage() {
  const queryClient = useQueryClient();
  const [showAudit, setShowAudit] = useState(false);
  const [expandedRule, setExpandedRule] = useState<string | null>(null);

  const { data: rules = [], isLoading: rulesLoading } = useQuery<AutomationRule[]>({
    queryKey: ["workflow-automation-rules"],
    queryFn: () => fetchApi(`/workflow-automation/automation-rules?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 30000,
  });

  const { data: auditLog = [], isLoading: auditLoading } = useQuery<AuditEntry[]>({
    queryKey: ["workflow-automation-audit"],
    queryFn: () => fetchApi(`/workflow-automation/audit?tenant_id=${MOCK_TENANT_ID}`),
    enabled: showAudit,
  });

  const scanMutation = useMutation({
    mutationFn: () => fetchApi(`/workflow-automation/scan-and-create-tasks?tenant_id=${MOCK_TENANT_ID}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["workflow-automation-audit"] });
      queryClient.invalidateQueries({ queryKey: ["workflow-automation-rules"] });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ rule_id, enabled }: { rule_id: string; enabled: boolean }) =>
      fetchApi(`/workflow-automation/toggle-rule?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({ rule_id, enabled }),
      }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["workflow-automation-rules"] }); },
  });

  const enabledCount = rules.filter((r) => r.enabled).length;
  const scanResult = scanMutation.data as ScanResult | undefined;

  return (
    <div className="p-6 max-w-[1600px] mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Zap className="text-platform-400" size={28} />
            Workflow Automation
          </h1>
          <p className="text-gray-400 text-sm mt-1">Automated task creation from platform intelligence</p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={() => setShowAudit(!showAudit)}>
            <FileText className="w-3.5 h-3.5 mr-1" /> {showAudit ? "Hide" : "Show"} Audit Log
          </Button>
          <Button
            size="sm"
            className="bg-platform-600 hover:bg-platform-500 text-white"
            onClick={() => scanMutation.mutate()}
            disabled={scanMutation.isPending}
          >
            {scanMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin mr-1" /> : <RefreshCw className="w-3.5 h-3.5 mr-1" />}
            Scan Now
          </Button>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="glass-panel p-4 rounded-xl border border-surface-border">
          <div className="flex items-center gap-2 mb-2">
            <Settings className="w-4 h-4 text-platform-400" />
            <span className="text-[10px] font-mono text-slate-500 uppercase">Active Rules</span>
          </div>
          <p className="text-2xl font-bold font-mono text-platform-400">{enabledCount}/{rules.length}</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-surface-border">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-[10px] font-mono text-slate-500 uppercase">Tasks Created</span>
          </div>
          <p className="text-2xl font-bold font-mono text-emerald-400">{scanResult?.tasks_created ?? 0}</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-surface-border">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="w-4 h-4 text-amber-400" />
            <span className="text-[10px] font-mono text-slate-500 uppercase">Skipped</span>
          </div>
          <p className="text-2xl font-bold font-mono text-amber-400">{scanResult?.tasks_skipped ?? 0}</p>
        </div>
        <div className="glass-panel p-4 rounded-xl border border-surface-border">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-4 h-4 text-slate-400" />
            <span className="text-[10px] font-mono text-slate-500 uppercase">Scan Sources</span>
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">
            {(scanResult?.campaigns_scanned ?? 0) + (scanResult?.citations_scanned ?? 0) + (scanResult?.outreach_scanned ?? 0) + (scanResult?.profiles_scanned ?? 0)}
          </p>
        </div>
      </div>

      {/* Last scan result */}
      <AnimatePresence>
        {scanResult && (
          <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}>
            <div className="glass-panel p-4 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span className="text-xs font-mono text-emerald-400">Last scan completed</span>
                <span className="text-[10px] font-mono text-slate-500">{new Date(scanResult.scanned_at).toLocaleTimeString()}</span>
              </div>
              <div className="flex flex-wrap gap-3 text-[10px] font-mono text-slate-400">
                <span>Campaigns: {scanResult.campaigns_scanned}</span>
                <span>Citations: {scanResult.citations_scanned}</span>
                <span>Outreach: {scanResult.outreach_scanned}</span>
                <span>Profiles: {scanResult.profiles_scanned}</span>
                <span className="text-emerald-400">Created: {scanResult.tasks_created}</span>
                <span className="text-amber-400">Skipped: {scanResult.tasks_skipped}</span>
              </div>
              {Object.keys(scanResult.tasks_by_category).length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {Object.entries(scanResult.tasks_by_category).map(([cat, count]) => (
                    <span key={cat} className="px-2 py-0.5 bg-platform-500/10 border border-platform-500/20 rounded text-[9px] font-mono text-platform-300">
                      {cat.replace(/_/g, " ")}: {count}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Rules List */}
      <div>
        <h2 className="text-sm font-mono text-slate-400 uppercase mb-3 flex items-center gap-2">
          <Shield className="w-4 h-4" /> Automation Rules
        </h2>
        {rulesLoading ? (
          <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
        ) : rules.length === 0 ? (
          <EmptyState title="No automation rules" description="Rules will appear here once defined." />
        ) : (
          <div className="space-y-2">
            {rules.map((rule) => {
              const isExpanded = expandedRule === rule.id;
              return (
                <div key={rule.id} className="glass-panel rounded-xl border border-surface-border overflow-hidden">
                  <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-white/5 transition-colors" onClick={() => setExpandedRule(isExpanded ? null : rule.id)}>
                    <div className="flex items-center gap-3">
                      {getSourceIcon(rule.source)}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-slate-200">{rule.name}</span>
                          <StatusBadge enabled={rule.enabled} />
                        </div>
                        <p className="text-[10px] font-mono text-slate-500 mt-0.5">{rule.description}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant={rule.enabled ? "destructive" : "default"}
                        className={cn(!rule.enabled && "bg-emerald-600 hover:bg-emerald-500")}
                        onClick={(e) => { e.stopPropagation(); toggleMutation.mutate({ rule_id: rule.id, enabled: !rule.enabled }); }}
                        disabled={toggleMutation.isPending}
                      >
                        {rule.enabled ? "Disable" : "Enable"}
                      </Button>
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
                    </div>
                  </div>

                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
                        <div className="p-4 pt-0 border-t border-surface-border">
                          <dl className="grid grid-cols-2 gap-2 text-[10px] font-mono mt-3">
                            <div><dt className="text-slate-500 uppercase">Source</dt><dd className="text-slate-300">{rule.source}</dd></div>
                            <div><dt className="text-slate-500 uppercase">Threshold</dt><dd className="text-slate-300">{rule.threshold != null ? `${(rule.threshold * 100).toFixed(0)}%` : rule.days_threshold != null ? `${rule.days_threshold} days` : "—"}</dd></div>
                          </dl>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Audit Log */}
      <AnimatePresence>
        {showAudit && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden">
            <div>
              <h2 className="text-sm font-mono text-slate-400 uppercase mb-3 flex items-center gap-2">
                <FileText className="w-4 h-4" /> Audit Log
              </h2>
              <div className="glass-panel rounded-xl border border-surface-border overflow-hidden">
                {auditLoading ? (
                  <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
                ) : auditLog.length === 0 ? (
                  <EmptyState title="No audit entries" description="Run a scan to see automated actions here." />
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-surface-border text-gray-400 text-[10px] uppercase">
                        <th className="text-left p-3 font-mono">Time</th>
                        <th className="text-left p-3 font-mono">Rule</th>
                        <th className="text-left p-3 font-mono">Action</th>
                        <th className="text-left p-3 font-mono">Entity</th>
                        <th className="text-center p-3 font-mono">Result</th>
                      </tr>
                    </thead>
                    <tbody>
                      {auditLog.map((entry, i) => (
                        <tr key={i} className="border-b border-surface-border/50 hover:bg-white/5 transition-colors">
                          <td className="p-3 text-xs font-mono text-slate-400">{new Date(entry.timestamp).toLocaleTimeString()}</td>
                          <td className="p-3 text-xs font-mono text-platform-400">{entry.rule_id.replace(/_/g, " ")}</td>
                          <td className="p-3 text-xs font-mono text-slate-300">{entry.action}</td>
                          <td className="p-3 text-xs font-mono text-slate-400">{entry.entity_type}{entry.entity_id ? ` (${entry.entity_id.slice(0, 8)})` : ""}</td>
                          <td className="p-3 text-center">
                            {entry.task_created ? (
                              <span className="px-2 py-0.5 text-[10px] font-mono rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Created</span>
                            ) : entry.skipped ? (
                              <span className="px-2 py-0.5 text-[10px] font-mono rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">Skipped</span>
                            ) : (
                              <span className="px-2 py-0.5 text-[10px] font-mono rounded-full bg-slate-500/20 text-slate-400 border border-slate-500/30">—</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
