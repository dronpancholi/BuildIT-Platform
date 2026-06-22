"use client";

/**
 * Operator-language health signal vocabulary.
 * Used by all command center surfaces.
 */

export type HealthLevel = "healthy" | "warning" | "critical" | "unknown";

export interface HealthSignal {
  level: HealthLevel;
  label: string;
  detail?: string;
}

export function deriveHealth(
  endpointState: "ok" | "error" | "unknown",
  okRule?: boolean,
): HealthLevel {
  if (endpointState === "error") return "critical";
  if (endpointState === "unknown") return "unknown";
  if (okRule === false) return "warning";
  return "healthy";
}

export function healthColor(level: HealthLevel): {
  dot: string;
  bg: string;
  text: string;
  border: string;
  ring: string;
} {
  switch (level) {
    case "healthy":
      return {
        dot: "bg-emerald-500",
        bg: "bg-emerald-500/10",
        text: "text-emerald-400",
        border: "border-emerald-500/30",
        ring: "ring-emerald-500/20",
      };
    case "warning":
      return {
        dot: "bg-amber-500",
        bg: "bg-amber-500/10",
        text: "text-amber-400",
        border: "border-amber-500/30",
        ring: "ring-amber-500/20",
      };
    case "critical":
      return {
        dot: "bg-red-500",
        bg: "bg-red-500/10",
        text: "text-red-400",
        border: "border-red-500/30",
        ring: "ring-red-500/20",
      };
    default:
      return {
        dot: "bg-slate-500",
        bg: "bg-slate-500/10",
        text: "text-slate-400",
        border: "border-slate-500/30",
        ring: "ring-slate-500/20",
      };
  }
}

export function healthLabel(level: HealthLevel): string {
  switch (level) {
    case "healthy": return "HEALTHY";
    case "warning": return "WARNING";
    case "critical": return "CRITICAL";
    default: return "UNKNOWN";
  }
}
