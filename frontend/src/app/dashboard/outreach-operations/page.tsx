"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useApiDetail, useApiCreate } from "@/services/hooks";
import { ENDPOINTS } from "@/services/endpoints";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDate } from "@/lib/utils";
import {
  Search,
  Mail,
  AlertTriangle,
  CheckCircle,
  Clock,
  Send,
  Reply,
  BarChart3,
} from "lucide-react";

interface OutreachDashboardData {
  total_threads: number;
  by_status: Record<string, number>;
  response_rate: number;
  reply_rate: number;
  needs_followup_count: number;
  needs_followup_threads: ThreadSummary[];
  recent_activity: RecentActivity[];
}

interface ThreadSummary {
  id: string;
  prospect_domain: string | null;
  to_email: string;
  subject: string;
  status: string;
  follow_up_count: number;
  max_follow_ups: number;
  sent_at: string | null;
  replied_at: string | null;
  days_since_sent: number | null;
  needs_followup: boolean;
  campaign_id: string;
  campaign_name: string | null;
}

interface RecentActivity {
  id: string;
  to_email: string;
  subject: string;
  status: string;
  campaign_name: string | null;
  updated_at: string | null;
}

interface BulkFollowUpResult {
  tasks_created: number;
  thread_ids: string[];
}

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
  draft: "outline",
  queued: "secondary",
  sent: "default",
  delivered: "default",
  opened: "warning",
  replied: "success",
  link_acquired: "success",
  failed: "destructive",
  cancelled: "destructive",
};

const STATUS_ICONS: Record<string, string> = {
  draft: "📝",
  queued: "📬",
  sent: "📤",
  opened: "👁️",
  replied: "💬",
  link_acquired: "🔗",
  failed: "❌",
};

export default function OutreachOperationsPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");

  const { data: dashboard, isLoading, error } = useApiDetail<OutreachDashboardData>(
    ENDPOINTS.OUTREACH_OPERATIONS,
    "dashboard"
  );

  const bulkFollowUp = useApiCreate<BulkFollowUpResult, void>(
    `${ENDPOINTS.OUTREACH_OPERATIONS}/bulk-follow-up`,
    {
      invalidateKeys: [ENDPOINTS.OUTREACH_OPERATIONS],
      successMessage: "Follow-up tasks created successfully",
    }
  );

  const threads = dashboard?.needs_followup_threads || [];
  const recentActivity = dashboard?.recent_activity || [];

  const filteredThreads = searchQuery
    ? threads.filter(
        (t) =>
          t.to_email.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (t.prospect_domain && t.prospect_domain.toLowerCase().includes(searchQuery.toLowerCase())) ||
          t.subject.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : threads;

  if (isLoading) {
    return <LoadingSpinner size="lg" className="py-20" />;
  }

  if (error) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="py-8 text-center">
          <p className="text-red-400 text-sm">Failed to load outreach operations. Please try again.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Outreach Operations</h1>
          <p className="text-slate-400 mt-1">Track threads, response rates, and follow-ups</p>
        </div>
        <Button
          onClick={() => bulkFollowUp.mutate(undefined as never)}
          disabled={bulkFollowUp.isPending || (dashboard?.needs_followup_count || 0) === 0}
          className="gap-2"
        >
          <Send className="w-4 h-4" />
          {bulkFollowUp.isPending ? "Creating..." : `Bulk Follow-up (${dashboard?.needs_followup_count || 0})`}
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <Mail className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{dashboard?.total_threads || 0}</p>
                <p className="text-xs text-slate-400">Total Threads</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/10 rounded-lg">
                <Reply className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">
                  {dashboard ? `${(dashboard.response_rate * 100).toFixed(1)}%` : "0%"}
                </p>
                <p className="text-xs text-slate-400">Response Rate</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{dashboard?.needs_followup_count || 0}</p>
                <p className="text-xs text-slate-400">Needs Follow-up</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-slate-500/10 rounded-lg">
                <BarChart3 className="w-5 h-5 text-slate-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">
                  {dashboard ? `${(dashboard.reply_rate * 100).toFixed(1)}%` : "0%"}
                </p>
                <p className="text-xs text-slate-400">Reply Rate</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Status Breakdown */}
      {dashboard?.by_status && Object.keys(dashboard.by_status).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-slate-200">Status Breakdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {Object.entries(dashboard.by_status).map(([status, count]) => (
                <div
                  key={status}
                  className="flex items-center gap-2 px-3 py-2 bg-surface-darker/50 rounded-lg"
                >
                  <span className="text-sm">{STATUS_ICONS[status] || "📌"}</span>
                  <span className="text-sm text-slate-300 capitalize">{status.replace(/_/g, " ")}</span>
                  <Badge variant={STATUS_VARIANT[status] || "outline"} className="ml-1">
                    {count}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Needs Follow-up Section */}
      {threads.length > 0 && (
        <Card className="border-amber-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
              Needs Follow-up ({threads.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative max-w-sm mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                placeholder="Search threads..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="space-y-2">
              {filteredThreads.map((thread) => (
                <div
                  key={thread.id}
                  onClick={() => router.push(`/dashboard/outreach-operations?thread=${thread.id}`)}
                  className="flex items-center justify-between p-3 bg-surface-darker/50 rounded-lg border border-surface-border hover:border-amber-500/30 cursor-pointer transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant={STATUS_VARIANT[thread.status] || "outline"} className="text-xs">
                        {thread.status}
                      </Badge>
                      <span className="text-xs text-slate-500">
                        Follow-up #{thread.follow_up_count + 1}/{thread.max_follow_ups}
                      </span>
                    </div>
                    <p className="text-sm text-slate-200 truncate">{thread.subject}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {thread.to_email}
                      {thread.prospect_domain && ` — ${thread.prospect_domain}`}
                    </p>
                  </div>
                  <div className="text-right ml-4 shrink-0">
                    <p className="text-xs text-amber-400 font-medium">
                      {thread.days_since_sent}d ago
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {thread.campaign_name || "No campaign"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {threads.length === 0 && (
        <EmptyState
          icon={<CheckCircle className="w-8 h-8" />}
          title="No threads need follow-up"
          description="All outreach threads are up to date."
        />
      )}

      {/* Recent Activity */}
      {recentActivity.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-slate-200">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recentActivity.slice(0, 15).map((event) => (
                <div
                  key={event.id}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-darker/30 cursor-pointer"
                  onClick={() => router.push(`/dashboard/outreach-operations?thread=${event.id}`)}
                >
                  <div
                    className={`w-2 h-2 rounded-full shrink-0 ${
                      event.status === "replied" || event.status === "link_acquired"
                        ? "bg-green-400"
                        : event.status === "failed"
                        ? "bg-red-400"
                        : event.status === "opened"
                        ? "bg-amber-400"
                        : "bg-blue-400"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 truncate">{event.subject}</p>
                    <p className="text-xs text-slate-500">
                      {event.to_email}
                      {event.campaign_name && ` — ${event.campaign_name}`}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <Badge variant={STATUS_VARIANT[event.status] || "outline"} className="text-xs">
                      {event.status}
                    </Badge>
                    <p className="text-xs text-slate-500 mt-1">
                      {event.updated_at ? formatDate(event.updated_at) : "—"}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
