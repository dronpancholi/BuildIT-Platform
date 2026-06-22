"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import {
  ArrowLeft,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  TrendingUp,
  Shield,
  Target,
  Users,
  BarChart3,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { useRouter, useParams } from "next/navigation";
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { formatDate, cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/error-boundary";
import { safeArr, safeStr, safeNum, safeSlice } from "@/lib/safe";

// ── Types ──────────────────────────────────────────────

interface PlanStep {
  id: string;
  name: string;
  description?: string;
  status: string;
  assignee?: string;
  dependencies?: string[];
  risk_score?: number;
  estimated_duration?: string;
  domain?: string;
}

interface Plan {
  id: string;
  tenant_id: string;
  // client_id is derived server-side from plan.goal_execution -> campaign.
  // It may be null when the plan was created without a campaign
  // (ad-hoc goal, missing metadata). Render defensively.
  client_id?: string | null;
  name: string;
  status: string;
  objectives?: Record<string, unknown>;
  steps?: PlanStep[];
  domain?: string;
  strategy?: string;
  risk_score?: number;
  confidence_score?: number;
  forecast?: {
    estimated_impact?: string;
    timeline_weeks?: number;
    resource_requirements?: string;
    success_probability?: number;
  };
  risk_assessment?: {
    overall_risk?: string;
    key_risks?: string[];
    mitigations?: string[];
  };
  created_at: string;
  updated_at: string;
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
    case "in_progress":
      return "default";
    case "pending_approval":
      return "warning";
    case "draft":
    case "pending":
      return "secondary";
    case "failed":
    case "rejected":
      return "destructive";
    default:
      return "outline";
  }
}

