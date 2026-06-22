"use client";

import { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, getTenantId } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { formatDate } from "@/lib/utils";
import {
  AlertTriangle,
  Clock,
  FileWarning,
  Mail,
  CheckCircle,
  Lightbulb,
  Filter,
  Eye,
  EyeOff,
  Timer,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";

interface AttentionItem {
  id: string;
  type: string;
  priority: string;
  title: string;
  description: string | null;
  client_id: string | null;
  client_name: string | null;
  campaign_id: string | null;
  campaign_name: string | null;
  source: string;
  impact_score: number | null;
  due_date: string | null;
  actions_available: string[];
  entity_type: string | null;
  entity_id: string | null;
  created_at: string | null;
}

interface QuickStats {
  open_tasks: number;
  overdue_tasks: number;
  active_campaigns: number;
  pending_approvals: number;
  failed_citations: number;
  outreach_needing_action: number;
}

interface ActionCenterData {
  attention_items: AttentionItem[];
  summary: {
    total_items: number;
    by_type: Record<string, number>;
    by_priority: Record<string, number>;
    oldest_item_days: number;
    newest_item_hours: number;
  };
  quick_stats: QuickStats;
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  task: <Clock className="w-4 h-4" />,
  campaign_alert: <AlertTriangle className="w-4 h-4" />,
  citation_failure: <FileWarning className="w-4 h-4" />,
  outreach_followup: <Mail className="w-4 h-4" />,
  approval: <CheckCircle className="w-4 h-4" />,
  recommendation: <Lightbulb className="w-4 h-4" />,
};

const TYPE_LABELS: Record<string, string> = {
  task: "Task",
  campaign_alert: "Campaign Alert",
  citation_failure: "Citation Failure",
  outreach_followup: "Outreach Follow-up",
  approval: "Approval",
  recommendation: "Recommendation",
};

const PRIORITY_VARIANT: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
  P0: "destructive",
  P1: "warning",
  P2: "default",
  P3: "secondary",
};

const TYPE_FILTERS = [
  { label: "All", value: "" },
  { label: "Tasks", value: "task" },
  { label: "Campaign Alerts", value: "campaign_alert" },
  { label: "Citation Failures", value: "citation_failure" },
  { label: "Outreach", value: "outreach_followup" },
  { label: "Approvals", value: "approval" },
  { label: "Recommendations", value: "recommendation" },
] as const;

const PRIORITY_FILTERS = [
  { label: "All", value: "" },
  { label: "P0", value: "P0" },
  { label: "P1", value: "P1" },
  { label: "P2", value: "P2" },
  { label: "P3", value: "P3" },
] as const;

function PriorityBadge({ priority }: { priority: string }) {
  return (
    <Badge variant={PRIORITY_VARIANT[priority] || "outline"} className="text-xs font-mono">
      {priority}
    </Badge>
  );
}

function ImpactBar({ score }: { score: number }) {
  const color =
    score >= 80 ? "bg-red-500" : score >= 60 ? "bg-orange-500" : score >= 40 ? "bg-yellow-500" : "bg-green-500";
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 bg-surface-darker rounded-full h-1.5">
        <div className={`${color} h-1.5 rounded-full`} style={{ width: `${score}%` }} />
      </div>
      <span className="text-xs text-slate-400">{score}</span>
    </div>
  );
}

function StatCard({ label, value, icon, color }: { label: string; value: number; icon: React.ReactNode; color: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-slate-400 uppercase tracking-wider">{label}</p>
            <p className="text-2xl font-bold text-slate-100 mt-1">{value}</p>
          </div>
          <div className={`p-2 rounded-lg ${color}`}>{icon}</div>
        </div>
      </CardContent>
    </Card>
  );
}

function timeSince(dateStr: string | null): string {
  if (!dateStr) return "—";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffDays > 0) return `${diffDays}d ago`;
  if (diffHours > 0) return `${diffHours}h ago`;
  return "just now";
}

