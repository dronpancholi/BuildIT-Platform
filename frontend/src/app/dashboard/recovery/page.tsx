"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  RotateCcw,
  AlertTriangle,
  CheckCircle,
  Loader2,
  X,
  RefreshCw,
  ShieldAlert,
  KeyRound,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { recoveryApi, FailedItem } from "@/lib/api";

type Tab = "submissions" | "credentials";

export default function RecoveryPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<Tab>("submissions");
  const [showRetryAllConfirm, setShowRetryAllConfirm] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["recovery-failed"],
    queryFn: recoveryApi.listFailedItems,
    refetchInterval: 10_000,
  });

  const retryItemMutation = useMutation({
    mutationFn: ({ type, id }: { type: string; id: string }) =>
      recoveryApi.retryItem(type, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recovery-failed"] });
    },
  });

  const retryAllMutation = useMutation({
    mutationFn: recoveryApi.retryAllFailed,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recovery-failed"] });
      setShowRetryAllConfirm(false);
    },
  });

  const submissions = data?.submissions ?? [];
  const credentials = data?.credentials ?? [];
  const total = data?.total ?? 0;

  const renderTable = (items: FailedItem[], showProject: boolean) => (
    <div className="overflow-hidden rounded-xl border border-surface-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-surface-darker border-b border-surface-border">
            <th className="text-left px-4 py-3 font-mono text-xs text-slate-400 uppercase tracking-wider">
              Name
            </th>
            {showProject && (
              <th className="text-left px-4 py-3 font-mono text-xs text-slate-400 uppercase tracking-wider">
                Project
              </th>
            )}
            <th className="text-left px-4 py-3 font-mono text-xs text-slate-400 uppercase tracking-wider">
              Status
            </th>
            <th className="text-left px-4 py-3 font-mono text-xs text-slate-400 uppercase tracking-wider">
              Error
            </th>
            <th className="text-left px-4 py-3 font-mono text-xs text-slate-400 uppercase tracking-wider">
              Last Updated
            </th>
            <th className="text-right px-4 py-3 font-mono text-xs text-slate-400 uppercase tracking-wider">
              Action
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-border/50">
          {items.map((item) => (
            <motion.tr
              key={item.id}
              layout
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="bg-surface-card/50 hover:bg-surface-card transition-colors"
            >
              <td className="px-4 py-3 text-slate-200 font-medium">
                {item.name}
              </td>
              {showProject && (
                <td className="px-4 py-3 text-slate-400">
                  {item.project || "-"}
                </td>
              )}
              <td className="px-4 py-3">
                <span
                  className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                    item.status === "locked"
                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      : "bg-red-500/10 text-red-400 border border-red-500/20"
                  }`}
                >
                  {item.status}
                </span>
              </td>
              <td className="px-4 py-3 text-xs text-slate-500 max-w-[300px] truncate">
                {item.error || "No error recorded"}
              </td>
              <td className="px-4 py-3 text-xs text-slate-500 font-mono">
                {item.updated_at
                  ? new Date(item.updated_at).toLocaleString()
                  : "-"}
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() =>
                    retryItemMutation.mutate({
                      type: item.type === "credential" ? "credential" : "submission",
                      id: item.id,
                    })
                  }
                  disabled={retryItemMutation.isPending}
                  className="px-3 py-1.5 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded text-xs font-mono font-bold transition-colors flex items-center gap-1.5 ml-auto disabled:opacity-50"
                >
                  {retryItemMutation.isPending ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <RotateCcw className="w-3 h-3" />
                  )}
                  RETRY
                </button>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">
            Failure Recovery
          </h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">
            Retry failed submissions and locked credentials
          </p>
        </div>
        <div className="flex items-center gap-3">
          {total > 0 && (
            <button
              onClick={() => setShowRetryAllConfirm(true)}
              className="px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/20 rounded-lg text-sm font-mono font-bold transition-colors flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              RETRY ALL ({total})
            </button>
          )}
          <div
            className={`px-3 py-1.5 rounded-md flex items-center gap-2 border ${
              total > 0
                ? "bg-red-500/10 border-red-500/30"
                : "bg-emerald-500/10 border-emerald-500/30"
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                total > 0 ? "bg-red-500 animate-pulse" : "bg-emerald-500"
              }`}
            />
            <span
              className={`text-xs font-mono ${
                total > 0 ? "text-red-400" : "text-emerald-400"
              }`}
            >
              {total > 0 ? `${total} FAILED` : "ALL_CLEAR"}
            </span>
          </div>
        </div>
      </div>

      {/* Info Banner */}
      {total > 0 && (
        <div className="glass-panel p-4 border-amber-500/20 bg-amber-500/5 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-amber-300 font-medium">
              {total} item{total !== 1 ? "s" : ""} require attention.
            </p>
            <p className="text-xs text-slate-400 mt-1">
              Retry individual items or use &ldquo;Retry All&rdquo; to reset them to
              pending state for reprocessing.
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-surface-darker rounded-lg border border-surface-border w-fit">
        <button
          onClick={() => setActiveTab("submissions")}
          className={`px-4 py-2 rounded-md text-xs font-mono font-bold uppercase tracking-wider transition-colors flex items-center gap-2 ${
            activeTab === "submissions"
              ? "bg-surface-card text-slate-200 shadow"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <ShieldAlert className="w-3.5 h-3.5" />
          Failed Submissions
          <span className="px-1.5 py-0.5 rounded bg-red-500/15 text-red-400 text-[10px]">
            {submissions.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab("credentials")}
          className={`px-4 py-2 rounded-md text-xs font-mono font-bold uppercase tracking-wider transition-colors flex items-center gap-2 ${
            activeTab === "credentials"
              ? "bg-surface-card text-slate-200 shadow"
              : "text-slate-500 hover:text-slate-300"
          }`}
        >
          <KeyRound className="w-3.5 h-3.5" />
          Locked Credentials
          <span className="px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-400 text-[10px]">
            {credentials.length}
          </span>
        </button>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="w-6 h-6 text-platform-400 animate-spin" />
          <span className="ml-3 text-slate-400 font-mono text-sm">
            Loading failed items...
          </span>
        </div>
      ) : error ? (
        <div className="glass-panel p-6 border-red-500/20 bg-red-500/5 text-center">
          <X className="w-8 h-8 text-red-400 mx-auto mb-3" />
          <p className="text-sm text-red-300 font-medium">
            Failed to load recovery data
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {(error as Error).message || "Unknown error"}
          </p>
        </div>
      ) : (
        <AnimatePresence mode="wait">
          {activeTab === "submissions" ? (
            <motion.div
              key="submissions"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              {submissions.length === 0 ? (
                <div className="glass-panel p-12 text-center">
                  <CheckCircle className="w-12 h-12 text-emerald-400/30 mx-auto mb-3" />
                  <p className="text-sm text-slate-400">
                    No failed submissions
                  </p>
                  <p className="text-xs text-slate-600 mt-1">
                    All citation submissions are healthy.
                  </p>
                </div>
              ) : (
                renderTable(submissions, true)
              )}
            </motion.div>
          ) : (
            <motion.div
              key="credentials"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              {credentials.length === 0 ? (
                <div className="glass-panel p-12 text-center">
                  <CheckCircle className="w-12 h-12 text-emerald-400/30 mx-auto mb-3" />
                  <p className="text-sm text-slate-400">
                    No locked credentials
                  </p>
                  <p className="text-xs text-slate-600 mt-1">
                    All directory credentials are active.
                  </p>
                </div>
              ) : (
                renderTable(credentials, false)
              )}
            </motion.div>
          )}
        </AnimatePresence>
      )}

      {/* Retry All Confirmation Modal */}
      <AnimatePresence>
        {showRetryAllConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={() => setShowRetryAllConfirm(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="glass-panel p-6 max-w-md w-full mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <RefreshCw className="w-5 h-5 text-emerald-400" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-slate-200">
                    Retry All Failed Items?
                  </h3>
                  <p className="text-xs text-slate-500">
                    This will reset all failed items to pending.
                  </p>
                </div>
              </div>
              <p className="text-sm text-slate-400 mb-6">
                This will reset{" "}
                <span className="text-slate-200 font-mono">{total}</span>{" "}
                failed item{total !== 1 ? "s" : ""} (
                <span className="text-red-400">{submissions.length} submissions</span>,{" "}
                <span className="text-amber-400">{credentials.length} credentials</span>)
                to pending/active state for reprocessing.
              </p>
              <div className="flex gap-3 justify-end">
                <button
                  onClick={() => setShowRetryAllConfirm(false)}
                  className="px-4 py-2 bg-surface-darker text-slate-400 rounded-lg text-sm font-mono transition-colors"
                >
                  CANCEL
                </button>
                <button
                  onClick={() => retryAllMutation.mutate()}
                  disabled={retryAllMutation.isPending}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-mono font-bold transition-colors flex items-center gap-2 disabled:opacity-50"
                >
                  {retryAllMutation.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  CONFIRM RETRY ALL
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
