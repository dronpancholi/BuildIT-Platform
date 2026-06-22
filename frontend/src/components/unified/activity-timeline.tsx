"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { 
  UserPlus, GitBranch, Sparkles, Search, Mail, 
  CheckCircle, FileText, AlertCircle, TrendingUp, Clock 
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";
import { safeArr, safeUpper } from "@/lib/safe";

interface ActivityTimelineProps {
  className?: string;
}

interface Activity {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  customer_name?: string;
  campaign_name?: string;
}

const typeConfig: any = {
  customer_created: { icon: UserPlus, color: "text-blue-400", bg: "bg-blue-500/10" },
  campaign_created: { icon: GitBranch, color: "text-purple-400", bg: "bg-purple-500/10" },
  keyword_discovered: { icon: Sparkles, color: "text-amber-400", bg: "bg-amber-500/10" },
  prospect_found: { icon: Search, color: "text-emerald-400", bg: "bg-emerald-500/10" },
  email_generated: { icon: Mail, color: "text-slate-400", bg: "bg-slate-500/10" },
  email_sent: { icon: Mail, color: "text-blue-400", bg: "bg-blue-500/10" },
  reply_received: { icon: Mail, color: "text-green-400", bg: "bg-green-500/10" },
  approval_completed: { icon: CheckCircle, color: "text-green-400", bg: "bg-green-500/10" },
  report_generated: { icon: FileText, color: "text-indigo-400", bg: "bg-indigo-500/10" },
  link_acquired: { icon: TrendingUp, color: "text-emerald-400", bg: "bg-emerald-500/10" },
};

function mapEventType(eventType: string): string {
  const mapping: any = {
    'prospecting_active': 'campaign_created',
    'outreach_replies_received': 'reply_received',
    'links_verified': 'link_acquired',
    'keyword_discovered': 'keyword_discovered',
    'email_sent': 'email_sent',
    'approval_completed': 'approval_completed',
  };
  return mapping[eventType] || 'customer_created';
}

export function ActivityTimeline({ className }: ActivityTimelineProps) {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["activity-timeline"],
    queryFn: () => fetchApi("/business-intelligence/intelligence/events?limit=20"),
    refetchInterval: 30000,
  });

  // Transform BI events to activity format
  const events = safeArr<any>(data?.data?.events);
  const activities: Activity[] = safeArr<any>(events).map((e: any) => ({
    id: e.id || e.event_type,
    type: mapEventType(e.event_type),
    title: safeUpper(e.event_type?.replace('_', ' '), 'Event'),
    description: e.description || e.message || '',
    timestamp: e.occurred_at || e.created_at || new Date().toISOString(),
    campaign_name: e.campaign_name,
    customer_name: e.customer_name,
  }));

  return (
    <Card className={cn("bg-surface-card border-surface-border", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-slate-400">Activity Timeline</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-platform-500"></div>
          </div>
        ) : activities.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            No recent activity
          </div>
        ) : (
          <div className="space-y-0">
            {activities.slice(0, 20).map((activity, index) => {
              const config = typeConfig[activity.type] || { icon: AlertCircle, color: "text-slate-400", bg: "bg-slate-500/10" };
              const Icon = config.icon;

              return (
                <div key={activity.id} className="relative">
                  {index < activities.length - 1 && (
                    <div className="absolute left-4 top-8 bottom-0 w-px bg-surface-border" />
                  )}
                  <div className="flex items-start gap-4 py-3">
                    <div className={cn("w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0", config.bg)}>
                      <Icon className={cn("w-4 h-4", config.color)} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-medium text-slate-200">{activity.title}</h4>
                        <span className="text-xs text-slate-500">
                          {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                        </span>
                      </div>
                      <p className="text-xs text-slate-500 mt-1">{activity.description}</p>
                      {(activity.customer_name || activity.campaign_name) && (
                        <div className="flex items-center gap-2 mt-2">
                          {activity.customer_name && (
                            <Badge variant="outline" className="text-[10px] border-surface-border">
                              {activity.customer_name}
                            </Badge>
                          )}
                          {activity.campaign_name && (
                            <Badge variant="outline" className="text-[10px] border-surface-border">
                              {activity.campaign_name}
                            </Badge>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
