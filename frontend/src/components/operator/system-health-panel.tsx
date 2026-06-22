"use client";

/**
 * Global System Health Panel
 * Phase 1.2.1
 *
 * Aggregates health from /health, /provider-health, /approvals, /executions, /plans, /reports.
 * Operator-language status (Healthy / Warning / Critical) — never raw errors.
 */

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  Activity, Database, Server, ListChecks, Inbox, Cpu,
  RefreshCw, AlertOctagon, CheckCircle2, Clock, XCircle,
} from "lucide-react";
import { fetchApi, ApiError } from "@/lib/api";
import { HealthRow, HealthPill } from "./health-pill";
import { HealthLevel } from "./health";

interface SystemHealth {
  status: string;
  components: { name: string; status: string; latency_ms?: number; message?: string | null }[];
}

interface ProviderHealth {
  providers: Record<string, {
    provider: string;
    healthy: boolean;
    not_configured: boolean;
    uptime_pct: number;
    total_calls_24h: number;
    success_count_24h: number;
    circuit_breaker_state: string;
  }>;
  healthy_providers: number;
  total_providers: number;
  not_configured_providers?: number;
  configured_providers?: number;
  overall_uptime_pct: number;
}

interface ApprovalsList {
  data: any[];
}

interface ExecutionsList {
  data: any[];
}

interface PlansList {
  data: any[];
}

interface ReportsList {
  data: any[];
}

type ProbeState = "ok" | "error" | "unknown";

interface HealthProbe {
  state: ProbeState;
  message: string;
  latency_ms?: number;
}

async function probe(path: string): Promise<HealthProbe> {
  try {
    const t0 = performance.now();
    const data = await fetchApi<any>(path);
    const latency = Math.round(performance.now() - t0);
    return { state: "ok", message: "available", latency_ms: latency };
  } catch (e) {
    if (e instanceof ApiError) {
      const msg = e.status === 500
        ? "endpoint unavailable"
        : e.status === 404
        ? "not available"
        : `error ${e.status}`;
      return { state: "error", message: msg };
    }
    return { state: "error", message: "cannot reach" };
  }
}

function levelFromProbe(p: HealthProbe, okLogic?: (data: any) => HealthLevel): HealthLevel {
  if (p.state === "error") return "critical";
  return "healthy";
}

