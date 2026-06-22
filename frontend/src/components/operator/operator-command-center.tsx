"use client";

/**
 * Operator Command Center — single page where the operator answers
 * "Is the platform healthy?" and "What needs my attention?" in 30 seconds.
 *
 * Layout:
 *   Top:    Global system health (8 signals)
 *   Row 1:  Action Center (urgent items) | Quick Stats
 *   Row 2:  Campaign Command Center (compact)
 *   Row 3:  Approvals | Executions (side-by-side)
 *   Row 4:  Provider Command Center (compact)
 */

import { SystemHealthPanel } from "./system-health-panel";
import { ActionCenter } from "./action-center";
import { CampaignCommandCenter } from "./campaign-command-center";
import { ApprovalCommandCenter } from "./approval-command-center";
import { ExecutionVisibility } from "./execution-visibility";
import { ProviderCommandCenter } from "./provider-command-center";
import { useState } from "react";
import { ChevronDown, ChevronUp, Maximize2, Minimize2 } from "lucide-react";

export function OperatorCommandCenter() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Operator Command Center</h1>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            Health · Action · Campaigns · Approvals · Executions · Providers
          </p>
        </div>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-[10px] font-mono uppercase px-2 py-1 rounded border border-surface-border text-slate-400 hover:text-slate-200 hover:border-slate-500 flex items-center gap-1.5"
        >
          {expanded ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
          {expanded ? "Compact view" : "Expanded view"}
        </button>
      </div>

      <SystemHealthPanel />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <ActionCenter limit={expanded ? 20 : 8} />
        </div>
        <div className="rounded-xl border border-surface-border bg-surface-card/80 backdrop-blur-md p-5 shadow-xl shadow-black/20">
          <h2 className="text-sm font-bold text-slate-100 mb-3 tracking-tight">Quick Answers</h2>
          <ul className="text-xs text-slate-300 space-y-1.5 font-mono">
            <li>· Is the system healthy? → <span className="text-slate-400">see top panel</span></li>
            <li>· What needs attention? → <span className="text-slate-400">action center left</span></li>
            <li>· Are campaigns running? → <span className="text-slate-400">campaigns below</span></li>
            <li>· Pending approvals? → <span className="text-slate-400">approvals below</span></li>
            <li>· Anything stuck? → <span className="text-slate-400">executions below</span></li>
            <li>· Are providers up? → <span className="text-slate-400">providers bottom</span></li>
          </ul>
        </div>
      </div>

      <CampaignCommandCenter />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <ApprovalCommandCenter />
        <ExecutionVisibility />
      </div>

      <ProviderCommandCenter />
    </div>
  );
}
