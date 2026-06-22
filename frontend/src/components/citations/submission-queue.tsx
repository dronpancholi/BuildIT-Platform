"use client";

import { useState } from "react";
import {
  CheckCircle2,
  Clock,
  Globe,
  Loader2,
  Play,
  PlayCircle,
  RotateCcw,
  Square,
  Trash2,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StatusBadge } from "./status-badge";
import { AutoFillModal } from "./auto-fill-modal";
import type { CitationSubmission } from "@/lib/api";

interface SubmissionQueueProps {
  submissions: CitationSubmission[];
  onRefresh: () => void;
}

export function SubmissionQueue({ submissions, onRefresh }: SubmissionQueueProps) {
  const [selectedSubmission, setSelectedSubmission] = useState<CitationSubmission | null>(null);
  const [showAutoFill, setShowAutoFill] = useState(false);
  const [isRunningBatch, setIsRunningBatch] = useState(false);
  const [batchProgress, setBatchProgress] = useState<{ current: number; total: number } | null>(null);

  const pendingSubmissions = submissions.filter(
    (s) => s.status === "not_started" || s.status === "pending"
  );
  const inProgressSubmissions = submissions.filter((s) => s.status === "in_progress");
  const completedSubmissions = submissions.filter(
    (s) => s.status === "already_exists" || s.status === "new_backlink"
  );
  const failedSubmissions = submissions.filter((s) => s.status === "failed");

  const handleAutoFill = (submission: CitationSubmission) => {
    setSelectedSubmission(submission);
    setShowAutoFill(true);
  };

  const handleRunBatch = async () => {
    if (pendingSubmissions.length === 0) return;

    try {
      setIsRunningBatch(true);
      setBatchProgress({ current: 0, total: pendingSubmissions.length });

      // In production, this would call the batch API
      // For now, we auto-fill one by one
      for (let i = 0; i < pendingSubmissions.length; i++) {
        setBatchProgress({ current: i + 1, total: pendingSubmissions.length });
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }

      setBatchProgress(null);
      onRefresh();
    } catch (err) {
      console.error("Batch failed:", err);
    } finally {
      setIsRunningBatch(false);
      setBatchProgress(null);
    }
  };

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
              Submission Queue ({submissions.length})
            </CardTitle>
            <div className="flex items-center gap-2">
              {batchProgress && (
                <span className="text-xs text-slate-500">
                  {batchProgress.current}/{batchProgress.total}
                </span>
              )}
              <Button
                size="sm"
                onClick={handleRunBatch}
                disabled={isRunningBatch || pendingSubmissions.length === 0}
              >
                {isRunningBatch ? (
                  <Loader2 className="w-4 h-4 mr-1 animate-spin" />
                ) : (
                  <PlayCircle className="w-4 h-4 mr-1" />
                )}
                Run Queue
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {/* Pending */}
          {pendingSubmissions.length > 0 && (
            <div className="border-b border-surface-border">
              <div className="px-4 py-2 bg-surface-darker/50">
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                  Pending ({pendingSubmissions.length})
                </span>
              </div>
              {pendingSubmissions.map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-surface-darker/30 transition-colors border-b border-surface-border last:border-0"
                >
                  <Clock className="w-4 h-4 text-slate-500 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 truncate">
                      {sub.site?.name || "Unknown Site"}
                    </p>
                    <p className="text-xs text-slate-500 truncate">
                      {sub.site?.url || ""}
                    </p>
                  </div>
                  <StatusBadge status={sub.status} />
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleAutoFill(sub)}
                  >
                    <Play className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* In Progress */}
          {inProgressSubmissions.length > 0 && (
            <div className="border-b border-surface-border">
              <div className="px-4 py-2 bg-surface-darker/50">
                <span className="text-[10px] font-mono uppercase tracking-wider text-blue-400">
                  In Progress ({inProgressSubmissions.length})
                </span>
              </div>
              {inProgressSubmissions.map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-surface-darker/30 transition-colors border-b border-surface-border last:border-0"
                >
                  <Loader2 className="w-4 h-4 text-blue-400 shrink-0 animate-spin" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 truncate">
                      {sub.site?.name || "Unknown Site"}
                    </p>
                    <p className="text-xs text-slate-500 truncate">
                      {sub.site?.url || ""}
                    </p>
                  </div>
                  <StatusBadge status={sub.status} />
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleAutoFill(sub)}
                  >
                    <Play className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* Completed */}
          {completedSubmissions.length > 0 && (
            <div className="border-b border-surface-border">
              <div className="px-4 py-2 bg-surface-darker/50">
                <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400">
                  Completed ({completedSubmissions.length})
                </span>
              </div>
              {completedSubmissions.map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-surface-darker/30 transition-colors border-b border-surface-border last:border-0"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 truncate">
                      {sub.site?.name || "Unknown Site"}
                    </p>
                    {sub.listing_url && (
                      <a
                        href={sub.listing_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-platform-400 hover:underline truncate block"
                      >
                        {sub.listing_url}
                      </a>
                    )}
                  </div>
                  <StatusBadge status={sub.status} />
                </div>
              ))}
            </div>
          )}

          {/* Failed */}
          {failedSubmissions.length > 0 && (
            <div>
              <div className="px-4 py-2 bg-surface-darker/50">
                <span className="text-[10px] font-mono uppercase tracking-wider text-red-400">
                  Failed ({failedSubmissions.length})
                </span>
              </div>
              {failedSubmissions.map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-surface-darker/30 transition-colors border-b border-surface-border last:border-0"
                >
                  <XCircle className="w-4 h-4 text-red-400 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 truncate">
                      {sub.site?.name || "Unknown Site"}
                    </p>
                    {sub.notes && (
                      <p className="text-xs text-red-400/70 truncate">{sub.notes}</p>
                    )}
                  </div>
                  <StatusBadge status={sub.status} />
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleAutoFill(sub)}
                  >
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* Empty state */}
          {submissions.length === 0 && (
            <div className="p-8 text-center">
              <p className="text-slate-500 text-sm">No submissions yet.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Auto-Fill Modal */}
      {selectedSubmission && (
        <AutoFillModal
          open={showAutoFill}
          onOpenChange={setShowAutoFill}
          submissionId={selectedSubmission.id}
          siteName={selectedSubmission.site?.name || "Unknown Site"}
          siteUrl={selectedSubmission.site?.url || ""}
          onComplete={onRefresh}
        />
      )}
    </>
  );
}
