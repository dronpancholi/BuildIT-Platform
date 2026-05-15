"use client";

import { motion } from "framer-motion";
import {
  Building2, Users, GitBranch, TrendingUp, Clock, Loader2,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";

interface OrgWorkflowIntelligence {
  total_workflows: number;
  active_workflows: number;
  workflow_types: Record<string, number>;
  efficiency_score: number;
  failure_rate: number;
}

interface ApprovalBottleneckAnalysis {
  avg_approval_time_hours: number;
  pending_approvals: number;
  bottleneck_stages: { stage: string; avg_time_hours: number; bottleneck_risk: string }[];
}

interface OperationalHierarchy {
  hierarchy_levels: { level: string; teams: number; span: number }[];
  communication_paths: number;
  complexity_score: number;
}

const slideUp = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4 },
};

export default function OrganizationalIntelligencePage() {
  const { data: workflows, isLoading: loadingWorkflows } = useQuery<OrgWorkflowIntelligence>({
    queryKey: ["org-workflows"],
    queryFn: () => fetchApi("/organizational-intelligence/workflow-intelligence?org_id=org-main"),
  });

  const { data: bottlenecks, isLoading: loadingBottlenecks } = useQuery<ApprovalBottleneckAnalysis>({
    queryKey: ["approval-bottlenecks"],
    queryFn: () => fetchApi("/organizational-intelligence/approval-bottlenecks?org_id=org-main"),
  });

  const { data: hierarchy, isLoading: loadingHierarchy } = useQuery<OperationalHierarchy>({
    queryKey: ["operational-hierarchy"],
    queryFn: () => fetchApi("/organizational-intelligence/operational-hierarchy?org_id=org-main"),
  });

  if (loadingWorkflows || loadingBottlenecks || loadingHierarchy) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-platform-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <motion.div {...slideUp}>
        <h1 className="text-3xl font-bold text-slate-100">Organizational Intelligence</h1>
        <p className="text-slate-400 mt-1">Org-level workflow intelligence, coordination analytics, and hierarchy mapping</p>
      </motion.div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="w-5 h-5 text-platform-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Workflow Intelligence</h2>
          </div>
          {workflows && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-4xl font-bold text-slate-100">{workflows.total_workflows}</span>
                <span className="text-sm text-slate-400">total workflows</span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="text-slate-400">Active: <span className="text-green-400">{workflows.active_workflows}</span></div>
                <div className="text-slate-400">Efficiency: <span className="text-slate-200">{(workflows.efficiency_score * 100).toFixed(0)}%</span></div>
                <div className="text-slate-400">Failure rate: <span className="text-red-400">{(workflows.failure_rate * 100).toFixed(1)}%</span></div>
              </div>
              <div>
                <div className="text-xs text-slate-500 mb-1">By type:</div>
                {Object.entries(workflows.workflow_types).map(([key, val]) => (
                  <div key={key} className="flex items-center justify-between text-xs">
                    <span className="text-slate-400 capitalize">{key}</span>
                    <span className="text-slate-300">{val}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Approval Bottlenecks</h2>
          </div>
          {bottlenecks && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-amber-400">{bottlenecks.avg_approval_time_hours.toFixed(0)}h</span>
                <span className="text-sm text-slate-400">avg approval time</span>
              </div>
              <div className="text-sm text-slate-500">{bottlenecks.pending_approvals} pending</div>
              {bottlenecks.bottleneck_stages.map((s, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 capitalize">{s.stage}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-300">{s.avg_time_hours.toFixed(0)}h</span>
                    <span className={`px-1.5 py-0.5 rounded text-xs font-medium border ${
                      s.bottleneck_risk === "high" ? "bg-red-500/10 text-red-400 border-red-500/20" :
                      s.bottleneck_risk === "medium" ? "bg-amber-500/10 text-amber-400 border-amber-500/20" :
                      "bg-green-500/10 text-green-400 border-green-500/20"
                    }`}>{s.bottleneck_risk}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </motion.div>

        <motion.div {...slideUp} className="bg-surface-card border border-surface-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-5 h-5 text-purple-400" />
            <h2 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Operational Hierarchy</h2>
          </div>
          {hierarchy && (
            <div className="space-y-3">
              <div className="flex items-end gap-3">
                <span className="text-3xl font-bold text-purple-400">{hierarchy.communication_paths}</span>
                <span className="text-sm text-slate-400">comm paths</span>
              </div>
              <div className="text-sm text-slate-500">Complexity: {(hierarchy.complexity_score * 100).toFixed(0)}%</div>
              {hierarchy.hierarchy_levels.map((l, i) => (
                <div key={i} className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 capitalize">{l.level}</span>
                  <span className="text-slate-300">{l.teams} teams · span {l.span}</span>
                </div>
              ))}
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}
