"use client";

/**
 * Provider Command Center — single source of truth for provider status.
 * Phase 1.3.4: Now reads from the server-computed /providers/unified endpoint.
 * No more client-side reconciliation. The server decides healthy | broken |
 * needs-key | untested | disabled | unknown. We just render.
 */

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState, useMemo } from "react";
import {
  Key, Zap, AlertTriangle, CheckCircle2, XCircle,
  TestTube2, Loader2, Search,
} from "lucide-react";
import { fetchApi } from "@/lib/api";
import { HealthPill } from "./health-pill";
import { HealthLevel } from "./health";
import { safeArr, safeLower } from "@/lib/safe";

type UnifiedStatus = "healthy" | "broken" | "needs-key" | "untested" | "disabled" | "unknown";

interface ProviderUnifiedRow {
  provider: string;
  label: string;
  category?: string;
  fields?: string[];
  configured: boolean;
  last_key_update?: string | null;
  last_key_updated_by?: string | null;
  is_active_seo?: boolean;
  tracked: boolean;
  uptime_pct: number;
  avg_latency_ms: number;
  total_calls_24h: number;
  success_count_24h: number;
  circuit_breaker_state: string;
  not_configured: boolean;
  unified_status: UnifiedStatus;
  unified_reason: string;
}

interface UnifiedResponse {
  providers: ProviderUnifiedRow[];
  summary: {
    total: number;
    healthy: number;
    broken: number;
    needs_key: number;
    untested: number;
    disabled: number;
    unknown: number;
  };
}

