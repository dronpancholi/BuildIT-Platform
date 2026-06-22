"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Plus,
  Loader2,
  ArrowRight,
  Calendar,
  Target,
  TrendingUp,
  AlertTriangle,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

// ── Types ──────────────────────────────────────────────

interface Plan {
  id: string;
  tenant_id: string;
  // client_id is derived server-side and may be null. Marked optional+nullable
  // so the list page can't crash if the field is missing.
  client_id?: string | null;
  name: string;
  status: string;
  objectives?: Record<string, unknown>;
  steps?: Record<string, unknown>[];
  domain?: string;
  strategy?: string;
  risk_score?: number;
  confidence_score?: number;
  forecast?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

interface Goal {
  id: string;
  name: string;
  type: string;
  status: string;
}

// ── Helpers ────────────────────────────────────────────

function statusBadgeVariant(
  status: string
): "default" | "secondary" | "destructive" | "success" | "warning" | "outline" {
  switch (status) {
    case "approved":
    case "completed":
      return "success";
    case "executing":
      return "default";
    case "pending_approval":
      return "warning";
    case "draft":
      return "secondary";
    case "failed":
      return "destructive";
    default:
      return "outline";
  }
}

function statusLabel(status: string): string {
  return safeStr(status, "").replace(/_/g, " ").replace(/\b\w/g, (c) => safeUpper(c));
}

// ── Page ───────────────────────────────────────────────

export default function PlanningStudioPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [showGenerate, setShowGenerate] = useState(false);
  const [goalId, setGoalId] = useState("");
  const [domain, setDomain] = useState("");
  const [strategy, setStrategy] = useState("balanced");

  // ── Queries ──

  const { data: plans = [], isLoading } = useQuery<Plan[]>({
    queryKey: ["plans"],
    queryFn: () => fetchApi(`/plans?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  const { data: goals = [] } = useQuery<Goal[]>({
    queryKey: ["goals"],
    queryFn: () => fetchApi(`/goals?tenant_id=${MOCK_TENANT_ID}`),
  });

  // ── Mutations ──

  const generateMutation = useMutation({
    mutationFn: (payload: {
      goal_id: string;
      domain: string;
      strategy: string;
    }) =>
      fetchApi(`/plans/generate?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      setShowGenerate(false);
      setGoalId("");
      setDomain("");
      setStrategy("balanced");
    },
  });

  const handleGenerate = () => {
    if (!goalId) return;
    generateMutation.mutate({ goal_id: goalId, domain, strategy });
  };

  const pendingCount = plans.filter((p) => p.status === "pending_approval").length;

