"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, AlertTriangle, CheckCircle2, Info, RefreshCw,
  Search, Link2, BarChart3, Shield, Zap, Loader2,
} from "lucide-react";
import { fetchApi } from "@/lib/api";

interface OperationalEvent {
  id: string;
  event_type: string;
  summary: string;
  severity: string;
  metadata: Record<string, any> | null;
  created_at: string;
}

const SEVERITY_CONFIG: Record<string, { color: string; icon: React.ReactNode }> = {
  warning: { color: "border-amber-500/30 bg-amber-500/5 text-amber-400", icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  error: { color: "border-red-500/30 bg-red-500/5 text-red-400", icon: <AlertTriangle className="w-3.5 h-3.5" /> },
  info: { color: "border-platform-500/20 bg-platform-500/5 text-platform-400", icon: <Info className="w-3.5 h-3.5" /> },
  success: { color: "border-emerald-500/20 bg-emerald-500/5 text-emerald-400", icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
};

const TYPE_ICONS: Record<string, React.ReactNode> = {
  operational_pulse: <Activity className="w-3.5 h-3.5" />,
  campaign_alert: <BarChart3 className="w-3.5 h-3.5" />,
  health_scan_complete: <CheckCircle2 className="w-3.5 h-3.5" />,
  discovery_cycle_complete: <Search className="w-3.5 h-3.5" />,
  campaign_health_warning: <AlertTriangle className="w-3.5 h-3.5" />,
  idle_scan: <Zap className="w-3.5 h-3.5" />,
};

function getEventIcon(event: OperationalEvent): React.ReactNode {
  return TYPE_ICONS[event.event_type] || <Activity className="w-3.5 h-3.5" />;
}

function getSeverityStyle(severity: string): string {
  return SEVERITY_CONFIG[severity]?.color || SEVERITY_CONFIG.info.color;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60000) return "just now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return d.toLocaleDateString();
}

export default function LiveFeed() {
  const [events, setEvents] = useState<OperationalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [paused, setPaused] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval>>(undefined);

  const fetchEvents = async () => {
    try {
      const data = await fetchApi<OperationalEvent[]>("/operations/operations-feed?limit=50");
      setEvents(data || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
    pollRef.current = setInterval(() => {
      if (!paused) fetchEvents();
    }, 5000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [paused]);

  useEffect(() => {
    if (feedRef.current && !paused) {
      feedRef.current.scrollTop = 0;
    }
  }, [events, paused]);

  return (
    <div className="glass-panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-emerald-400" />
          <h3 className="text-sm font-semibold text-slate-200 font-mono uppercase tracking-wider">
            Live Feed
          </h3>
          <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-[10px] font-mono text-emerald-400">LIVE</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPaused(!paused)}
            className={`text-[10px] font-mono px-2 py-1 rounded border transition-colors ${
              paused ? "bg-amber-500/10 border-amber-500/20 text-amber-400" : "bg-slate-800 border-slate-700 text-slate-500"
            }`}
          >
            {paused ? "PAUSED" : "AUTO"}
          </button>
          <button
            onClick={fetchEvents}
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>
      </div>

      <div
        ref={feedRef}
        className="space-y-1 max-h-[400px] overflow-y-auto custom-scrollbar"
      >
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-5 h-5 text-slate-500 animate-spin" />
          </div>
        ) : events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Activity className="w-8 h-8 text-slate-700 mb-2" />
            <p className="text-xs text-slate-600 font-mono">Waiting for operational activity...</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {events.map((event, idx) => {
              const sev = event.severity || "info";
              const sevConfig = SEVERITY_CONFIG[sev] || SEVERITY_CONFIG.info;
              return (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2, delay: Math.min(idx * 0.02, 0.3) }}
                  className={`flex items-start gap-2.5 p-2 rounded border ${sevConfig.color} transition-colors hover:brightness-110`}
                >
                  <div className="mt-0.5 flex-shrink-0">
                    {getEventIcon(event)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-mono text-slate-300 leading-relaxed truncate">
                      {event.summary}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[9px] font-mono text-slate-600 uppercase">
                        {event.event_type.replace(/_/g, " ")}
                      </span>
                      <span className="text-[9px] font-mono text-slate-600">
                        {formatTime(event.created_at)}
                      </span>
                    </div>
                  </div>
                  <span className="text-[9px] font-mono uppercase text-slate-600 flex-shrink-0">
                    {sev}
                  </span>
                </motion.div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
