"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Activity, AlertTriangle, CheckCircle2, Info, Search,
  Link2, BarChart3, Zap, Radio, GitBranch, Shield,
  TrendingUp, Target, Users,
} from "lucide-react";
import { fetchApi } from "@/lib/api";

interface TickerEvent {
  id: string;
  event_type: string;
  summary: string;
  severity: string;
  created_at: string;
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  operational_pulse: <Activity className="w-3 h-3" />,
  campaign_alert: <BarChart3 className="w-3 h-3" />,
  health_scan_complete: <CheckCircle2 className="w-3 h-3" />,
  discovery_cycle_complete: <Search className="w-3 h-3" />,
  campaign_health_warning: <AlertTriangle className="w-3 h-3" />,
  idle_scan: <Zap className="w-3 h-3" />,
  backlink_verified: <Link2 className="w-3 h-3" />,
  serp_change: <TrendingUp className="w-3 h-3" />,
  recommendation_generated: <Target className="w-3 h-3" />,
  workflow_started: <Radio className="w-3 h-3" />,
  workflow_completed: <CheckCircle2 className="w-3 h-3" />,
  campaign_health_changed: <GitBranch className="w-3 h-3" />,
  citation_drift: <Shield className="w-3 h-3" />,
};

const SEVERITY_STYLES: Record<string, string> = {
  warning: "text-amber-400",
  error: "text-red-400",
  info: "text-platform-400",
  success: "text-emerald-400",
};

function getIcon(event: TickerEvent): React.ReactNode {
  return TYPE_ICONS[event.event_type] || <Activity className="w-3 h-3" />;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 60000) return "now";
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`;
  return d.toLocaleDateString();
}

function getSeverityStyle(severity: string): string {
  return SEVERITY_STYLES[severity] || SEVERITY_STYLES.info;
}

export function LiveEventTicker() {
  const [events, setEvents] = useState<TickerEvent[]>([]);
  const [visible, setVisible] = useState(true);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetch = async () => {
      try {
        const data = await fetchApi<TickerEvent[]>("/operations/operations-feed?limit=20");
        if (data) setEvents(data);
      } catch {}
    };
    fetch();
    const interval = setInterval(fetch, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollLeft = 0;
    }
  }, [events]);

  if (!visible || events.length === 0) return null;

  return (
    <div className="border-b border-surface-border bg-surface-card/30 backdrop-blur-sm">
      <div className="flex items-center max-w-6xl mx-auto">
        <div className="flex items-center gap-2 px-4 py-1.5 border-r border-surface-border bg-surface-darker/50 flex-shrink-0">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-[9px] font-mono text-emerald-400 font-bold uppercase tracking-wider">LIVE</span>
        </div>
        <div
          ref={scrollRef}
          className="flex-1 overflow-x-auto custom-scrollbar flex items-center gap-4 px-4 py-1.5"
        >
          <AnimatePresence mode="popLayout">
            {events.slice(0, 12).map((event) => (
              <motion.div
                key={event.id}
                layout
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 10 }}
                transition={{ duration: 0.2 }}
                className={`flex items-center gap-1.5 text-[10px] font-mono whitespace-nowrap ${getSeverityStyle(event.severity)}`}
              >
                {getIcon(event)}
                <span className="text-slate-400 max-w-[200px] truncate">{event.summary}</span>
                <span className="text-slate-600 ml-1">{formatTime(event.created_at)}</span>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
        <button
          onClick={() => setVisible(false)}
          className="px-3 py-1.5 text-[9px] font-mono text-slate-600 hover:text-slate-400 hover:bg-surface-border transition-colors border-l border-surface-border flex-shrink-0"
        >
          HIDE
        </button>
      </div>
    </div>
  );
}
