"use client";

import { motion } from "framer-motion";
import {
  Shield, Activity, Users, Lock, CheckCircle2, Loader2, Clock,
  XCircle, AlertTriangle, FileText,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface AuditEntry {
  id: string;
  timestamp: string;
  actor: string;
  action: string;
  resource: string;
  detail: string;
}

interface ComplianceReport {
  overall_status: string;
  checks: { check: string; status: string; detail: string }[];
  score: number;
}

interface RBACHardening {
  roles: { role: string; user_count: number; permissions: string[]; risk_level: string }[];
  recommendations: string[];
}

interface AccessControlEntry {
  resource: string;
  principal: string;
  access_level: string;
  granted_at: string;
  expires_at: string;
}

interface WorkflowAuthorization {
  workflow_type: string;
  authorization_required: boolean;
  authorized_roles: string[];
  pending_approvals: number;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function GovernancePage() {
  const { data: auditLog, isLoading: loadingAudit } = useQuery<AuditEntry[]>({
    queryKey: ["governance-audit"],
    queryFn: () => fetchApi("/governance/audit-export"),
    refetchInterval: 15000,
  });

  const { data: compliance, isLoading: loadingCompliance } = useQuery<ComplianceReport>({
    queryKey: ["governance-compliance"],
    queryFn: () => fetchApi("/governance/compliance-report"),
    refetchInterval: 15000,
  });

  const { data: rbac, isLoading: loadingRbac } = useQuery<RBACHardening>({
    queryKey: ["governance-rbac"],
    queryFn: () => fetchApi("/governance/rbac-hardening"),
    refetchInterval: 15000,
  });

  const { data: accessControl, isLoading: loadingAccess } = useQuery<AccessControlEntry[]>({
    queryKey: ["governance-access-control"],
    queryFn: () => fetchApi("/governance/infra-access-control"),
    refetchInterval: 15000,
  });

  const { data: workflowAuth, isLoading: loadingWorkflow } = useQuery<WorkflowAuthorization[]>({
    queryKey: ["governance-workflow-auth"],
    queryFn: () => fetchApi("/governance/workflow-authorization"),
    refetchInterval: 15000,
  });

  const auditEntries = auditLog || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">GOVERNANCE</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Enterprise Governance Dashboard</p>
        </div>
        {compliance && (
          <span className={`px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 ${
            compliance.overall_status === "compliant" ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" :
            "bg-amber-500/10 text-amber-400 border-amber-500/20"
          }`}>
            <Shield className="w-4 h-4" />
            {compliance.overall_status.toUpperCase()} ({Math.round(compliance.score)}%)
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Audit Log */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <FileText className="w-5 h-5 text-platform-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">AUDIT_LOG</h3>
            <span className="ml-auto text-xs font-mono text-slate-500">{auditEntries.length} entries</span>
          </div>
          {loadingAudit ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : auditEntries.length === 0 ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No audit entries</div>
          ) : (
            <div className="space-y-2 max-h-[350px] overflow-auto custom-scrollbar">
              {auditEntries.slice(0, 20).map((entry, i) => (
                <motion.div
                  key={entry.id || i}
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="p-2.5 rounded bg-surface-darker/30 border border-surface-border/30"
                >
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[10px] font-mono text-platform-400">{entry.actor}</span>
                    <span className="text-[10px] font-mono text-slate-500">{entry.action.replace(/_/g, " ")}</span>
                    <span className="text-[9px] font-mono text-slate-600 ml-auto">{new Date(entry.timestamp).toLocaleTimeString()}</span>
                  </div>
                  <p className="text-[10px] font-mono text-slate-400">{entry.resource}</p>
                  {entry.detail && <p className="text-[9px] font-mono text-slate-600">{entry.detail}</p>}
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>

        {/* Compliance Report */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <CheckCircle2 className="w-5 h-5 text-emerald-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">COMPLIANCE_REPORT</h3>
            {compliance && (
              <span className={`ml-auto text-lg font-bold font-mono ${compliance.score >= 80 ? "text-emerald-400" : compliance.score >= 50 ? "text-amber-400" : "text-red-400"}`}>
                {Math.round(compliance.score)}%
              </span>
            )}
          </div>
          {loadingCompliance ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !compliance ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No compliance data</div>
          ) : (
            <div className="space-y-2">
              {compliance.checks.map((c, i) => (
                <motion.div
                  key={c.check || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.03 }}
                  className="flex items-center justify-between p-2.5 rounded bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center gap-2">
                    {c.status === "pass" ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                    ) : c.status === "fail" ? (
                      <XCircle className="w-4 h-4 text-red-500" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-500" />
                    )}
                    <span className="text-xs font-mono text-slate-300">{c.check.replace(/_/g, " ")}</span>
                  </div>
                  <span className="text-[10px] font-mono text-slate-500">{c.detail}</span>
                </motion.div>
              ))}
            </div>
          )}
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RBAC Hardening */}
        <motion.div {...slideUp} className="glass-panel p-6">
          <div className="flex items-center gap-2 mb-4">
            <Users className="w-5 h-5 text-amber-500" />
            <h3 className="text-lg font-medium text-slate-200 font-mono">RBAC_HARDENING</h3>
          </div>
          {loadingRbac ? (
            <div className="flex items-center justify-center py-8"><Loader2 className="w-6 h-6 text-platform-500 animate-spin" /></div>
          ) : !rbac ? (
            <div className="text-center py-8 text-sm font-mono text-slate-500">No RBAC data</div>
          ) : (
            <div className="space-y-3">
              {rbac.roles.map((r, i) => (
                <motion.div
                  key={r.role || i}
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-slate-300">{r.role}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-slate-500">{r.user_count} users</span>
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        r.risk_level === "high" ? "bg-red-500/10 text-red-400" :
                        r.risk_level === "medium" ? "bg-amber-500/10 text-amber-400" :
                        "bg-emerald-500/10 text-emerald-400"
                      }`}>{r.risk_level.toUpperCase()}</span>
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {r.permissions.slice(0, 4).map(p => (
                      <span key={p} className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-surface-darker text-slate-500">{p}</span>
                    ))}
                    {r.permissions.length > 4 && (
                      <span className="text-[9px] font-mono text-slate-600">+{r.permissions.length - 4}</span>
                    )}
                  </div>
                </motion.div>
              ))}
              {rbac.recommendations.length > 0 && (
                <div className="pt-3 border-t border-surface-border space-y-1">
                  <p className="text-[10px] font-mono text-amber-400 uppercase">Recommendations</p>
                  {rbac.recommendations.map((r, i) => (
                    <p key={i} className="text-[10px] font-mono text-slate-400">&gt; {r.replace(/_/g, " ")}</p>
                  ))}
                </div>
              )}
            </div>
          )}
        </motion.div>

        {/* Access Control + Workflow Auth */}
        <div className="space-y-6">
          <motion.div {...slideUp} className="glass-panel p-6">
            <div className="flex items-center gap-2 mb-4">
              <Lock className="w-5 h-5 text-platform-500" />
              <h3 className="text-lg font-medium text-slate-200 font-mono">ACCESS_CONTROL</h3>
            </div>
            {loadingAccess ? (
              <div className="flex items-center justify-center py-4"><Loader2 className="w-5 h-5 text-platform-500 animate-spin" /></div>
            ) : !accessControl || accessControl.length === 0 ? (
              <div className="text-center py-4 text-sm font-mono text-slate-500">No access control entries</div>
            ) : (
              <div className="space-y-2 max-h-[200px] overflow-auto custom-scrollbar">
                {accessControl.map((a, i) => (
                  <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/30 border border-surface-border/30">
                    <div>
                      <span className="text-xs font-mono text-slate-300">{a.resource}</span>
                      <span className="text-[9px] font-mono text-slate-600 ml-2">{a.principal}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-mono px-1 py-0.5 rounded ${
                        a.access_level === "admin" ? "bg-red-500/10 text-red-400" :
                        a.access_level === "write" ? "bg-amber-500/10 text-amber-400" :
                        "bg-emerald-500/10 text-emerald-400"
                      }`}>{a.access_level.toUpperCase()}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>

          <motion.div {...slideUp} className="glass-panel p-6">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-5 h-5 text-purple-500" />
              <h3 className="text-lg font-medium text-slate-200 font-mono">WORKFLOW_AUTHORIZATION</h3>
            </div>
            {loadingWorkflow ? (
              <div className="flex items-center justify-center py-4"><Loader2 className="w-5 h-5 text-platform-500 animate-spin" /></div>
            ) : !workflowAuth || workflowAuth.length === 0 ? (
              <div className="text-center py-4 text-sm font-mono text-slate-500">No workflow authorization data</div>
            ) : (
              <div className="space-y-2">
                {workflowAuth.map((w, i) => (
                  <div key={w.workflow_type || i} className="flex items-center justify-between p-2.5 rounded bg-surface-darker/50 border border-surface-border/50">
                    <div>
                      <span className="text-xs font-mono text-slate-300">{w.workflow_type.replace(/_/g, " ")}</span>
                      {w.authorization_required && (
                        <span className="text-[9px] font-mono text-amber-400 ml-2">AUTH REQUIRED</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {w.pending_approvals > 0 && (
                        <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-amber-500/10 text-amber-400">{w.pending_approvals} pending</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