function statusLabel(status: string): string {
  return safeStr(status, "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function stepNodeColor(status: string): string {
  switch (status) {
    case "completed":
      return "#10b981";
    case "in_progress":
    case "executing":
      return "#f59e0b";
    case "failed":
      return "#ef4444";
    case "pending":
    case "draft":
    default:
      return "#64748b";
  }
}

function stepNodeBg(status: string): string {
  switch (status) {
    case "completed":
      return "bg-emerald-500/10 border-emerald-500/30";
    case "in_progress":
    case "executing":
      return "bg-amber-500/10 border-amber-500/30";
    case "failed":
      return "bg-red-500/10 border-red-500/30";
    default:
      return "bg-slate-500/10 border-slate-500/30";
  }
}

function stepNodeText(status: string): string {
  switch (status) {
    case "completed":
      return "text-emerald-400";
    case "in_progress":
    case "executing":
      return "text-amber-400";
    case "failed":
      return "text-red-400";
    default:
      return "text-slate-400";
  }
}

// ── Custom Step Node ───────────────────────────────────

function StepNode({ data }: { data: Record<string, unknown> }) {
  const name = data.name as string;
  const status = data.status as string;
  const assignee = data.assignee as string | undefined;
  const domain = data.domain as string | undefined;

  return (
    <div
      className={cn(
        "px-4 py-3 rounded-lg border min-w-[180px] max-w-[240px] shadow-lg",
        stepNodeBg(status)
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: stepNodeColor(status) }}
        />
        <span className="text-xs font-semibold text-slate-200 truncate">
          {safeStr(name)}
        </span>
      </div>
      <div className="flex items-center gap-2 mt-1">
        <span
          className={cn("text-[9px] font-mono uppercase", stepNodeText(status))}
        >
          {safeStr(status, "").replace(/_/g, " ")}
        </span>
        {domain && (
          <span className="text-[9px] font-mono text-slate-600">
            · {domain}
          </span>
        )}
      </div>
      {assignee && (
        <div className="flex items-center gap-1 mt-1.5 text-[9px] text-slate-500">
          <Users className="w-2.5 h-2.5" />
          <span className="truncate">{assignee}</span>
        </div>
      )}
    </div>
  );
}

const nodeTypes = { stepNode: StepNode };

// ── Page ───────────────────────────────────────────────

export default function PlanDetailPage() {
  return (
    <ErrorBoundary>
      <PlanDetailPageContent />
    </ErrorBoundary>
  );
}

function PlanDetailPageContent() {
  const router = useRouter();
  const params = useParams();
  const planId = params.id as string;
  const queryClient = useQueryClient();

  const [approvalComment, setApprovalComment] = useState("");

  // ── Query ──

  const { data: plan, isLoading, isError } = useQuery<Plan>({
    queryKey: ["plan", planId],
    queryFn: () => fetchApi(`/plans/${planId}?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 10000,
  });

  // ── Mutations ──

  const approveMutation = useMutation({
    mutationFn: () =>
      fetchApi(`/plans/${planId}/approve?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({ decision: "approved", comments: approvalComment }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plan", planId] });
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      setApprovalComment("");
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () =>
      fetchApi(`/plans/${planId}/approve?tenant_id=${MOCK_TENANT_ID}`, {
        method: "POST",
        body: JSON.stringify({ decision: "rejected", comments: approvalComment }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plan", planId] });
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      setApprovalComment("");
    },
  });

  // ── Build React Flow Graph ──

  const { flowNodes, flowEdges } = useMemo(() => {
    const safeSteps: PlanStep[] = safeArr<PlanStep>(plan?.steps);
    if (safeSteps.length === 0) {
      return { flowNodes: [], flowEdges: [] };
    }

    const nodes: Node[] = [];
    const edges: Edge[] = [];

    // Layout: group by level based on dependencies
    const stepMap = new Map(safeSteps.map((s) => [s.id, s]));
    const levels = new Map<string, number>();
    const visited = new Set<string>();

    function getLevel(stepId: string, depth = 0): number {
      if (levels.has(stepId)) return levels.get(stepId)!;
      if (visited.has(stepId)) return depth;
      visited.add(stepId);

      const step = stepMap.get(stepId);
      const stepDeps: string[] = safeArr<string>(step?.dependencies);
      if (stepDeps.length === 0) {
        levels.set(stepId, 0);
        return 0;
      }

      const maxDepLevel = Math.max(
        ...stepDeps.map((dep) => getLevel(dep, depth + 1))
      );
      const level = maxDepLevel + 1;
      levels.set(stepId, level);
      return level;
    }

    safeSteps.forEach((step) => getLevel(step.id));

    // Group steps by level
    const levelGroups = new Map<number, PlanStep[]>();
    safeSteps.forEach((step) => {
      const level = levels.get(step.id) ?? 0;
      if (!levelGroups.has(level)) levelGroups.set(level, []);
      levelGroups.get(level)!.push(step);
    });

    // Create nodes
    const sortedLevels = Array.from(levelGroups.keys()).sort((a, b) => a - b);
    sortedLevels.forEach((level) => {
      const stepsAtLevel = levelGroups.get(level)!;
      stepsAtLevel.forEach((step, idx) => {
        nodes.push({
          id: step.id,
          type: "stepNode",
          position: {
            x: level * 300 + 50,
            y: idx * 120 + 50,
          },
          data: {
            name: step.name,
            status: step.status,
            assignee: step.assignee,
            domain: step.domain,
          },
        });
      });
    });

    // Create edges
    safeSteps.forEach((step) => {
      const deps: string[] = safeArr<string>(step.dependencies);
      deps.forEach((depId) => {
        if (stepMap.has(depId)) {
          edges.push({
            id: `${depId}-${step.id}`,
            source: depId,
            target: step.id,
            animated: step.status === "in_progress",
            style: { stroke: "#64748b", strokeWidth: 2 },
          });
        }
      });
    });

    return { flowNodes: nodes, flowEdges: edges };
  }, [plan]);

  // ── Loading / Error States ──

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
      </div>
    );
  }

  if (isError || !plan) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => router.push("/dashboard/plans")}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Plans
        </button>
        <div className="glass-panel p-12 flex flex-col items-center justify-center text-center">
          <AlertTriangle className="w-12 h-12 text-slate-600 mb-3" />
          <h3 className="text-lg font-medium text-slate-300">
            Plan Not Found
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            The plan you&apos;re looking for doesn&apos;t exist or has been
            removed.
          </p>
          <Button
            onClick={() => router.push("/dashboard/plans")}
            className="mt-4"
          >
            View All Plans
          </Button>
        </div>
      </div>
    );
  }

  const steps: PlanStep[] = safeArr<PlanStep>(plan.steps);
  const completedSteps = steps.filter((s) => s.status === "completed").length;
  const totalSteps = steps.length;
  const progress = totalSteps > 0 ? Math.round((completedSteps / totalSteps) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* ── Back Button ── */}
      <button
        onClick={() => router.push("/dashboard/plans")}
        className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Plans
      </button>

      {/* ── Header ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between"
      >
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight">
            {plan.name || `Plan ${safeSlice(safeStr(plan.id), 0, 8) || "—"}`}
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <Badge variant={statusBadgeVariant(plan.status)}>
              {statusLabel(plan.status)}
            </Badge>
            {plan.domain && (
              <span className="text-xs font-mono text-slate-500">
                {plan.domain}
              </span>
            )}
            {plan.strategy && (
              <span className="text-xs font-mono text-slate-500 capitalize">
                {safeStr(plan.strategy)} strategy
              </span>
            )}
          </div>
        </div>

        {/* ── Risk & Confidence Scores ── */}
        <div className="flex items-center gap-4">
          {plan.risk_score != null && (
            <div className="text-right">
              <p className="text-[9px] font-mono text-slate-500 uppercase">
                Risk Score
              </p>
              <p
                className={cn(
                  "text-lg font-bold font-mono",
                  plan.risk_score <= 0.3
                    ? "text-emerald-400"
                    : plan.risk_score <= 0.6
                      ? "text-amber-400"
                      : "text-red-400"
                )}
              >
                {Math.round(safeNum(plan.risk_score) * 100)}%
              </p>
            </div>
          )}
          {plan.confidence_score != null && (
            <div className="text-right">
              <p className="text-[9px] font-mono text-slate-500 uppercase">
                Confidence
              </p>
              <p
                className={cn(
                  "text-lg font-bold font-mono",
                  plan.confidence_score >= 0.8
                    ? "text-emerald-400"
                    : plan.confidence_score >= 0.5
                      ? "text-amber-400"
                      : "text-red-400"
                )}
              >
                {Math.round(safeNum(plan.confidence_score) * 100)}%
              </p>
            </div>
          )}
        </div>
      </motion.div>

      {/* ── Progress Bar ── */}
      <div className="glass-panel p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-mono text-slate-400">
            Progress: {completedSteps}/{totalSteps} steps
          </span>
          <span className="text-xs font-mono text-platform-400 font-bold">
            {progress}%
          </span>
        </div>
        <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
            className="h-full bg-platform-500 rounded-full"
          />
        </div>
      </div>

      {/* ── Main Content: DAG + Side Panel ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* ── DAG Visualization ── */}
        <div className="xl:col-span-2 glass-panel overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between">
            <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider">
              Plan DAG — {totalSteps} Steps
            </h3>
            <div className="flex items-center gap-3 text-[9px] font-mono">
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Completed
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-amber-500" /> In Progress
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-red-500" /> Failed
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-slate-500" /> Pending
              </span>
            </div>
          </div>
          <div style={{ height: 600 }}>
            {flowNodes.length > 0 ? (
              <ReactFlow
                nodes={flowNodes}
                edges={flowEdges}
                nodeTypes={nodeTypes}
                fitView
                fitViewOptions={{ padding: 0.2 }}
                minZoom={0.3}
                maxZoom={2}
                defaultEdgeOptions={{
                  animated: false,
                  style: { strokeWidth: 2 },
                }}
              >
                <Controls className="!bg-surface-darker !border-surface-border !rounded-lg" />
                <Background
                  color="#334155"
                  gap={20}
                  size={1}
                />
                <MiniMap
                  nodeColor={(node) =>
                    stepNodeColor((node.data as Record<string, unknown>).status as string)
                  }
                  maskColor="rgba(0,0,0,0.6)"
                  className="!bg-surface-darker !border-surface-border !rounded-lg"
                />
              </ReactFlow>
            ) : (
              <div className="flex items-center justify-center h-full text-sm text-slate-500">
                No steps defined in this plan
              </div>
            )}
          </div>
        </div>

        {/* ── Side Panel ── */}
        <div className="space-y-4">
          {/* Plan Details */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Target className="w-4 h-4 text-platform-400" />
                Plan Details
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Created</span>
                <span className="text-slate-300 font-mono">
                  {formatDate(plan.created_at)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Updated</span>
                <span className="text-slate-300 font-mono">
                  {formatDate(plan.updated_at)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Client ID</span>
                <span className="text-slate-300 font-mono truncate max-w-[120px]">
                  {plan.client_id ? `${safeSlice(plan.client_id, 0, 8)}...` : "N/A"}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Forecast */}
          {plan.forecast && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-platform-400" />
                  Forecast
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {plan.forecast.estimated_impact && (
                  <div>
                    <p className="text-[9px] font-mono text-slate-500 uppercase mb-1">
                      Estimated Impact
                    </p>
                    <p className="text-xs text-slate-300">
                      {safeStr(plan.forecast.estimated_impact)}
                    </p>
                  </div>
                )}
                {plan.forecast.timeline_weeks != null && (
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Timeline</span>
                    <span className="text-slate-300 font-mono">
                      {plan.forecast.timeline_weeks} weeks
                    </span>
                  </div>
                )}
                {plan.forecast.resource_requirements && (
                  <div>
                    <p className="text-[9px] font-mono text-slate-500 uppercase mb-1">
                      Resources
                    </p>
                    <p className="text-xs text-slate-300">
                      {safeStr(plan.forecast.resource_requirements)}
                    </p>
                  </div>
                )}
                {plan.forecast.success_probability != null && (
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Success Prob.</span>
                    <span
                      className={cn(
                        "font-mono font-bold",
                        plan.forecast.success_probability >= 0.7
                          ? "text-emerald-400"
                          : "text-amber-400"
                      )}
                    >
                      {Math.round(safeNum(plan.forecast.success_probability) * 100)}%
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Risk Assessment */}
          {plan.risk_assessment && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Shield className="w-4 h-4 text-platform-400" />
                  Risk Assessment
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {plan.risk_assessment.overall_risk && (
                  <div>
                    <p className="text-[9px] font-mono text-slate-500 uppercase mb-1">
                      Overall Risk
                    </p>
                    <p className="text-xs text-slate-300 capitalize">
                      {safeStr(plan.risk_assessment.overall_risk)}
                    </p>
                  </div>
                )}
                {plan.risk_assessment.key_risks &&
                  safeArr<string>(plan.risk_assessment.key_risks).length > 0 && (
                    <div>
                      <p className="text-[9px] font-mono text-slate-500 uppercase mb-1">
                        Key Risks
                      </p>
                      <ul className="space-y-1">
                        {safeArr<string>(plan.risk_assessment.key_risks).map((risk, i) => (
                          <li
                            key={i}
                            className="text-xs text-slate-300 flex items-start gap-1.5"
                          >
                            <AlertTriangle className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                            {safeStr(risk)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                {plan.risk_assessment.mitigations &&
                  safeArr<string>(plan.risk_assessment.mitigations).length > 0 && (
                    <div>
                      <p className="text-[9px] font-mono text-slate-500 uppercase mb-1">
                        Mitigations
                      </p>
                      <ul className="space-y-1">
                        {safeArr<string>(plan.risk_assessment.mitigations).map((m, i) => (
                          <li
                            key={i}
                            className="text-xs text-slate-300 flex items-start gap-1.5"
                          >
                            <CheckCircle2 className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                            {safeStr(m)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
              </CardContent>
            </Card>
          )}

          {/* Action Buttons */}
          {(plan.status === "pending_approval" || plan.status === "draft") && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-platform-400" />
                  Actions
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className="text-[9px] font-mono text-slate-500 mb-1 block">
                    Comment (optional)
                  </label>
                  <textarea
                    value={approvalComment}
                    onChange={(e) => setApprovalComment(e.target.value)}
                    placeholder="Add a comment..."
                    rows={2}
                    className="w-full px-3 py-2 bg-surface-darker border border-surface-border rounded-lg text-xs text-slate-200 placeholder-slate-600 focus:outline-none focus:border-platform-500 resize-none"
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="destructive"
                    className="flex-1"
                    onClick={() => rejectMutation.mutate()}
                    disabled={rejectMutation.isPending}
                  >
                    {rejectMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <XCircle className="w-4 h-4 mr-1" />
                    )}
                    Reject
                  </Button>
                  <Button
                    className="flex-1"
                    onClick={() => approveMutation.mutate()}
                    disabled={approveMutation.isPending}
                  >
                    {approveMutation.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-4 h-4 mr-1" />
                    )}
                    Approve
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
