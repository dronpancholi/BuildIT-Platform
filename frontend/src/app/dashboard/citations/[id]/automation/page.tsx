"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Bot,
  CheckCircle2,
  Globe,
  Loader2,
  PlayCircle,
  RefreshCw,
  Settings,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { SubmissionQueue } from "@/components/citations/submission-queue";
import { StatusBadge } from "@/components/citations/status-badge";
import { citationApi, type CitationProject, type CitationSubmission } from "@/lib/api";

export default function AutomationWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<CitationProject | null>(null);
  const [submissions, setSubmissions] = useState<CitationSubmission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [proj, subs] = await Promise.all([
        citationApi.getProject(projectId),
        citationApi.listSubmissions(projectId),
      ]);
      setProject(proj);
      setSubmissions(subs);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load project");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (projectId) loadData();
  }, [projectId]);

  if (isLoading) {
    return <LoadingSpinner size="lg" className="py-20" />;
  }

  if (error || !project) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="p-6 text-center">
          <p className="text-red-400">{error || "Project not found"}</p>
          <Button variant="outline" className="mt-4" onClick={() => router.back()}>
            <ArrowLeft className="w-4 h-4 mr-2" />
            Go Back
          </Button>
        </CardContent>
      </Card>
    );
  }

  const stats = {
    total: submissions.length,
    pending: submissions.filter((s) => s.status === "not_started" || s.status === "pending").length,
    inProgress: submissions.filter((s) => s.status === "in_progress").length,
    completed: submissions.filter(
      (s) => s.status === "already_exists" || s.status === "new_backlink"
    ).length,
    failed: submissions.filter((s) => s.status === "failed").length,
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`/dashboard/citations/${projectId}`)}
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-100 font-mono">
                AUTOMATION_WORKSPACE
              </h1>
              <Badge variant="outline" className="text-xs">
                Phase 2
              </Badge>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              {project.business_name} — Semi-automated form filling
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={loadData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-slate-200">{stats.total}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
              Total
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-slate-400">{stats.pending}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
              Pending
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-blue-400">{stats.inProgress}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
              In Progress
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-emerald-400">{stats.completed}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
              Completed
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-red-400">{stats.failed}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
              Failed
            </div>
          </CardContent>
        </Card>
      </div>

      {/* How it works */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Bot className="w-4 h-4" />
            How Semi-Auto Filling Works
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="w-10 h-10 rounded-full bg-platform-600/10 border border-platform-500/20 flex items-center justify-center mx-auto mb-2">
                <span className="text-platform-400 font-mono font-bold">1</span>
              </div>
              <p className="text-xs text-slate-400">Select submission from queue</p>
            </div>
            <div className="text-center">
              <div className="w-10 h-10 rounded-full bg-platform-600/10 border border-platform-500/20 flex items-center justify-center mx-auto mb-2">
                <span className="text-platform-400 font-mono font-bold">2</span>
              </div>
              <p className="text-xs text-slate-400">Browser navigates to site</p>
            </div>
            <div className="text-center">
              <div className="w-10 h-10 rounded-full bg-platform-600/10 border border-platform-500/20 flex items-center justify-center mx-auto mb-2">
                <span className="text-platform-400 font-mono font-bold">3</span>
              </div>
              <p className="text-xs text-slate-400">Auto-fill detects & fills fields</p>
            </div>
            <div className="text-center">
              <div className="w-10 h-10 rounded-full bg-platform-600/10 border border-platform-500/20 flex items-center justify-center mx-auto mb-2">
                <span className="text-platform-400 font-mono font-bold">4</span>
              </div>
              <p className="text-xs text-slate-400">Review & submit manually</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Submission Queue */}
      <SubmissionQueue submissions={submissions} onRefresh={loadData} />
    </div>
  );
}
