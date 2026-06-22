"use client";

import { HealthLevel, healthColor, healthLabel } from "./health";
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from "lucide-react";

interface HealthPillProps {
  level: HealthLevel;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  detail?: string;
}

export function HealthPill({ level, size = "md", showLabel = true, detail }: HealthPillProps) {
  const c = healthColor(level);
  const sizes = {
    sm: "text-[10px] px-1.5 py-0.5 gap-1",
    md: "text-xs px-2.5 py-1 gap-1.5",
    lg: "text-sm px-3 py-1.5 gap-2",
  };
  const dotSizes = {
    sm: "w-1.5 h-1.5",
    md: "w-2 h-2",
    lg: "w-2.5 h-2.5",
  };
  const Icon =
    level === "healthy" ? CheckCircle2 :
    level === "warning" ? AlertTriangle :
    level === "critical" ? XCircle :
    HelpCircle;
  const iconSize = size === "sm" ? "w-3 h-3" : size === "lg" ? "w-4 h-4" : "w-3.5 h-3.5";

  return (
    <span
      className={`inline-flex items-center rounded-md border font-bold font-mono uppercase tracking-wider ${c.bg} ${c.text} ${c.border} ${sizes[size]}`}
      title={detail}
    >
      <span className={`rounded-full ${c.dot} ${dotSizes[size]}`} />
      {showLabel && <span>{healthLabel(level)}</span>}
    </span>
  );
}

interface HealthRowProps {
  name: string;
  level: HealthLevel;
  detail?: string;
  children?: React.ReactNode;
}

export function HealthRow({ name, level, detail, children }: HealthRowProps) {
  const c = healthColor(level);
  return (
    <div className={`flex items-center justify-between gap-4 py-2.5 px-3 rounded-md border ${c.border} ${c.bg} transition-colors`}>
      <div className="flex items-center gap-3 min-w-0 flex-1">
        <span className={`rounded-full ${c.dot} w-2.5 h-2.5 flex-shrink-0`} />
        <span className="text-sm font-medium text-slate-200">{name}</span>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        {detail && <span className={`text-xs ${c.text} font-mono hidden sm:inline`}>{detail}</span>}
        <HealthPill level={level} size="sm" />
        {children}
      </div>
    </div>
  );
}
