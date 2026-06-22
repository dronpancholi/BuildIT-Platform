"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  Clock,
  Mail,
  RefreshCw,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { VerificationPanel } from "@/components/citations/verification-panel";
import { StatusBadge } from "@/components/citations/status-badge";
import { citationApi, type CitationProject, type CitationSubmission } from "@/lib/api";

export default function VerificationWorkspacePage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<CitationProject | null>(null);
  const [submissions, setSubmissions] = useState<CitationSubmission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSubmission, setSelectedSubmission] = useState<CitationSubmission | null>(null);

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
      // Auto-select first unverified submission
      const unverified = subs.find((s) => !s.email_verified && s.status === "in_progress");
      if (unverified) setSelectedSubmission(unverified);
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
    verified: submissions.filter((s) => s.email_verified).length,
    pending: submissions.filter((s) => !s.email_verified && s.status === "in_progress").length,
    notStarted: submissions.filter((s) => s.status === "not_started" || s.status === "pending").length,
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
                EMAIL_VERIFICATION
              </h1>
              <Badge variant="outline" className="text-xs">
                Phase 3
              </Badge>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              {project.business_name} — Automated email verification
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={loadData}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
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
            <div className="text-2xl font-mono font-bold text-emerald-400">{stats.verified}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
              Verified
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-amber-400">{stats.pending}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
              Pending
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-slate-400">{stats.notStarted}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
              Not Started
            </div>
          </CardContent>
        </Card>
      </div>

      {/* How it works */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <Mail className="w-4 h-4" />
            How Email Verification Works
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="w-10 h-10 rounded-full bg-platform-600/10 border border-platform-500/20 flex items-center justify-center mx-auto mb-2">
                <span className="text-platform-400 font-mono font-bold">1</span>
              </div>
              <p className="text-xs text-slate-400">Connect to email inbox via IMAP</p>
            </div>
            <div className="text-center">
              <div className="w-10 h-10 rounded-full bg-platform-600/10 border border-platform-500/20 flex items-center justify-center mx-auto mb-2">
                <span className="text-platform-400 font-mono font-bold">2</span>
              </div>
              <p className="text-xs text-slate-400">Search for verification email</p>
            </div>
            <div className="text-center">
              <div className="w-10 h-10 rounded-full bg-platform-600/10 border border-platform-500/20 flex items-center justify-center mx-auto mb-2">
                <span className="text-platform-400 font-mono font-bold">3</span>
              </div>
              <p className="text-xs text-slate-400">Extract confirmation link</p>
            </div>
            <div className="text-center">
              <div className="w-10 h-10 rounded-full bg-platform-600/10 border border-platform-500/20 flex items-center justify-center mx-auto mb-2">
                <span className="text-platform-400 font-mono font-bold">4</span>
              </div>
              <p className="text-xs text-slate-400">Click link and confirm</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Main content: Submission list + Verification panel */}
      <div className="grid grid-cols-3 gap-6">
        {/* Submission List */}
        <Card className="col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
              Submissions ({submissions.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0 max-h-[500px] overflow-y-auto">
            {submissions.length === 0 ? (
              <div className="p-6 text-center">
                <p className="text-slate-500 text-sm">No submissions yet.</p>
              </div>
            ) : (
              <div>
                {submissions.map((sub) => (
                  <div
                    key={sub.id}
                    className={`flex items-center gap-3 px-4 py-3 cursor-pointer transition-colors border-b border-surface-border last:border-0 ${
                      selectedSubmission?.id === sub.id
                        ? "bg-platform-600/10 border-l-2 border-l-platform-500"
                        : "hover:bg-surface-darker/30"
                    }`}
                    onClick={() => setSelectedSubmission(sub)}
                  >
                    {sub.email_verified ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                    ) : (
                      <Clock className="w-4 h-4 text-slate-500 shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-slate-300 truncate">
                        {sub.site?.name || "Unknown Site"}
                      </p>
                      <p className="text-xs text-slate-500 truncate">
                        {sub.site?.url || ""}
                      </p>
                    </div>
                    <StatusBadge status={sub.status} />
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Verification Panel */}
        <div className="col-span-2">
          {selectedSubmission ? (
            <VerificationPanel
              submissionId={selectedSubmission.id}
              siteName={selectedSubmission.site?.name || "Unknown Site"}
              siteDomain={
                selectedSubmission.site?.url
                  ? new URL(selectedSubmission.site.url).hostname
                  : ""
              }
              emailVerified={selectedSubmission.email_verified}
              onVerified={loadData}
            />
          ) : (
            <Card>
              <CardContent className="p-8 text-center">
                <Mail className="w-8 h-8 text-slate-600 mx-auto" />
                <p className="text-slate-500 text-sm mt-2">
                  Select a submission to verify its email
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
