"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { TrendingUp, GitBranch, Mail, Users, AlertTriangle, CheckCircle2, FileText, Lightbulb } from "lucide-react";

interface ActivityEvent {
  id: string;
  event_type: string;
  domain: string;
  severity: string;
  title: string;
  description: string;
  entity_id?: string;
  entity_type?: string;
  occurred_at: string;
  action_required?: boolean;
}

function getEventIcon(eventType: string) {
  const iconMap: Record<string, any> = {
    campaign_created: GitBranch,
    campaign_launched: Play,
    campaign_complete: CheckCircle2,
    email_sent: Mail,
    email_replied: Mail,
    link_acquired: CheckCircle2,
    prospect_discovered: Users,
    keyword_research: Search,
    approval_requested: AlertTriangle,
    approval_approved: CheckCircle2,
    approval_rejected: XCircle,
    health_score_changed: TrendingUp,
    default: FileText,
  };
  
  const Icon = iconMap[eventType] || iconMap.default;
  return Icon;
}

function getSeverityColor(severity: string) {
  const colors: Record<string, string> = {
    critical: "text-red-400 bg-red-500/10 border-red-500/20",
    high: "text-orange-400 bg-orange-500/10 border-orange-500/20",
    medium: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    low: "text-slate-400 bg-slate-500/10 border-slate-500/20",
  };
  
  return colors[severity] || colors.low;
}

export function ActivityTimelineTab({ customerId }: { customerId: string }) {
  const tenantId = process.env.NEXT_PUBLIC_TENANT_ID || "00000000-0000-0000-0000-000000000001";

  const { data: events = [], isLoading, error } = useQuery<ActivityEvent[]>({
    queryKey: ["customer", customerId, "activity"],
    queryFn: async () => {
      const response = await fetchApi<any>(`/business-intelligence/intelligence/events?tenant_id=${tenantId}&limit=100`);
      return response?.data?.events || [];
    },
    refetchInterval: 60000,
  });

  // Filter events for this customer's campaigns
  const { data: campaigns = [] } = useQuery<any[]>({
    queryKey: ["customer", customerId, "campaigns"],
    queryFn: async () => {
      const response = await fetchApi<any>(`/business-intelligence/intelligence/campaigns?tenant_id=${tenantId}`);
      return (response?.data?.campaigns || []).filter((c: any) => c.client_id === customerId);
    },
  });

  const campaignIds = new Set(campaigns.map((c: any) => c.id));
  const filteredEvents = events.filter((e: ActivityEvent) => 
    !e.entity_id || campaignIds.has(e.entity_id)
  );

  const stats = {
    total: filteredEvents.length,
    critical: filteredEvents.filter((e) => e.severity === "critical").length,
    high: filteredEvents.filter((e) => e.severity === "high").length,
    actionsRequired: filteredEvents.filter((e) => e.action_required).length,
  };

  if (error) {
    return (
      <div className="p-6">
        <div className="text-center p-8 glass-panel">
          <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">Failed to load activity</h3>
          <p className="text-xs text-slate-500 mb-4">{(error as Error).message}</p>
          <button 
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-xs font-bold font-mono transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="text-center p-8 glass-panel">
          <TrendingUp className="w-12 h-12 text-platform-500 animate-spin mx-auto mb-3" />
          <p className="text-xs font-mono text-slate-500">Loading activity timeline...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-3">
        <div className="glass-panel p-4">
          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-500 uppercase mb-2">
            <FileText className="w-3.5 h-3.5" /> Total
          </div>
          <p className="text-2xl font-bold font-mono text-slate-100">{stats.total}</p>
        </div>
        <div className="glass-panel p-4 border-red-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-red-500 uppercase mb-2">
            <AlertTriangle className="w-3.5 h-3.5" /> Critical
          </div>
          <p className="text-2xl font-bold font-mono text-red-400">{stats.critical}</p>
        </div>
        <div className="glass-panel p-4 border-orange-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-orange-500 uppercase mb-2">
            <AlertTriangle className="w-3.5 h-3.5" /> High
          </div>
          <p className="text-2xl font-bold font-mono text-orange-400">{stats.high}</p>
        </div>
        <div className="glass-panel p-4 border-amber-500/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-amber-500 uppercase mb-2">
            <Lightbulb className="w-3.5 h-3.5" /> Actions
          </div>
          <p className="text-2xl font-bold font-mono text-amber-400">{stats.actionsRequired}</p>
        </div>
      </div>

      {/* Timeline */}
      <div className="glass-panel overflow-hidden">
        <div className="px-4 py-2 border-b border-surface-border bg-surface-darker/50">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-platform-400" />
            <h3 className="text-xs font-bold font-mono text-slate-200 uppercase">Activity Timeline</h3>
          </div>
        </div>

        {filteredEvents.length === 0 ? (
          <div className="p-8 text-center">
            <TrendingUp className="w-12 h-12 text-slate-700 mx-auto mb-3" />
            <h3 className="text-sm font-bold font-mono text-slate-300 mb-2">No Activity Yet</h3>
            <p className="text-xs text-slate-500">Activity will appear here as you work</p>
          </div>
        ) : (
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-8 top-0 bottom-0 w-0.5 bg-surface-border" />
            
            <div className="divide-y divide-surface-border/50">
              {filteredEvents.map((event, index) => {
                const Icon = getEventIcon(event.event_type);
                const severityColor = getSeverityColor(event.severity);
                
                return (
                  <div key={event.id} className="relative p-4 hover:bg-surface-border/20 transition-colors">
                    <div className="flex items-start gap-4">
                      {/* Timeline icon */}
                      <div className={`relative z-10 w-8 h-8 rounded-full border-2 ${severityColor} flex items-center justify-center flex-shrink-0`}>
                        <Icon className="w-4 h-4" />
                      </div>
                      
                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-bold font-mono text-slate-200">{event.title}</h4>
                          <span className={`px-1.5 py-0.5 text-[8px] font-mono rounded border ${severityColor}`}>
                            {event.severity.toUpperCase()}
                          </span>
                          {event.action_required && (
                            <span className="px-1.5 py-0.5 text-[8px] font-mono rounded border bg-amber-500/10 text-amber-400 border-amber-500/20">
                              ACTION NEEDED
                            </span>
                          )}
                        </div>
                        <p className="text-[10px] text-slate-500 mb-2">{event.description}</p>
                        <div className="flex items-center gap-3 text-[9px] font-mono text-slate-600">
                          <span>{event.domain.toUpperCase()}</span>
                          <span>•</span>
                          <span>{new Date(event.occurred_at).toLocaleString()}</span>
                          {event.entity_type && (
                            <>
                              <span>•</span>
                              <span>{event.entity_type}</span>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Additional icons needed
import { Play, XCircle, Search } from "lucide-react";