"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Radio, X, Search, Filter, ChevronDown, ChevronUp,
  Activity, CheckCircle2, AlertTriangle, Zap, Server, Play,
} from "lucide-react";
import { API_BASE_URL, MOCK_TENANT_ID } from "@/lib/api";

interface StreamEvent {
  type: string;
  event_type?: string;
  channel?: string;
  tenant_id?: string;
  timestamp?: number;
  source_service?: string;
  severity?: string;
  payload?: Record<string, unknown>;
  [key: string]: unknown;
}

const EVENT_TYPES = ["workflow", "approval", "campaign", "infra"];
const SEVERITY_LEVELS = ["info", "warning", "error", "critical"];

const EVENT_STYLE: Record<string, { icon: React.ReactNode; bg: string; border: string; text: string }> = {
  workflow: {
    icon: <Play className="w-3.5 h-3.5" />,
    bg: "bg-blue-500/10",
    border: "border-blue-500/20",
    text: "text-blue-400",
  },
  approval: {
    icon: <CheckCircle2 className="w-3.5 h-3.5" />,
    bg: "bg-amber-500/10",
    border: "border-amber-500/20",
    text: "text-amber-400",
  },
  campaign: {
    icon: <Zap className="w-3.5 h-3.5" />,
    bg: "bg-emerald-500/10",
    border: "border-emerald-500/20",
    text: "text-emerald-400",
  },
  infra: {
    icon: <Server className="w-3.5 h-3.5" />,
    bg: "bg-red-500/10",
    border: "border-red-500/20",
    text: "text-red-400",
  },
};

const SEVERITY_STYLE: Record<string, string> = {
  info: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  warning: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  error: "bg-red-500/10 text-red-400 border-red-500/20",
  critical: "bg-red-500/20 text-red-300 border-red-500/30",
};

function detectChannel(type: string): string {
  const lower = type.toLowerCase();
  if (lower.includes("workflow") || lower.includes("onboarding") || lower.includes("keyword") || lower.includes("backlink") || lower.includes("citation") || lower.includes("report")) return "workflow";
  if (lower.includes("approval") || lower.includes("sla") || lower.includes("gate")) return "approval";
  if (lower.includes("campaign") || lower.includes("outreach") || lower.includes("link")) return "campaign";
  if (lower.includes("infra") || lower.includes("db") || lower.includes("kafka") || lower.includes("redis") || lower.includes("temporal")) return "infra";
  return "workflow";
}

