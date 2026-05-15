"use client";

import { motion, AnimatePresence } from "framer-motion";
import { ShieldAlert, Power, Clock, AlertTriangle, CheckCircle, Loader2, History, X, Ban } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { useState } from "react";

interface KillSwitch {
  key: string;
  active: string;
  reason: string;
  activated_by: string;
  activated_at: string;
  auto_reset_at?: string;
}

interface AuditEntry {
  id: string;
  switch_key: string;
  action: string;
  performed_by: string;
  performed_at: string;
  reason: string;
}

const SWITCH_DEFINITIONS = [
  { key: "platform.all_outreach", label: "All Outreach", description: "Stops ALL email/SMS sends platform-wide", severity: "critical" },
  { key: "platform.all_llm_calls", label: "All LLM Inference", description: "Stops ALL AI model calls globally", severity: "critical" },
  { key: "platform.all_scraping", label: "All Scraping", description: "Stops ALL browser automation", severity: "high" },
  { key: "provider.ahrefs", label: "Ahrefs Provider", description: "Stops Ahrefs API integration", severity: "medium" },
  { key: "provider.dataforseo", label: "DataForSEO Provider", description: "Stops DataForSEO integration", severity: "medium" },
  { key: "provider.hunter", label: "Hunter.io Provider", description: "Stops contact discovery", severity: "medium" },
];

const SEVERITY_COLORS: Record<string, { dot: string; bg: string; border: string; text: string; label: string }> = {
  critical: { dot: "bg-red-500", bg: "bg-red-500/10", border: "border-red-500/20", text: "text-red-400", label: "CRITICAL" },
  high: { dot: "bg-amber-500", bg: "bg-amber-500/10", border: "border-amber-500/20", text: "text-amber-400", label: "HIGH" },
  medium: { dot: "bg-platform-500", bg: "bg-platform-500/10", border: "border-platform-500/20", text: "text-platform-400", label: "MEDIUM" },
};