export function SystemHealthPanel() {
  const [tick, setTick] = useState(0);
  const [lastChecked, setLastChecked] = useState<Date>(new Date());

  // Auto-refresh every 10s
  useEffect(() => {
    const t = setInterval(() => setTick((n) => n + 1), 10000);
    return () => clearInterval(t);
  }, []);

  // System health (API + DB + Redis + Kafka + Temporal + Qdrant)
  const sysQ = useQuery<SystemHealth>({
    queryKey: ["sys-health", tick],
    queryFn: () => fetchApi("/health"),
    refetchInterval: 10000,
  });

  // Provider health
  const provQ = useQuery<ProviderHealth>({
    queryKey: ["provider-health", tick],
    queryFn: () => fetchApi("/provider-health"),
    refetchInterval: 10000,
  });

  // Approvals
  const apprQ = useQuery<{ data: ApprovalsList; probe: HealthProbe }>({
    queryKey: ["health-approvals", tick],
    queryFn: async () => {
      const probeRes = await probe("/approvals?limit=1");
      let data: ApprovalsList = { data: [] };
      if (probeRes.state === "ok") {
        try { data = await fetchApi<ApprovalsList>("/approvals?limit=1"); } catch {}
      }
      return { data, probe: probeRes };
    },
    refetchInterval: 10000,
  });

  // Executions
  const execQ = useQuery<{ data: ExecutionsList; probe: HealthProbe }>({
    queryKey: ["health-executions", tick],
    queryFn: async () => {
      const probeRes = await probe("/executions?limit=1");
      let data: ExecutionsList = { data: [] };
      if (probeRes.state === "ok") {
        try { data = await fetchApi<ExecutionsList>("/executions?limit=1"); } catch {}
      }
      return { data, probe: probeRes };
    },
    refetchInterval: 10000,
  });

  // Plans
  const plansQ = useQuery<{ data: PlansList; probe: HealthProbe }>({
    queryKey: ["health-plans", tick],
    queryFn: async () => {
      const probeRes = await probe("/plans?limit=1");
      let data: PlansList = { data: [] };
      if (probeRes.state === "ok") {
        try { data = await fetchApi<PlansList>("/plans?limit=1"); } catch {}
      }
      return { data, probe: probeRes };
    },
    refetchInterval: 10000,
  });

  // Reports
  const repQ = useQuery<{ data: ReportsList; probe: HealthProbe }>({
    queryKey: ["health-reports", tick],
    queryFn: async () => {
      const probeRes = await probe("/reports?limit=1");
      let data: ReportsList = { data: [] };
      if (probeRes.state === "ok") {
        try { data = await fetchApi<ReportsList>("/reports?limit=1"); } catch {}
      }
      return { data, probe: probeRes };
    },
    refetchInterval: 10000,
  });

  // Derive signals
  const sysStatus = sysQ.data?.status;
  const sysLevel: HealthLevel =
    sysQ.isError ? "critical" :
    sysStatus === "healthy" ? "healthy" :
    sysStatus === "degraded" ? "warning" :
    "unknown";

  const dbComp = sysQ.data?.components?.find((c) => c.name === "postgresql");
  const dbLevel: HealthLevel =
    dbComp?.status === "healthy" ? "healthy" :
    dbComp?.status === "degraded" ? "warning" :
    dbComp?.status === "unhealthy" ? "critical" :
    sysQ.isError ? "critical" : "unknown";

  const ph = provQ.data;
  const phConfigured = ph?.configured_providers ?? ph?.providers
    ? Object.values(ph.providers).filter((p) => !p.not_configured).length : 0;
  const phTotal = ph?.total_providers ?? Object.keys(ph?.providers ?? {}).length;
  const phLevel: HealthLevel = provQ.isError ? "critical"
    : ph && ph.healthy_providers > 0 ? "healthy"
    : ph && phTotal > 0 && phConfigured === 0 ? "warning"
    : "healthy";

  const aprLevel: HealthLevel = apprQ.data?.probe.state === "error" ? "critical"
    : (apprQ.data?.data.data?.length ?? 0) > 0 ? "warning" : "healthy";

  const execLevel: HealthLevel = execQ.data?.probe.state === "error" ? "critical"
    : (execQ.data?.data.data?.length ?? 0) > 0 ? "warning" : "healthy";

  const plansLevel: HealthLevel = plansQ.data?.probe.state === "error" ? "critical" : "healthy";
  const repLevel: HealthLevel = repQ.data?.probe.state === "error" ? "critical" : "healthy";

  const refresh = () => {
    setTick((n) => n + 1);
    setLastChecked(new Date());
    sysQ.refetch();
    provQ.refetch();
    apprQ.refetch();
    execQ.refetch();
    plansQ.refetch();
    repQ.refetch();
  };

  // Age
  useEffect(() => {
    const t = setInterval(() => setLastChecked(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const isLoading = sysQ.isLoading || provQ.isLoading;

  return (
    <div className="rounded-xl border border-surface-border bg-surface-card/80 backdrop-blur-md p-5 shadow-xl shadow-black/20">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-tight">System Status</h2>
          <p className="text-xs text-slate-500 font-mono mt-0.5">Live health across all platform components</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">
            Updated <ClockAgo date={lastChecked} />
          </span>
          <button
            onClick={refresh}
            className="p-1.5 rounded-md border border-surface-border text-slate-400 hover:text-slate-200 hover:border-slate-500 transition-colors"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div className="space-y-2">
        <HealthRow
          name="API"
          level={sysLevel}
          detail={sysQ.data ? `${sysQ.data.status}` : "checking…"}
        />
        <HealthRow
          name="Database"
          level={dbLevel}
          detail={dbComp ? `${dbComp.latency_ms ?? 0}ms` : "checking…"}
        />
        <HealthRow
          name="Providers"
          level={phLevel}
          detail={ph ? `${phConfigured}/${phTotal} configured · ${ph.healthy_providers} healthy` : "checking…"}
        />
        <HealthRow
          name="Queue"
          level={execLevel}
          detail={execQ.data?.probe.state === "error" ? "endpoint unavailable" : "draining"}
        />
        <HealthRow
          name="Approvals"
          level={aprLevel}
          detail={apprQ.data?.probe.state === "error" ? "endpoint unavailable" : `${apprQ.data?.data.data?.length ?? 0} pending`}
        />
        <HealthRow
          name="Executions"
          level={execLevel}
          detail={execQ.data?.probe.state === "error" ? "endpoint unavailable" : `${execQ.data?.data.data?.length ?? 0} visible`}
        />
        <HealthRow
          name="Plans"
          level={plansLevel}
          detail={plansQ.data?.probe.state === "error" ? "endpoint unavailable" : "available"}
        />
        <HealthRow
          name="Reports"
          level={repLevel}
          detail={repQ.data?.probe.state === "error" ? "endpoint unavailable" : "available"}
        />
      </div>
    </div>
  );
}

function ClockAgo({ date }: { date: Date }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const seconds = Math.floor((now - date.getTime()) / 1000);
  if (seconds < 5) return <span>just now</span>;
  if (seconds < 60) return <span>{seconds}s ago</span>;
  if (seconds < 3600) return <span>{Math.floor(seconds / 60)}m ago</span>;
  return <span>{Math.floor(seconds / 3600)}h ago</span>;
}
