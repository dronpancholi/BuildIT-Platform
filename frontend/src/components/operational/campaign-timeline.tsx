"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import {
  GitBranch, Search, Target, Mail, Reply, Calendar,
  Link2, FileText, CheckCircle2, Clock, Loader2,
} from "lucide-react";

interface TimelineEvent {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  icon: string;
  color: string;
}

interface ThreadData {
  id: string;
  status: string;
  subject: string;
  prospect_domain: string;
  sent_at: string | null;
  replied_at: string | null;
  created_at: string | null;
  follow_up_count: number;
  ai_personalization: Record<string, unknown>;
}

interface CampaignData {
  id: string;
  name: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  started_at: string | null;
  completed_at: string | null;
}

interface AcquiredLink {
  id: string;
  source_url: string;
  anchor_text: string;
  first_verified_at: string | null;
  created_at: string | null;
}

function TimelineIcon({ type }: { type: string }) {
  const config: Record<string, { icon: any; color: string }> = {
    campaign_created: { icon: GitBranch, color: "text-platform-400" },
    keyword_discovery: { icon: Search, color: "text-emerald-400" },
    prospect_discovery: { icon: Target, color: "text-amber-400" },
    email_generated: { icon: Mail, color: "text-blue-400" },
    email_sent: { icon: Mail, color: "text-indigo-400" },
    reply_received: { icon: Reply, color: "text-cyan-400" },
    follow_up_sent: { icon: Calendar, color: "text-orange-400" },
    link_acquired: { icon: Link2, color: "text-purple-400" },
    report_generated: { icon: FileText, color: "text-slate-400" },
  };
  const { icon: Icon, color } = config[type] || { icon: Clock, color: "text-slate-500" };
  return <Icon className={`w-4 h-4 ${color}`} />;
}

export function CampaignTimeline({ campaignId }: { campaignId: string }) {
  const { data: campaign } = useQuery<CampaignData>({
    queryKey: ["campaign", campaignId],
    queryFn: () => fetchApi(`/campaigns/${campaignId}?tenant_id=${MOCK_TENANT_ID}`),
  });

  const { data: threads = [] } = useQuery<ThreadData[]>({
    queryKey: ["campaign-threads", campaignId],
    queryFn: () => fetchApi(`/campaigns/${campaignId}/threads?tenant_id=${MOCK_TENANT_ID}`),
  });

  const { data: savedReports = [] } = useQuery<any[]>({
    queryKey: ["reports-list"],
    queryFn: () => fetchApi(`/reports?tenant_id=${MOCK_TENANT_ID}`),
  });

  const events: TimelineEvent[] = [];

  if (campaign?.created_at) {
    events.push({
      id: `campaign-${campaignId}`,
      type: "campaign_created",
      title: "Campaign Created",
      description: campaign.name,
      timestamp: campaign.created_at,
      icon: "campaign_created",
      color: "text-platform-400",
    });
  }

  if (campaign?.started_at) {
    events.push({
      id: `started-${campaignId}`,
      type: "campaign_created",
      title: "Campaign Started",
      description: "Prospect discovery initiated",
      timestamp: campaign.started_at,
      icon: "campaign_created",
      color: "text-emerald-400",
    });
  }

  for (const thread of threads) {
    if (thread.created_at) {
      events.push({
        id: `email-gen-${thread.id}`,
        type: "email_generated",
        title: "Email Generated",
        description: `Draft for ${thread.prospect_domain}`,
        timestamp: thread.created_at,
        icon: "email_generated",
        color: "text-blue-400",
      });
    }

    if (thread.sent_at) {
      events.push({
        id: `email-sent-${thread.id}`,
        type: "email_sent",
        title: "Email Sent",
        description: `Sent to ${thread.prospect_domain}`,
        timestamp: thread.sent_at,
        icon: "email_sent",
        color: "text-indigo-400",
      });
    }

    if (thread.replied_at) {
      events.push({
        id: `reply-${thread.id}`,
        type: "reply_received",
        title: "Reply Received",
        description: `Reply from ${thread.prospect_domain}`,
        timestamp: thread.replied_at,
        icon: "reply_received",
        color: "text-cyan-400",
      });
    }

    if (thread.follow_up_count > 0) {
      events.push({
        id: `followup-${thread.id}`,
        type: "follow_up_sent",
        title: "Follow-Up Sent",
        description: `${thread.follow_up_count} follow-up(s) to ${thread.prospect_domain}`,
        timestamp: thread.sent_at || thread.created_at || new Date().toISOString(),
        icon: "follow_up_sent",
        color: "text-orange-400",
      });
    }

    if (thread.status === "link_acquired" && thread.ai_personalization?.link_acquired_at) {
      events.push({
        id: `link-${thread.id}`,
        type: "link_acquired",
        title: "Link Acquired",
        description: `Backlink from ${thread.prospect_domain}`,
        timestamp: thread.ai_personalization.link_acquired_at as string,
        icon: "link_acquired",
        color: "text-purple-400",
      });
    }
  }

  events.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  if (events.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-slate-600">
        <Clock className="w-5 h-5 mb-2" />
        <span className="text-[10px] font-mono">No events yet. Campaign activity will appear here.</span>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {events.map((event, i) => (
        <div key={event.id} className="flex gap-3">
          <div className="flex flex-col items-center">
            <div className={`w-8 h-8 rounded-full bg-surface-darker border border-surface-border flex items-center justify-center flex-shrink-0 ${event.color}`}>
              <TimelineIcon type={event.type} />
            </div>
            {i < events.length - 1 && (
              <div className="w-px h-full bg-surface-border min-h-[24px]" />
            )}
          </div>
          <div className="pb-6 flex-1">
            <p className="text-xs font-medium text-slate-200">{event.title}</p>
            <p className="text-[10px] text-slate-500 mt-0.5">{event.description}</p>
            <p className="text-[9px] font-mono text-slate-600 mt-1">
              {new Date(event.timestamp).toLocaleString()}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