export default function KillSwitchesPage() {
  const queryClient = useQueryClient();
  const [confirmKey, setConfirmKey] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [showAudit, setShowAudit] = useState(false);

  const { data: activeSwitch = [], isLoading } = useQuery<KillSwitch[]>({
    queryKey: ["kill-switches"],
    queryFn: () => fetchApi("/kill-switches"),
    refetchInterval: 5000,
  });

  const { data: auditLog = [] } = useQuery<AuditEntry[]>({
    queryKey: ["kill-switches-audit"],
    queryFn: () => fetchApi("/kill-switches/audit?limit=50"),
    refetchInterval: 15000,
  });

  const activeMutation = useMutation({
    mutationFn: ({ key, reason: r }: { key: string; reason: string }) =>
      fetchApi("/kill-switches/activate", {
        method: "POST",
        body: JSON.stringify({ switch_key: key, reason: r, activated_by: "console_admin" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kill-switches"] });
      queryClient.invalidateQueries({ queryKey: ["kill-switches-audit"] });
      setConfirmKey(null);
      setReason("");
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (key: string) =>
      fetchApi("/kill-switches/deactivate", {
        method: "POST",
        body: JSON.stringify({ switch_key: key, deactivated_by: "console_admin" }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["kill-switches"] });
      queryClient.invalidateQueries({ queryKey: ["kill-switches-audit"] });
    },
  });

  const isActive = (key: string) => activeSwitch.some((s) => s.key === key);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">KILL_SWITCHES</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Emergency Operations Control</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowAudit(!showAudit)}
            className="px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 transition-colors bg-surface-darker border-surface-border text-slate-400 hover:text-slate-300"
          >
            <History className="w-3.5 h-3.5" />
            AUDIT LOG
          </button>
          <div className={`px-3 py-1.5 rounded-md flex items-center gap-2 border ${
            activeSwitch.length > 0
              ? "bg-red-500/10 border-red-500/30"
              : "bg-emerald-500/10 border-emerald-500/30"
          }`}>
            <span className={`w-2 h-2 rounded-full ${activeSwitch.length > 0 ? "bg-red-500 animate-pulse" : "bg-emerald-500"}`}></span>
            <span className={`text-xs font-mono ${activeSwitch.length > 0 ? "text-red-400" : "text-emerald-400"}`}>
              {activeSwitch.length > 0 ? `${activeSwitch.length} ACTIVE` : "ALL_CLEAR"}
            </span>
          </div>
        </div>
      </div>

      {/* Warning Banner */}
      <div className="glass-panel p-4 border-amber-500/20 bg-amber-500/5 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm text-amber-300 font-medium">Kill switches are the fastest path to stopping a bad operation.</p>
          <p className="text-xs text-slate-400 mt-1">Activating a switch will immediately halt all matching operations across all tenants. Use with extreme caution.</p>
        </div>
      </div>

      {/* Switch Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {SWITCH_DEFINITIONS.map((sw, i) => {
          const active = isActive(sw.key);
          const severity = SEVERITY_COLORS[sw.severity] || SEVERITY_COLORS.medium;
          return (
            <motion.div
              key={sw.key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className={`glass-panel p-5 transition-all duration-300 ${
                active ? "border-red-500/40 bg-red-500/5 shadow-[0_0_20px_rgba(239,68,68,0.08)]" : ""
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <ShieldAlert className={`w-5 h-5 ${severity.dot.replace("bg-", "text-")}`} />
                    <h3 className="text-lg font-semibold text-slate-200 font-mono">{sw.label}</h3>
                    <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest rounded border ${severity.bg} ${severity.border} ${severity.text}`}>
                      {severity.label}
                    </span>
                  </div>
                  <p className="text-sm text-slate-400 mb-1">{sw.description}</p>
                  <p className="text-xs text-slate-600 font-mono">{sw.key}</p>
                </div>

                <div className="flex-shrink-0 ml-4">
                  {active ? (
                    <button
                      onClick={() => deactivateMutation.mutate(sw.key)}
                      disabled={deactivateMutation.isPending}
                      className="px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-md text-sm font-mono font-bold transition-colors flex items-center gap-2 disabled:opacity-50"
                    >
                      <CheckCircle className="w-4 h-4" />
                      RESTORE
                    </button>
                  ) : confirmKey === sw.key ? (
                    <div className="flex flex-col gap-2">
                      <input
                        type="text"
                        placeholder="Reason for activation..."
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        className="px-3 py-1.5 text-xs font-mono bg-surface-darker border border-surface-border rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500 w-48"
                        autoFocus
                      />
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => activeMutation.mutate({ key: sw.key, reason: reason || "Manual activation via console" })}
                          disabled={activeMutation.isPending || !reason.trim()}
                          className="flex-1 px-3 py-2 bg-red-600 hover:bg-red-500 text-white rounded-md text-xs font-mono font-bold transition-colors disabled:opacity-50"
                        >
                          CONFIRM
                        </button>
                        <button
                          onClick={() => { setConfirmKey(null); setReason(""); }}
                          className="px-3 py-2 bg-surface-darker text-slate-400 rounded-md text-xs font-mono transition-colors"
                        >
                          CANCEL
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmKey(sw.key)}
                      className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 rounded-md text-sm font-mono font-bold transition-colors flex items-center gap-2"
                    >
                      <Power className="w-4 h-4" />
                      ENGAGE
                    </button>
                  )}
                </div>
              </div>

              {active && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  className="mt-4 pt-4 border-t border-red-500/20"
                >
                  <div className="flex items-center gap-4 text-xs text-red-300 font-mono">
                    <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> Active since: {activeSwitch.find(s => s.key === sw.key)?.activated_at ? new Date(activeSwitch.find(s => s.key === sw.key)!.activated_at).toLocaleString() : "unknown"}</span>
                    <span>By: {activeSwitch.find(s => s.key === sw.key)?.activated_by || "console_admin"}</span>
                  </div>
                  {activeSwitch.find(s => s.key === sw.key)?.reason && (
                    <p className="text-xs text-slate-500 mt-2 font-mono">
                      Reason: {activeSwitch.find(s => s.key === sw.key)?.reason}
                    </p>
                  )}
                </motion.div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Audit Log Panel */}
      <AnimatePresence>
        {showAudit && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="glass-panel p-6">
              <h3 className="text-sm font-bold text-slate-200 mb-4 flex items-center gap-2 uppercase tracking-wider font-mono">
                <History className="w-4 h-4 text-platform-400" /> Audit Log
              </h3>
              <div className="space-y-2 max-h-64 overflow-y-auto custom-scrollbar">
                {auditLog.length === 0 ? (
                  <div className="text-sm text-slate-500 font-mono text-center py-4">No audit entries recorded</div>
                ) : (
                  auditLog.map((entry) => (
                    <div key={entry.id} className="flex items-center justify-between p-3 bg-surface-darker/50 rounded border border-surface-border/50 text-xs font-mono">
                      <div className="flex items-center gap-3">
                        <span className={`w-1.5 h-1.5 rounded-full ${entry.action === "activate" ? "bg-red-500" : "bg-emerald-500"}`}></span>
                        <span className="text-slate-400 uppercase text-[10px] font-bold">{entry.action}</span>
                        <span className="text-slate-500">{entry.switch_key}</span>
                        <span className="text-slate-600">by {entry.performed_by}</span>
                      </div>
                      <div className="flex items-center gap-3">
                        {entry.reason && <span className="text-slate-600 max-w-[200px] truncate">{entry.reason}</span>}
                        <span className="text-slate-600">{new Date(entry.performed_at).toLocaleString()}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