export default function EventStreamPage() {
  const [isLive, setIsLive] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);
  const [expandedEvent, setExpandedEvent] = useState<number | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [sourceFilter, setSourceFilter] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const retryRef = useRef(0);

  useEffect(() => {
    if (!isLive) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return;
    }

    const connect = () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
      const url = `${API_BASE_URL}/stream/${MOCK_TENANT_ID}?channels=workflows,approvals,campaigns,infrastructure`;
      const es = new EventSource(url);
      eventSourceRef.current = es;

      es.onopen = () => { retryRef.current = 0; };

      es.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data);
          const enriched: StreamEvent = {
            ...parsed,
            channel: parsed.channel || detectChannel(parsed.type || parsed.event_type || ""),
            severity: parsed.severity || "info",
            source_service: parsed.source_service || "unknown",
            timestamp: parsed.timestamp || Date.now() / 1000,
          };
          setEvents((prev) => [enriched, ...prev].slice(0, 1000));
        } catch {}
      };

      es.onerror = () => {
        es.close();
        const delay = Math.min(1000 * 2 ** retryRef.current, 30000);
        retryRef.current += 1;
        setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [isLive]);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events, autoScroll]);

  const filteredEvents = useMemo(() => {
    return events.filter((evt) => {
      if (typeFilter !== "all" && evt.channel !== typeFilter) return false;
      if (severityFilter !== "all" && evt.severity !== severityFilter) return false;
      if (sourceFilter && !(evt.source_service || "").toLowerCase().includes(sourceFilter.toLowerCase())) return false;
      return true;
    });
  }, [events, typeFilter, severityFilter, sourceFilter]);

  const formatTimestamp = (ts?: number) => {
    if (!ts) return "—";
    return new Date(ts * 1000).toISOString();
  };

  const getEventStyle = (channel?: string) => {
    return EVENT_STYLE[channel || "workflow"] || EVENT_STYLE.workflow;
  };

  const truncatePayload = (evt: StreamEvent, maxLen = 100) => {
    const { type, event_type, channel, tenant_id, timestamp, severity, source_service, ...rest } = evt;
    return JSON.stringify(rest).slice(0, maxLen);
  };

  return (
    <div className="space-y-6 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">EVENT_STREAM</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Kafka Domain Event Feed</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-slate-500 font-mono">{filteredEvents.length} events</div>
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`px-2 py-1.5 rounded border text-xs font-mono transition-colors ${
              autoScroll ? "bg-platform-500/10 border-platform-500/30 text-platform-400" : "bg-surface-darker border-surface-border text-slate-400"
            }`}
          >
            {autoScroll ? "AUTO_SCROLL" : "MANUAL"}
          </button>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`px-3 py-1.5 rounded-md border text-xs font-mono flex items-center gap-2 transition-colors ${
              showFilters || typeFilter !== "all" || severityFilter !== "all"
                ? "bg-platform-500/10 border-platform-500/30 text-platform-400"
                : "bg-surface-darker border-surface-border text-slate-400"
            }`}
          >
            <Filter className="w-3.5 h-3.5" />
            FILTERS
          </button>
          <button
            onClick={() => setIsLive(!isLive)}
            className={`px-3 py-1.5 rounded-md border text-xs font-mono font-bold transition-colors ${
              isLive
                ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                : "bg-surface-darker border-surface-border text-slate-400"
            }`}
          >
            <span className={`w-2 h-2 rounded-full inline-block mr-2 ${isLive ? "bg-emerald-500 animate-pulse" : "bg-slate-600"}`}></span>
            {isLive ? "LIVE" : "PAUSED"}
          </button>
        </div>
      </div>

      {/* Filter Panel */}
      <AnimatePresence>
        {showFilters && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="glass-panel p-4 flex flex-wrap items-center gap-6">
              <div>
                <label className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-1.5">Event Type</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setTypeFilter("all")}
                    className={`px-3 py-1.5 text-xs font-mono rounded border transition-colors ${
                      typeFilter === "all" ? "bg-platform-500/10 border-platform-500/30 text-platform-400" : "bg-surface-darker border-surface-border text-slate-500"
                    }`}
                  >ALL</button>
                  {EVENT_TYPES.map((t) => (
                    <button
                      key={t}
                      onClick={() => setTypeFilter(t)}
                      className={`px-3 py-1.5 text-xs font-mono rounded border transition-colors ${
                        typeFilter === t ? "bg-platform-500/10 border-platform-500/30 text-platform-400" : "bg-surface-darker border-surface-border text-slate-500"
                      }`}
                    >{t.toUpperCase()}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-1.5">Severity</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSeverityFilter("all")}
                    className={`px-3 py-1.5 text-xs font-mono rounded border transition-colors ${
                      severityFilter === "all" ? "bg-platform-500/10 border-platform-500/30 text-platform-400" : "bg-surface-darker border-surface-border text-slate-500"
                    }`}
                  >ALL</button>
                  {SEVERITY_LEVELS.map((s) => (
                    <button
                      key={s}
                      onClick={() => setSeverityFilter(s)}
                      className={`px-3 py-1.5 text-xs font-mono rounded border transition-colors ${
                        severityFilter === s ? "bg-platform-500/10 border-platform-500/30 text-platform-400" : "bg-surface-darker border-surface-border text-slate-500"
                      }`}
                    >{s.toUpperCase()}</button>
                  ))}
                </div>
              </div>
              <div>
                <label className="text-[10px] font-mono text-slate-500 uppercase tracking-widest block mb-1.5">Source Service</label>
                <input
                  type="text"
                  placeholder="Filter by service..."
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  className="px-3 py-1.5 text-xs font-mono bg-surface-darker border border-surface-border rounded text-slate-200 placeholder-slate-500 focus:outline-none focus:border-platform-500"
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Event Stream */}
      <div className="flex-1 glass-panel overflow-hidden flex flex-col">
        <div className="px-6 py-3 border-b border-surface-border flex items-center gap-4 text-[10px] font-mono text-slate-500 uppercase tracking-widest bg-surface-darker">
          <span className="w-20">Severity</span>
          <span className="w-44">Timestamp</span>
          <span className="w-20">Source</span>
          <span className="w-48">Event Type</span>
          <span className="flex-1">Payload Preview</span>
        </div>
        <div ref={scrollRef} className="flex-1 overflow-auto custom-scrollbar">
          {filteredEvents.length === 0 ? (
            <div className="flex items-center justify-center p-12 h-full">
              <div className="text-center flex flex-col items-center">
                <div className="w-16 h-16 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center mb-4">
                  <Radio className="text-slate-600" size={32} />
                </div>
                <h3 className="text-lg font-medium text-slate-300 font-mono">
                  {isLive ? "Waiting for Events..." : "No Events in Stream"}
                </h3>
                <p className="text-sm text-slate-500 mt-2 max-w-sm">
                  {isLive
                    ? "Listening for domain events. Events will appear as workflows execute and campaigns progress."
                    : "Toggle LIVE to start listening for events."}
                </p>
              </div>
            </div>
          ) : (
            <div className="divide-y divide-surface-border">
              {filteredEvents.map((evt, i) => {
                const style = getEventStyle(evt.channel);
                const isExpanded = expandedEvent === i;
                return (
                  <div key={`${evt.timestamp}-${i}`}>
                    <div
                      onClick={() => setExpandedEvent(isExpanded ? null : i)}
                      className={`px-6 py-2.5 flex items-center gap-4 text-xs font-mono hover:bg-surface-darker/50 cursor-pointer transition-colors ${style.bg}`}
                    >
                      <span className="w-20">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                          SEVERITY_STYLE[evt.severity || "info"] || SEVERITY_STYLE.info
                        }`}>
                          {(evt.severity || "info").toUpperCase()}
                        </span>
                      </span>
                      <span className="w-44 text-slate-500 flex items-center gap-2">
                        {style.icon}
                        {formatTimestamp(evt.timestamp)}
                      </span>
                      <span className="w-20 text-slate-500">{evt.source_service || "—"}</span>
                      <span className={`w-48 flex items-center gap-2 ${style.text}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${style.bg.replace("/10", "")}`}></span>
                        {evt.event_type || evt.type || "—"}
                      </span>
                      <span className="flex-1 text-slate-500 truncate flex items-center gap-2">
                        {truncatePayload(evt)}
                        {isExpanded ? <ChevronUp className="w-3 h-3 flex-shrink-0" /> : <ChevronDown className="w-3 h-3 flex-shrink-0" />}
                      </span>
                    </div>
                    {isExpanded && (
                      <div className="px-6 py-4 bg-surface-darker/30 border-t border-surface-border/50">
                        <pre className="text-xs font-mono text-slate-400 whitespace-pre-wrap overflow-x-auto max-h-64 overflow-y-auto custom-scrollbar">
                          {JSON.stringify(evt, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
