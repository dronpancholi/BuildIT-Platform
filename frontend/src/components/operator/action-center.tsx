"use client";

/**
 * Action Center — operator's single inbox.
 * Aggregates items that need attention from 5 sources, orders by urgency.
 */

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState, useMemo } from "react";
import {
  AlertOctagon, Inbox, Megaphone, Server, Key, FileText,
  ArrowRight, Filter, ChevronDown, ChevronUp,
} from "lucide-react";
import { fetchApi, ApiError } from "@/lib/api";
import { HealthPill } from "./health-pill";
import { HealthLevel } from "./health";
import { safeArr, safeStr, safeNum, safeFixed } from "@/lib/safe";

type Urgency = "urgent" | "warning" | "info";

interface ActionItem {
  id: string;
  urgency: Urgency;
  title: string;
  detail: string;
  age: string;
  source: string;
  href: string;
  actions?: { label: string; href?: string; onClick?: () => void; tone?: "primary" | "ghost" }[];
}

function ageString(iso?: string): string {
  if (!iso) return "recently";
  const ms = Date.now() - new Date(iso).getTime();
  if (ms < 0) return "just now";
  const sec = Math.floor(ms / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const days = Math.floor(hr / 24);
  return `${days}d ago`;
}

export function ActionCenter({ limit = 50, showFilters = true }: { limit?: number; showFilters?: boolean }) {
  const [filter, setFilter] = useState<"all" | Urgency>("all");

  // Sources
  const approvalsQ = useQuery<{ data: any[]; probe: "ok" | "error" | "unknown" }>({
    queryKey: ["ac-approvals"],
    queryFn: async () => {
      try {
        const data = await fetchApi<any>("/approvals?limit=20");
        return { data: data.data || data, probe: "ok" as const };
      } catch (e) {
        return { data: [], probe: (e instanceof ApiError && e.status === 500) ? "error" : "unknown" };
      }
    },
    refetchInterval: 15000,
  });

  const campaignsQ = useQuery<any>({
    queryKey: ["ac-campaigns"],
    queryFn: () => fetchApi<any>("/campaigns?limit=50"),
    refetchInterval: 15000,
  });

  const providerHealthQ = useQuery<any>({
    queryKey: ["ac-provider-health"],
    queryFn: () => fetchApi<any>("/provider-health"),
    refetchInterval: 15000,
  });

  const providerKeysQ = useQuery<any>({
    queryKey: ["ac-provider-keys"],
    queryFn: () => fetchApi<any>("/providers/keys"),
    refetchInterval: 30000,
  });

  const recsQ = useQuery<any>({
    queryKey: ["ac-recs"],
    queryFn: () => fetchApi<any>("/recommendations?limit=20"),
    refetchInterval: 60000,
  });

  const items = useMemo<ActionItem[]>(() => {
    const out: ActionItem[] = [];

    // Approvals
    if (approvalsQ.data?.probe === "ok") {
      for (const a of safeArr<any>(approvalsQ.data.data)) {
        out.push({
          id: `apr-${a.id}`,
          urgency: a.risk_level === "high" || a.risk_level === "critical" ? "urgent" : "warning",
          title: a.summary || a.title || "Approval awaiting decision",
          detail: a.reason || a.description || `Risk: ${a.risk_level || "unknown"}`,
          age: ageString(a.created_at || a.requested_at),
          source: "Approvals",
          href: "/dashboard/approvals",
          actions: [
            { label: "View", href: "/dashboard/approvals" },
            { label: "Approve", href: "/dashboard/approvals", tone: "primary" },
          ],
        });
      }
    } else if (approvalsQ.data?.probe === "error") {
      out.push({
        id: "apr-broken",
        urgency: "urgent",
        title: "Approvals endpoint unavailable",
        detail: "Cannot load pending approvals. Contact engineering.",
        age: "now",
        source: "System",
        href: "/dashboard/approvals",
      });
    }

    // Failing campaigns
    const campaigns = safeArr<any>(campaignsQ.data?.data || campaignsQ.data);
    if (campaigns.length > 0) {
      for (const c of campaigns) {
        if (c.status === "failed" || (typeof c.health_score === "number" && c.health_score < 0.3 && c.acquired_link_count === 0)) {
          out.push({
            id: `camp-${c.id}`,
            urgency: "urgent",
            title: `Campaign "${safeStr(c.name, "") || safeStr(c.id?.slice(0, 8), "unknown")}" is failing`,
            detail: `Health ${safeFixed(safeNum(c.health_score) * 100, 0)}% · ${safeNum(c.acquired_link_count)}/${safeNum(c.target_link_count)} links acquired`,
            age: ageString(c.updated_at),
            source: "Campaigns",
            href: `/dashboard/campaigns/${c.id}`,
            actions: [
              { label: "View", href: `/dashboard/campaigns/${c.id}` },
              { label: "Pause", href: `/dashboard/campaigns/${c.id}` },
            ],
          });
        }
      }
    }

    // Broken providers (configured but unhealthy)
    const ph = providerHealthQ.data?.providers;
    if (ph) {
      for (const [name, p] of Object.entries(ph)) {
        const prov = p as any;
        if (!prov.not_configured && !prov.healthy) {
          out.push({
            id: `prov-broken-${name}`,
            urgency: "warning",
            title: `Provider "${name}" is broken`,
            detail: `Circuit breaker: ${safeStr(prov.circuit_breaker_state, "unknown")} · ${safeNum(prov.total_calls_24h)} calls in 24h · ${safeFixed(prov.uptime_pct, 0)}% uptime`,
            age: "ongoing",
            source: "Providers",
            href: "/dashboard/providers",
            actions: [{ label: "Investigate", href: "/dashboard/providers", tone: "primary" }],
          });
        }
      }
    }

    // Missing provider keys
    const cat = providerKeysQ.data?.data?.catalog || providerKeysQ.data?.catalog;
    if (cat) {
      const missing = safeArr<any>(cat).filter((p: any) => !p.configured);
      if (missing.length > 0) {
        out.push({
          id: "prov-missing-keys",
          urgency: "warning",
          title: `${missing.length} of ${cat.length} providers missing API keys`,
          detail: `Affects: ${missing.map((p: any) => p.provider).join(", ")}`,
          age: "ongoing",
          source: "Providers",
          href: "/dashboard/providers",
          actions: [{ label: "Add Keys", href: "/dashboard/providers", tone: "primary" }],
        });
      }
    }

    // Recommendations
    const recs = safeArr<any>(recsQ.data?.data?.all_recommendations || recsQ.data?.all_recommendations || recsQ.data?.data || recsQ.data);
    if (recs.length > 0) {
      for (const r of recs.slice(0, 5)) {
        out.push({
          id: `rec-${r.id || Math.random()}`,
          urgency: r.priority === "P0" ? "warning" : "info",
          title: r.recommendation_text || r.title || "Recommendation awaiting review",
          detail: r.category ? `Category: ${r.category} · Impact: ${r.impact}` : (r.description || ""),
          age: ageString(r.created_at),
          source: "Recommendations",
          href: "/dashboard/recommendations",
          actions: [{ label: "Review", href: "/dashboard/recommendations" }],
        });
      }
    }

    return out.sort((a, b) => {
      const order = { urgent: 0, warning: 1, info: 2 };
      if (order[a.urgency] !== order[b.urgency]) return order[a.urgency] - order[b.urgency];
      return 0;
    });
  }, [approvalsQ.data, campaignsQ.data, providerHealthQ.data, providerKeysQ.data, recsQ.data]);

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return safeArr<ActionItem>(items).filter((i) => i.urgency === filter);
  }, [items, filter]);

  const counts = useMemo(() => ({
    urgent: safeArr<ActionItem>(items).filter((i) => i.urgency === "urgent").length,
    warning: safeArr<ActionItem>(items).filter((i) => i.urgency === "warning").length,
    info: safeArr<ActionItem>(items).filter((i) => i.urgency === "info").length,
  }), [items]);

  return (
    <div className="rounded-xl border border-surface-border bg-surface-card/80 backdrop-blur-md p-5 shadow-xl shadow-black/20">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-bold text-slate-100 tracking-tight flex items-center gap-2">
            <Inbox className="w-4 h-4 text-platform-400" />
            Action Center
          </h2>
          <p className="text-xs text-slate-500 font-mono mt-0.5">
            {items.length === 0 ? "All clear" : `${items.length} item${items.length === 1 ? "" : "s"} need attention`}
          </p>
        </div>
        {showFilters && (
          <div className="flex items-center gap-1 text-[10px] font-mono uppercase">
            {(["all", "urgent", "warning", "info"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-1 rounded border transition-colors ${
                  filter === f
                    ? "border-platform-500 bg-platform-500/20 text-platform-300"
                    : "border-surface-border text-slate-500 hover:text-slate-300"
                }`}
              >
                {f}{f !== "all" && counts[f as Urgency] > 0 ? ` (${counts[f as Urgency]})` : ""}
              </button>
            ))}
          </div>
        )}
      </div>

      {items.length === 0 ? (
        <div className="rounded-md border border-emerald-500/30 bg-emerald-500/5 p-6 text-center">
          <div className="text-sm text-emerald-300 font-semibold mb-1">All clear</div>
          <div className="text-xs text-slate-500">Nothing needs your attention right now.</div>
        </div>
      ) : (
        <ul className="space-y-2">
          {filtered.slice(0, limit).map((item) => (
            <ActionItemRow key={item.id} item={item} />
          ))}
        </ul>
      )}

      {filtered.length > limit && (
        <div className="mt-3 text-center">
          <Link href="/dashboard/action-center" className="text-xs text-platform-400 hover:text-platform-300 font-mono">
            View all {filtered.length} →
          </Link>
        </div>
      )}
    </div>
  );
}

function ActionItemRow({ item }: { item: ActionItem }) {
  const icon =
    item.urgency === "urgent" ? <AlertOctagon className="w-4 h-4 text-red-400" /> :
    item.urgency === "warning" ? <AlertOctagon className="w-4 h-4 text-amber-400" /> :
    <FileText className="w-4 h-4 text-slate-400" />;
  const borderColor =
    item.urgency === "urgent" ? "border-red-500/30 bg-red-500/5" :
    item.urgency === "warning" ? "border-amber-500/30 bg-amber-500/5" :
    "border-slate-500/30 bg-slate-500/5";

  return (
    <li className={`rounded-md border p-3 ${borderColor} hover:border-slate-500 transition-colors`}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex-shrink-0">{icon}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="text-sm font-semibold text-slate-100">{item.title}</div>
            <div className="text-[10px] text-slate-500 font-mono whitespace-nowrap">{item.age}</div>
          </div>
          <div className="text-xs text-slate-400 mt-0.5">{item.detail}</div>
          <div className="flex items-center justify-between mt-2">
            <div className="text-[10px] text-slate-500 font-mono uppercase tracking-wider">From: {item.source}</div>
            <div className="flex items-center gap-1.5">
              {item.actions?.map((a, i) => (
                a.href ? (
                  <Link
                    key={i}
                    href={a.href}
                    className={`text-[10px] font-mono uppercase px-2 py-1 rounded border transition-colors ${
                      a.tone === "primary"
                        ? "border-platform-500 bg-platform-500/10 text-platform-300 hover:bg-platform-500/20"
                        : "border-surface-border text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {a.label}
                  </Link>
                ) : null
              ))}
            </div>
          </div>
        </div>
      </div>
    </li>
  );
}