function timeUntil(dateStr: string | null): string {
  if (!dateStr) return "—";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = date.getTime() - now.getTime();
  if (diffMs < 0) return "overdue";
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffDays > 0) return `${diffDays}d left`;
  if (diffHours > 0) return `${diffHours}h left`;
  return "due now";
}

export default function ActionCenterPage() {
  const queryClient = useQueryClient();
  const [typeFilter, setTypeFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [clientFilter, setClientFilter] = useState("");
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, error } = useQuery<ActionCenterData>({
    queryKey: ["action-center", "dashboard"],
    queryFn: () => fetchApi("/action-center/dashboard"),
    refetchInterval: 30000,
  });

  const { data: clients } = useQuery({
    queryKey: ["clients"],
    queryFn: () => fetchApi("/clients"),
  });

  const ignoreMutation = useMutation({
    mutationFn: (body: { item_id: string; item_type: string }) =>
      fetchApi("/action-center/ignore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      toast.success("Item ignored");
      queryClient.invalidateQueries({ queryKey: ["action-center"] });
    },
    onError: () => toast.error("Failed to ignore item"),
  });

  const snoozeMutation = useMutation({
    mutationFn: (body: { item_id: string; item_type: string; snooze_until: string }) =>
      fetchApi("/action-center/snooze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      toast.success("Item snoozed");
      queryClient.invalidateQueries({ queryKey: ["action-center"] });
    },
    onError: () => toast.error("Failed to snooze item"),
  });

  const items = data?.attention_items || [];
  const stats = data?.quick_stats;
  const summary = data?.summary;

  const filteredItems = items.filter((item) => {
    if (typeFilter && item.type !== typeFilter) return false;
    if (priorityFilter && item.priority !== priorityFilter) return false;
    if (clientFilter && item.client_id !== clientFilter) return false;
    return true;
  });

  const clientList = (clients as any)?.data || [];
  const clientMap = new Map(clientList.map((c: any) => [c.id, c.name]));

  if (isLoading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <LoadingSpinner size="lg" className="py-20" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <Card className="border-red-500/20 bg-red-500/5">
          <CardContent className="py-8 text-center">
            <p className="text-red-400 text-sm">Failed to load action center. Please try again.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Action Center</h1>
          <p className="text-slate-400 mt-1">What needs your attention right now</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
          className={showFilters ? "border-blue-500/50 text-blue-400" : ""}
        >
          <Filter className="w-4 h-4 mr-2" />
          Filters
        </Button>
      </div>

      {/* Quick Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard
            label="Open Tasks"
            value={stats.open_tasks}
            icon={<Clock className="w-5 h-5 text-blue-400" />}
            color="bg-blue-500/10"
          />
          <StatCard
            label="Overdue"
            value={stats.overdue_tasks}
            icon={<AlertTriangle className="w-5 h-5 text-red-400" />}
            color="bg-red-500/10"
          />
          <StatCard
            label="Active Campaigns"
            value={stats.active_campaigns}
            icon={<RefreshCw className="w-5 h-5 text-green-400" />}
            color="bg-green-500/10"
          />
          <StatCard
            label="Pending Approvals"
            value={stats.pending_approvals}
            icon={<CheckCircle className="w-5 h-5 text-yellow-400" />}
            color="bg-yellow-500/10"
          />
          <StatCard
            label="Failed Citations"
            value={stats.failed_citations}
            icon={<FileWarning className="w-5 h-5 text-orange-400" />}
            color="bg-orange-500/10"
          />
          <StatCard
            label="Need Follow-up"
            value={stats.outreach_needing_action}
            icon={<Mail className="w-5 h-5 text-purple-400" />}
            color="bg-purple-500/10"
          />
        </div>
      )}

      {/* Filters */}
      {showFilters && (
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-wrap items-center gap-4">
              <div className="space-y-1">
                <label className="text-xs text-slate-400 uppercase tracking-wider">Type</label>
                <div className="flex items-center gap-1 bg-surface-darker border border-surface-border rounded-lg p-1">
                  {TYPE_FILTERS.map((f) => (
                    <button
                      key={f.value}
                      onClick={() => setTypeFilter(f.value)}
                      className={`px-2 py-1 text-xs font-medium rounded-md transition-all ${
                        typeFilter === f.value
                          ? "bg-surface-card text-slate-100 shadow-sm"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-slate-400 uppercase tracking-wider">Priority</label>
                <div className="flex items-center gap-1 bg-surface-darker border border-surface-border rounded-lg p-1">
                  {PRIORITY_FILTERS.map((f) => (
                    <button
                      key={f.value}
                      onClick={() => setPriorityFilter(f.value)}
                      className={`px-2 py-1 text-xs font-medium rounded-md transition-all ${
                        priorityFilter === f.value
                          ? "bg-surface-card text-slate-100 shadow-sm"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {f.label}
                    </button>
                  ))}
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-slate-400 uppercase tracking-wider">Client</label>
                <Select
                  placeholder="All clients"
                  options={clientList.map((c: any) => ({ label: c.name, value: c.id }))}
                  value={clientFilter}
                  onChange={(e) => setClientFilter(e.target.value)}
                  className="w-48"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Summary bar */}
      {summary && (
        <div className="flex items-center gap-6 text-sm text-slate-400">
          <span>{summary.total_items} items</span>
          {summary.oldest_item_days > 0 && (
            <span>Oldest: {summary.oldest_item_days}d</span>
          )}
          {summary.newest_item_hours >= 0 && (
            <span>Newest: {summary.newest_item_hours}h ago</span>
          )}
        </div>
      )}

      {/* Attention Items List */}
      {filteredItems.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
            <p className="text-lg font-medium text-slate-200">All clear!</p>
            <p className="text-sm text-slate-400 mt-1">No attention items match your filters.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {filteredItems.map((item) => (
            <Card key={`${item.type}-${item.id}`} className="hover:bg-surface-card/50 transition-colors">
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <div className="mt-0.5 text-slate-400">
                      {TYPE_ICONS[item.type] || <Clock className="w-4 h-4" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <PriorityBadge priority={item.priority} />
                        <span className="text-xs text-slate-500 uppercase tracking-wider">
                          {TYPE_LABELS[item.type] || item.type}
                        </span>
                      </div>
                      <p className="text-sm font-medium text-slate-200 mt-1 truncate">{item.title}</p>
                      {item.description && (
                        <p className="text-xs text-slate-400 mt-0.5 truncate">{item.description}</p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
                        {item.client_name && <span>{item.client_name}</span>}
                        {item.campaign_name && <span className="text-slate-600">/ {item.campaign_name}</span>}
                        {item.impact_score != null && <ImpactBar score={item.impact_score} />}
                        {item.due_date && (
                          <span className={timeUntil(item.due_date) === "overdue" ? "text-red-400" : ""}>
                            {timeUntil(item.due_date)}
                          </span>
                        )}
                        {item.created_at && <span>{timeSince(item.created_at)}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    {item.actions_available.includes("ignore") && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-slate-400 hover:text-slate-200"
                        onClick={() =>
                          ignoreMutation.mutate({ item_id: item.id, item_type: item.type })
                        }
                        disabled={ignoreMutation.isPending}
                        title="Ignore"
                      >
                        <EyeOff className="w-3.5 h-3.5" />
                      </Button>
                    )}
                    {item.actions_available.includes("snooze") && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 px-2 text-slate-400 hover:text-slate-200"
                        onClick={() => {
                          const tomorrow = new Date();
                          tomorrow.setDate(tomorrow.getDate() + 1);
                          snoozeMutation.mutate({
                            item_id: item.id,
                            item_type: item.type,
                            snooze_until: tomorrow.toISOString(),
                          });
                        }}
                        disabled={snoozeMutation.isPending}
                        title="Snooze 1 day"
                      >
                        <Timer className="w-3.5 h-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
