"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Mail, Reply, Clock, AlertCircle, CheckCircle, Forward } from "lucide-react";

const MailOpen = Mail;
const MailReply = Reply;
const MailForward = Forward;
import { cn } from "@/lib/utils";
import { formatDistanceToNow } from "date-fns";

interface CommunicationFeedProps {
  className?: string;
}

interface Communication {
  id: string;
  type: "draft" | "scheduled" | "sent" | "reply" | "failed";
  subject?: string;
  recipient?: string;
  prospect_name?: string;
  status: string;
  created_at: string;
  scheduled_at?: string;
  sent_at?: string;
  metadata?: any;
}

export function CommunicationFeed({ className }: CommunicationFeedProps) {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["communications-feed"],
    queryFn: () => fetchApi("/campaigns/threads/all"),
    refetchInterval: 15000,
  });

  // Transform thread data to communication format
  const threads = data?.data || [];
  const communications: any[] = threads.map((t: any) => ({
    id: t.id,
    type: t.status === 'replied' ? 'reply' : t.status === 'link_acquired' ? 'sent' : 'draft',
    subject: t.subject,
    recipient: t.to_email,
    prospect_name: t.prospect_name,
    status: t.status,
    created_at: t.created_at,
    sent_at: t.sent_at,
    campaign_name: t.campaign_name,
  }));

  const getStatusIcon = (type: string, status?: string) => {
    switch (type) {
      case "draft":
        return <Mail className="w-4 h-4 text-slate-400" />;
      case "scheduled":
        return <Clock className="w-4 h-4 text-blue-400" />;
      case "sent":
        return <MailOpen className="w-4 h-4 text-emerald-400" />;
      case "reply":
        return <MailReply className="w-4 h-4 text-purple-400" />;
      case "failed":
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return <MailForward className="w-4 h-4 text-slate-400" />;
    }
  };

  const getStatusBadge = (comm: Communication) => {
    switch (comm.type) {
      case "draft":
        return "bg-slate-500/10 text-slate-400";
      case "scheduled":
        return "bg-blue-500/10 text-blue-400";
      case "sent":
        return "bg-emerald-500/10 text-emerald-400";
      case "reply":
        return "bg-purple-500/10 text-purple-400";
      case "failed":
        return "bg-red-500/10 text-red-400";
      default:
        return "bg-slate-500/10 text-slate-400";
    }
  };

  return (
    <Card className={cn("bg-surface-card border-surface-border", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-slate-400">Communication Feed</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-platform-500"></div>
          </div>
        ) : communications.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            No communications yet
          </div>
        ) : (
          <div className="space-y-3">
            {communications.map((comm: any) => (
              <div
                key={comm.id}
                className="p-4 rounded-lg bg-surface-darker border border-surface-border hover:border-platform-500/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-surface-darker">
                      {getStatusIcon(comm.type, comm.status)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-sm font-medium text-slate-200">
                          {comm.subject || "No Subject"}
                        </h4>
                        <Badge
                          variant="outline"
                          className={cn("text-[10px] border-0", getStatusBadge(comm))}
                        >
                          {comm.type}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500">
                        {comm.prospect_name 
                          ? `To: ${comm.prospect_name}` 
                          : comm.recipient 
                          ? `To: ${comm.recipient}`
                          : "No recipient"}
                      </p>
                      {comm.campaign_name && (
                        <p className="text-xs text-slate-600 mt-1">{comm.campaign_name}</p>
                      )}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-4 text-xs text-slate-500">
                  <div className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    <span>
                      {formatDistanceToNow(new Date(comm.created_at), { addSuffix: true })}
                    </span>
                  </div>
                  {comm.scheduled_at && (
                    <div className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>Scheduled: {formatDistanceToNow(new Date(comm.scheduled_at), { addSuffix: true })}</span>
                    </div>
                  )}
                  {comm.sent_at && (
                    <div className="flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      <span>Sent: {formatDistanceToNow(new Date(comm.sent_at), { addSuffix: true })}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