  return (
    <div className="space-y-6">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">
            Planning Studio
          </h1>
          <p className="text-slate-400 mt-1 text-sm">
            Generate, visualize, and manage strategic SEO plans.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {pendingCount > 0 && (
            <Badge variant="warning">
              {pendingCount} pending approval
            </Badge>
          )}
          <Button onClick={() => setShowGenerate(true)} className="flex items-center gap-2">
            <Plus className="w-4 h-4" /> Generate Plan
          </Button>
        </div>
      </div>

      {/* ── Plans List ── */}
      <div className="glass-panel overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
          </div>
        ) : plans.length === 0 ? (
          <div className="p-12 flex flex-col items-center justify-center text-center">
            <div className="w-16 h-16 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-4">
              <Target className="w-8 h-8 text-slate-600" />
            </div>
            <h3 className="text-lg font-medium text-slate-300">No Plans Yet</h3>
            <p className="text-sm text-slate-500 mt-1 max-w-md">
              Generate your first strategic plan to get started with automated
              SEO execution.
            </p>
            <Button
              onClick={() => setShowGenerate(true)}
              className="mt-4"
            >
              <Plus className="w-4 h-4 mr-2" /> Generate First Plan
            </Button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-[9px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
                <tr>
                  <th className="px-6 py-3 font-mono font-medium">Name</th>
                  <th className="px-6 py-3 font-mono font-medium">Status</th>
                  <th className="px-6 py-3 font-mono font-medium text-center">
                    Confidence
                  </th>
                  <th className="px-6 py-3 font-mono font-medium text-center">
                    Risk Score
                  </th>
                  <th className="px-6 py-3 font-mono font-medium">Steps</th>
                  <th className="px-6 py-3 font-mono font-medium">Created</th>
                  <th className="px-6 py-3 font-mono font-medium text-right">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {plans.map((plan, i) => (
                  <motion.tr
                    key={plan.id}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="hover:bg-surface-border/30 transition-colors group"
                  >
                    <td className="px-6 py-4">
                      <button
                        onClick={() =>
                          router.push(`/dashboard/plans/${plan.id}`)
                        }
                        className="font-medium text-slate-200 text-sm hover:text-platform-400 transition-colors text-left"
                      >
                        {plan.name}
                      </button>
                      {plan.domain && (
                        <div className="text-[10px] text-slate-600 font-mono mt-0.5">
                          {plan.domain}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={statusBadgeVariant(plan.status)}>
                        {statusLabel(plan.status)}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-center">
                      {plan.confidence_score != null ? (
                        <span
                          className={`text-xs font-mono font-bold ${
                            plan.confidence_score >= 0.8
                              ? "text-emerald-400"
                              : plan.confidence_score >= 0.5
                                ? "text-amber-400"
                                : "text-red-400"
                          }`}
                        >
                          {Math.round(plan.confidence_score * 100)}%
                        </span>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-center">
                      {plan.risk_score != null ? (
                        <span
                          className={`text-xs font-mono font-bold ${
                            plan.risk_score <= 0.3
                              ? "text-emerald-400"
                              : plan.risk_score <= 0.6
                                ? "text-amber-400"
                                : "text-red-400"
                          }`}
                        >
                          {Math.round(plan.risk_score * 100)}%
                        </span>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-mono text-slate-400">
                        {plan.steps?.length ?? 0} steps
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5 text-[10px] font-mono text-slate-500">
                        <Calendar className="w-3 h-3" />
                        {formatDate(plan.created_at)}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        onClick={() =>
                          router.push(`/dashboard/plans/${plan.id}`)
                        }
                        className="px-3 py-1.5 bg-surface-darker border border-surface-border rounded text-[10px] font-mono text-slate-400 hover:text-slate-200 hover:border-surface-border/80 transition-colors flex items-center gap-1.5 ml-auto"
                      >
                        View <ArrowRight className="w-3 h-3" />
                      </button>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Generate Plan Dialog ── */}
      <Dialog open={showGenerate} onOpenChange={setShowGenerate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Generate Plan</DialogTitle>
            <DialogDescription>
              Create a new strategic plan powered by AI analysis.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">
                Goal
              </label>
              <select
                value={goalId}
                onChange={(e) => setGoalId(e.target.value)}
                className="w-full px-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-sm text-slate-200 focus:outline-none focus:border-platform-500"
              >
                <option value="">Select a goal...</option>
                {goals.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.name} ({g.type})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">
                Domain / Focus Area
              </label>
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                placeholder="e.g., Technical SEO, Content, Backlinks"
                className="w-full px-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500"
              />
            </div>

            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">
                Strategy
              </label>
              <div className="grid grid-cols-3 gap-2">
                {(["balanced", "aggressive", "conservative"] as const).map(
                  (s) => (
                    <button
                      key={s}
                      onClick={() => setStrategy(s)}
                      className={`px-3 py-2 rounded-lg text-xs font-mono border transition-all ${
                        strategy === s
                          ? "bg-platform-500/20 text-platform-400 border-platform-500/30"
                          : "bg-surface-darker text-slate-400 border-surface-border hover:text-slate-200"
                      }`}
                    >
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </button>
                  )
                )}
              </div>
              <p className="text-[10px] text-slate-600 mt-2">
                {strategy === "balanced" &&
                  "Balanced approach optimizing for steady growth with moderate risk."}
                {strategy === "aggressive" &&
                  "High-impact actions targeting rapid gains with higher resource commitment."}
                {strategy === "conservative" &&
                  "Low-risk, incremental improvements focused on long-term sustainability."}
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowGenerate(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleGenerate}
              disabled={!goalId || generateMutation.isPending}
            >
              {generateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin mr-2" />
                  Generating...
                </>
              ) : (
                <>
                  <TrendingUp className="w-4 h-4 mr-2" />
                  Generate Plan
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