export function ProviderCommandCenter() {
  const qc = useQueryClient();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | UnifiedStatus>("all");
  const [testingProvider, setTestingProvider] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, { ok: boolean; message: string; at: string }>>({});

  const unifiedQ = useQuery<UnifiedResponse>({
    queryKey: ["pcc-unified"],
    queryFn: () => fetchApi<UnifiedResponse>("/providers/unified"),
    refetchInterval: 15000,
  });

  const rows = useMemo<ProviderUnifiedRow[]>(() => {
    return unifiedQ.data?.providers ?? [];
  }, [unifiedQ.data]);

  const counts = useMemo(() => ({
    total: rows.length,
    healthy: rows.filter((r) => r.unified_status === "healthy").length,
    broken: rows.filter((r) => r.unified_status === "broken").length,
    needsKey: rows.filter((r) => r.unified_status === "needs-key").length,
    untested: rows.filter((r) => r.unified_status === "untested").length,
    disabled: rows.filter((r) => r.unified_status === "disabled").length,
    unknown: rows.filter((r) => r.unified_status === "unknown").length,
  }), [rows]);

  const filtered = useMemo(() => {
    return safeArr<ProviderUnifiedRow>(rows).filter((r) => {
      if (filter !== "all" && r.unified_status !== filter) return false;
      if (search) {
        const s = safeLower(search, "");
        if (!safeLower(r.provider, "").includes(s) && !safeLower(r.label, "").includes(s)) {
          return false;
        }
      }
      return true;
    });
  }, [rows, filter, search]);

  const testConnection = async (provider: string) => {
    setTestingProvider(provider);
    try {
      const data = await fetchApi<UnifiedResponse>(`/providers/unified`);
      const target = data.providers.find((p) => p.provider === provider);
      let ok = false;
      let message = "Provider status check completed";
      if (target) {
        if (target.unified_status === "healthy") {
          ok = true;
          message = `Healthy · uptime ${target.uptime_pct}% · ${target.total_calls_24h} calls in 24h`;
        } else if (target.unified_status === "broken") {
          ok = false;
          message = `Broken · ${target.unified_reason}`;
        } else if (target.unified_status === "untested") {
          ok = false;
          message = "Provider has not been exercised yet — no calls recorded in 24h";
        } else {
          message = `Status: ${target.unified_status} · ${target.unified_reason}`;
        }
      }
      setTestResults((prev) => ({
        ...prev,
        [provider]: { ok, message, at: new Date().toISOString() },
      }));
      qc.invalidateQueries({ queryKey: ["pcc-unified"] });
    } catch (e) {
      setTestResults((prev) => ({
        ...prev,
        [provider]: {
          ok: false,
          message: e instanceof Error ? e.message : "Test failed",
          at: new Date().toISOString(),
        },
      }));
    } finally {
      setTestingProvider(null);
    }
  };

  if (unifiedQ.isError) {
    return (
      <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-6">
        <div className="flex items-center gap-2 mb-2">
          <XCircle className="w-5 h-5 text-red-400" />
          <h2 className="text-lg font-bold text-slate-100">Provider data unavailable</h2>
        </div>
        <p className="text-sm text-slate-300">/api/v1/providers/unified failed to respond.</p>
        <button
          onClick={() => qc.invalidateQueries({ queryKey: ["pcc-unified"] })}
          className="mt-3 px-3 py-1.5 rounded-md border border-surface-border text-sm text-slate-300 hover:border-slate-500"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-surface-border bg-surface-card/80 backdrop-blur-md p-5 shadow-xl shadow-black/20">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-100 tracking-tight flex items-center gap-2">
              <Zap className="w-4 h-4 text-platform-400" />
              Providers
            </h2>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              {counts.total} providers · {counts.healthy} healthy · {counts.broken} broken · {counts.needsKey} need keys · {counts.untested} untested
            </p>
          </div>
        </div>
        {counts.broken > 0 && (
          <div className="mt-3 px-3 py-2 rounded-md border border-red-500/30 bg-red-500/10 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-red-200">
              <strong className="font-bold">{counts.broken} provider(s) broken.</strong> A key is configured but uptime is below 80% or the circuit breaker is OPEN. Click INVESTIGATE on the affected row.
            </div>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-500" />
          <input
            type="text"
            placeholder="Search providers…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-md border border-surface-border bg-surface-darker text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500"
          />
        </div>
        <div className="flex items-center gap-1 text-[10px] font-mono uppercase">
          {(["all", "healthy", "broken", "needs-key", "untested"] as const).map((f) => {
            const c = f === "all" ? counts.total :
                       f === "healthy" ? counts.healthy :
                       f === "broken" ? counts.broken :
                       f === "needs-key" ? counts.needsKey :
                       counts.untested;
            return (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-1 rounded border transition-colors ${
                  filter === f
                    ? "border-platform-500 bg-platform-500/20 text-platform-300"
                    : "border-surface-border text-slate-500 hover:text-slate-300"
                }`}
              >
                {f}{f !== "all" && c > 0 ? ` (${c})` : ""}
              </button>
            );
          })}
        </div>
      </div>

      <ul className="space-y-2">
        {filtered.map((p) => (
          <ProviderRow
            key={p.provider}
            p={p}
            onTest={() => testConnection(p.provider)}
            testing={testingProvider === p.provider}
            testResult={testResults[p.provider]}
          />
        ))}
      </ul>

      {filtered.length === 0 && (
        <div className="rounded-xl border border-surface-border bg-surface-card/80 p-12 text-center">
          <div className="text-sm text-slate-300 font-semibold mb-1">No providers match</div>
          <div className="text-xs text-slate-500">Try clearing your filters.</div>
        </div>
      )}
    </div>
  );
}

function ProviderRow({ p, onTest, testing, testResult }: {
  p: ProviderUnifiedRow;
  onTest: () => void;
  testing: boolean;
  testResult?: { ok: boolean; message: string; at: string };
}) {
  const levelMap: Record<UnifiedStatus, HealthLevel> = {
    healthy: "healthy",
    broken: "critical",
    "needs-key": "warning",
    untested: "unknown",
    disabled: "unknown",
    unknown: "unknown",
  };
  const labelMap: Record<UnifiedStatus, string> = {
    healthy: "HEALTHY",
    broken: "BROKEN",
    "needs-key": "NEEDS KEY",
    untested: "UNTESTED",
    disabled: "DISABLED",
    unknown: "UNKNOWN",
  };

  const borderColor =
    p.unified_status === "healthy" ? "border-emerald-500/30 bg-emerald-500/5" :
    p.unified_status === "broken" ? "border-red-500/30 bg-red-500/5" :
    p.unified_status === "needs-key" ? "border-amber-500/30 bg-amber-500/5" :
    "border-surface-border bg-surface-card/40";

  return (
    <li className={`rounded-md border p-4 ${borderColor}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <div className="text-sm font-semibold text-slate-100">{p.label}</div>
            <HealthPill level={levelMap[p.unified_status]} size="sm" />
            <span className="text-[10px] font-mono text-slate-500">{labelMap[p.unified_status]}</span>
            {p.category && (
              <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider">· {p.category}</span>
            )}
            {p.is_active_seo && (
              <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider">· active SEO</span>
            )}
          </div>
          <div className="text-xs text-slate-300 mb-2">{p.unified_reason}</div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-3 gap-y-1 text-[11px] font-mono">
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Configured</div>
              <div className={p.configured ? "text-emerald-300" : "text-amber-300"}>
                {p.configured ? "yes" : "no"}
              </div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Last 24h</div>
              <div className="text-slate-300">{p.total_calls_24h} calls</div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Uptime</div>
              <div className="text-slate-300">
                {p.tracked && p.total_calls_24h > 0 ? `${p.uptime_pct.toFixed(1)}%` : "—"}
              </div>
            </div>
            <div>
              <div className="text-slate-500 uppercase tracking-wider">Circuit</div>
              <div className={p.circuit_breaker_state === "OPEN" ? "text-red-300" : "text-slate-300"}>
                {p.circuit_breaker_state}
              </div>
            </div>
          </div>

          {testResult && (
            <div className={`mt-2 text-[11px] font-mono rounded px-2 py-1.5 border ${
              testResult.ok
                ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300"
                : "border-red-500/30 bg-red-500/10 text-red-300"
            }`}>
              {testResult.ok ? "✓" : "✗"} {testResult.message} · {new Date(testResult.at).toLocaleTimeString()}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-1.5 flex-shrink-0">
          <button
            onClick={onTest}
            disabled={testing}
            className="px-3 py-1.5 rounded-md border border-platform-500/30 bg-platform-500/10 text-platform-300 text-xs font-mono font-bold hover:bg-platform-500/20 disabled:opacity-50 flex items-center gap-1.5"
          >
            {testing ? <Loader2 className="w-3 h-3 animate-spin" /> : <TestTube2 className="w-3 h-3" />}
            TEST
          </button>
          {!p.configured && (
            <Link
              href={`/dashboard/providers/${p.provider}`}
              className="px-3 py-1.5 rounded-md border border-amber-500/30 bg-amber-500/10 text-amber-300 text-xs font-mono font-bold hover:bg-amber-500/20 flex items-center gap-1.5"
            >
              <Key className="w-3 h-3" /> ADD KEY
            </Link>
          )}
          {p.unified_status === "broken" && (
            <Link
              href={`/dashboard/providers/${p.provider}`}
              className="px-3 py-1.5 rounded-md border border-red-500/30 bg-red-500/10 text-red-300 text-xs font-mono font-bold hover:bg-red-500/20 flex items-center gap-1.5"
            >
              <AlertTriangle className="w-3 h-3" /> INVESTIGATE
            </Link>
          )}
        </div>
      </div>
    </li>
  );
}
