"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useApiDetail, useApiCreate } from "@/services/hooks";
import { ENDPOINTS } from "@/services/endpoints";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { formatDate } from "@/lib/utils";
import {
  ArrowLeft,
  Activity,
  Heart,
  CheckSquare,
  Mail,
  Globe,
  Clock,
  Lightbulb,
  ChevronRight,
  Plus,
  AlertTriangle,
  Target,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";

interface CampaignDashboardData {
  campaign: {
    id: string;
    name: string;
    status: string;
    type: string;
    client_name: string | null;
    created_at: string | null;
    updated_at: string | null;
  };
  objectives: {
    target_links: number;
    acquired_links: number;
    progress_pct: number;
    days_active: number;
    velocity: string;
  };
  health: {
    score: number;
    tier: string;
    momentum: number;
    velocity: number;
    components: {
      outreach: number;
      freshness: number;
      keywords: number;
      operations: number;
    };
  };
  tasks: {
    total: number;
    by_status: Record<string, number>;
    overdue: number;
    recent: TaskItem[];
  };
  outreach: {
    threads: number;
    by_status: Record<string, number>;
    response_rate: number;
    needs_followup: number;
  };
  citations: {
    total_submissions: number;
    by_status: Record<string, number>;
  };
  timeline: TimelineEvent[];
  recommendations: RecommendationItem[];
  next_actions: string[];
}

interface TaskItem {
  id: string;
  title: string;
  status: string;
  priority: string;
  assigned_to: string | null;
  due_date: string | null;
  created_at: string | null;
}

interface TimelineEvent {
  id: string;
  step_name: string;
  status: string;
  message: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

interface RecommendationItem {
  id: string;
  type: string;
  title: string;
  description: string;
  priority: string;
  impact_score: number;
}

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
  active: "success",
  paused: "warning",
  complete: "secondary",
  draft: "outline",
  cancelled: "destructive",
  monitoring: "default",
  archived: "secondary",
  created: "outline",
  in_progress: "default",
  completed: "success",
  blocked: "destructive",
};

function HealthGauge({ score, tier }: { score: number; tier: string }) {
  const color =
    score >= 0.85
      ? "text-green-400"
      : score >= 0.7
      ? "text-blue-400"
      : score >= 0.5
      ? "text-amber-400"
      : "text-red-400";

  return (
    <div className="flex flex-col items-center">
      <div className="relative w-24 h-24">
        <svg className="w-24 h-24 transform -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="40"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            className="text-surface-darker"
          />
          <circle
            cx="50"
            cy="50"
            r="40"
            stroke="currentColor"
            strokeWidth="8"
            fill="none"
            strokeDasharray={`${score * 251.2} 251.2`}
            className={color}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={`text-xl font-bold ${color}`}>{Math.round(score * 100)}</span>
        </div>
      </div>
      <Badge variant={score >= 0.7 ? "success" : score >= 0.5 ? "warning" : "destructive"} className="mt-2">
        {tier}
      </Badge>
    </div>
  );
}

function ProgressBar({ acquired, target }: { acquired: number; target: number }) {
  const pct = target > 0 ? Math.round((acquired / target) * 100) : 0;
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{acquired} / {target} links</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full bg-surface-darker rounded-full h-3">
        <div
          className="bg-blue-500 h-3 rounded-full transition-all"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function CampaignOperationsDetailPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params.id as string;
  const [showCreateTask, setShowCreateTask] = useState(false);
  const [taskForm, setTaskForm] = useState({
    title: "",
    description: "",
    priority: "P1",
    assigned_to: "",
  });

  const { data: dashboard, isLoading, error } = useApiDetail<CampaignDashboardData>(
    `${ENDPOINTS.CAMPAIGN_OPERATIONS}/${campaignId}`,
    "dashboard"
  );

  const createTaskMutation = useApiCreate(`${ENDPOINTS.CAMPAIGN_OPERATIONS}/${campaignId}`, {
    invalidateKeys: [`${ENDPOINTS.CAMPAIGN_OPERATIONS}/${campaignId}`],
    successMessage: "Task created successfully",
  });

  const handleCreateTask = () => {
    createTaskMutation.mutate(
      {
        action: "create-task",
        ...taskForm,
        assigned_to: taskForm.assigned_to || undefined,
      } as any,
      {
        onSuccess: () => {
          setShowCreateTask(false);
          setTaskForm({ title: "", description: "", priority: "P1", assigned_to: "" });
        },
      }
    );
  };

  if (isLoading) {
    return <LoadingSpinner size="lg" className="py-20" />;
  }

  if (error || !dashboard) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="py-8 text-center">
          <p className="text-red-400 text-sm">Failed to load campaign operations.</p>
          <Button variant="outline" className="mt-4" onClick={() => router.back()}>
            Go Back
          </Button>
        </CardContent>
      </Card>
    );
  }

  const { campaign, objectives, health, tasks, outreach, citations, timeline, recommendations, next_actions } =
    dashboard;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => router.push("/dashboard/campaign-operations")}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-slate-100">{campaign.name}</h1>
            <Badge variant={STATUS_VARIANT[campaign.status] || "outline"}>{campaign.status}</Badge>
          </div>
          <p className="text-slate-400 mt-1">
            {campaign.client_name || "No client"} · {campaign.type?.replace(/_/g, " ")}
          </p>
        </div>
        <div className="text-right text-xs text-slate-500">
          <p>Created: {formatDate(campaign.created_at)}</p>
          <p>Updated: {formatDate(campaign.updated_at)}</p>
        </div>
      </div>

      {/* Objectives + Health Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Target className="w-4 h-4" />
              Objectives
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ProgressBar acquired={objectives.acquired_links} target={objectives.target_links} />
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-bold text-slate-100">{objectives.days_active}</p>
                <p className="text-xs text-slate-400">Days Active</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{objectives.velocity}</p>
                <p className="text-xs text-slate-400">Velocity</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{objectives.progress_pct}%</p>
                <p className="text-xs text-slate-400">Progress</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Heart className="w-4 h-4" />
              Health
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center">
            <HealthGauge score={health.score} tier={health.tier} />
            <div className="grid grid-cols-2 gap-2 mt-4 w-full text-xs">
              <div className="text-center p-2 bg-surface-darker rounded">
                <p className="text-slate-200">{health.momentum.toFixed(1)}</p>
                <p className="text-slate-500">Momentum</p>
              </div>
              <div className="text-center p-2 bg-surface-darker rounded">
                <p className="text-slate-200">{health.velocity.toFixed(1)}</p>
                <p className="text-slate-500">Velocity</p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2 w-full text-xs">
              {Object.entries(health.components).map(([key, val]) => (
                <div key={key} className="text-center p-2 bg-surface-darker/50 rounded">
                  <p className="text-slate-300">{Math.round((val as number) * 100)}%</p>
                  <p className="text-slate-500 capitalize">{key}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Next Actions */}
      {next_actions.length > 0 && (
        <Card className="border-blue-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-blue-400">
              <ChevronRight className="w-4 h-4" />
              Next Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {next_actions.map((action, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 p-2 rounded-lg bg-blue-500/5 border border-blue-500/10"
                >
                  <span className="text-blue-400 text-sm mt-0.5">{idx + 1}.</span>
                  <p className="text-sm text-slate-300">{action}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tasks + Outreach Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <CheckSquare className="w-4 h-4" />
              Tasks ({tasks.total})
            </CardTitle>
            <Button variant="outline" size="sm" onClick={() => setShowCreateTask(true)}>
              <Plus className="w-3 h-3 mr-1" />
              Add Task
            </Button>
          </CardHeader>
          <CardContent>
            {tasks.overdue > 0 && (
              <div className="flex items-center gap-2 p-2 mb-3 bg-red-500/10 rounded-lg border border-red-500/20">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <span className="text-sm text-red-400">{tasks.overdue} overdue task(s)</span>
              </div>
            )}
            <div className="flex gap-2 mb-3 flex-wrap">
              {Object.entries(tasks.by_status).map(([status, count]) => (
                <Badge key={status} variant={STATUS_VARIANT[status] || "outline"} className="text-xs">
                  {status}: {count}
                </Badge>
              ))}
            </div>
            <div className="space-y-2">
              {tasks.recent.map((task) => (
                <div
                  key={task.id}
                  className="flex items-center justify-between p-2 rounded-lg bg-surface-darker/30 hover:bg-surface-darker/50"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200 truncate">{task.title}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Badge variant={STATUS_VARIANT[task.status] || "outline"} className="text-xs">
                        {task.status}
                      </Badge>
                      <Badge variant="outline" className="text-xs">{task.priority}</Badge>
                      {task.assigned_to && (
                        <span className="text-xs text-slate-500">{task.assigned_to}</span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {tasks.recent.length === 0 && (
                <p className="text-sm text-slate-500 text-center py-4">No tasks yet</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Mail className="w-4 h-4" />
              Outreach
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4 text-center">
              <div className="p-3 bg-surface-darker rounded-lg">
                <p className="text-2xl font-bold text-slate-100">{outreach.threads}</p>
                <p className="text-xs text-slate-400">Total Threads</p>
              </div>
              <div className="p-3 bg-surface-darker rounded-lg">
                <p className="text-2xl font-bold text-slate-100">
                  {Math.round(outreach.response_rate * 100)}%
                </p>
                <p className="text-xs text-slate-400">Response Rate</p>
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              {Object.entries(outreach.by_status).map(([status, count]) => (
                <Badge key={status} variant={STATUS_VARIANT[status] || "outline"} className="text-xs">
                  {status}: {count}
                </Badge>
              ))}
            </div>
            {outreach.needs_followup > 0 && (
              <div className="flex items-center gap-2 p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                <Clock className="w-4 h-4 text-amber-400" />
                <span className="text-sm text-amber-400">
                  {outreach.needs_followup} thread(s) need follow-up
                </span>
              </div>
            )}
            {citations.total_submissions > 0 && (
              <div className="pt-3 border-t border-surface-border">
                <p className="text-xs text-slate-400 mb-2">Citations</p>
                <div className="flex gap-2 flex-wrap">
                  {Object.entries(citations.by_status).map(([status, count]) => (
                    <Badge key={status} variant="outline" className="text-xs">
                      {status}: {count}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recommendations */}
      {recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Lightbulb className="w-4 h-4" />
              Recommendations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {recommendations.map((rec) => (
                <div
                  key={rec.id}
                  className="flex items-start gap-3 p-3 rounded-lg bg-surface-darker/30"
                >
                  <Badge
                    variant={rec.priority === "P0" ? "destructive" : rec.priority === "P1" ? "warning" : "outline"}
                    className="text-xs shrink-0"
                  >
                    {rec.priority}
                  </Badge>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200">{rec.title}</p>
                    <p className="text-xs text-slate-400 mt-1 line-clamp-2">{rec.description}</p>
                  </div>
                  <span className="text-xs text-slate-500 shrink-0">
                    Impact: {Math.round(rec.impact_score * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Timeline */}
      {timeline.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Activity className="w-4 h-4" />
              Timeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {timeline.map((event) => (
                <div key={event.id} className="flex items-start gap-3">
                  <div
                    className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${
                      event.status === "completed"
                        ? "bg-green-400"
                        : event.status === "failed"
                        ? "bg-red-400"
                        : event.status === "running"
                        ? "bg-blue-400 animate-pulse"
                        : "bg-slate-500"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300">{event.message || event.step_name}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{formatDate(event.timestamp)}</p>
                  </div>
                  <Badge variant={event.status === "completed" ? "success" : "outline"} className="text-xs shrink-0">
                    {event.status}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create Task Dialog */}
      <Dialog open={showCreateTask} onOpenChange={setShowCreateTask}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Task</DialogTitle>
            <DialogDescription>Add a new task for this campaign</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="task-title">Title</Label>
              <Input
                id="task-title"
                placeholder="e.g., Follow up with prospect"
                value={taskForm.title}
                onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="task-desc">Description</Label>
              <Textarea
                id="task-desc"
                placeholder="Optional details..."
                value={taskForm.description}
                onChange={(e) => setTaskForm({ ...taskForm, description: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="task-priority">Priority</Label>
                <Select
                  id="task-priority"
                  options={[
                    { label: "P0", value: "P0" },
                    { label: "P1", value: "P1" },
                    { label: "P2", value: "P2" },
                    { label: "P3", value: "P3" },
                  ]}
                  value={taskForm.priority}
                  onChange={(e) => setTaskForm({ ...taskForm, priority: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="task-assignee">Assign To</Label>
                <Input
                  id="task-assignee"
                  placeholder="Email or name"
                  value={taskForm.assigned_to}
                  onChange={(e) => setTaskForm({ ...taskForm, assigned_to: e.target.value })}
                />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateTask(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreateTask}
              disabled={!taskForm.title || createTaskMutation.isPending}
            >
              {createTaskMutation.isPending ? "Creating..." : "Create Task"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
