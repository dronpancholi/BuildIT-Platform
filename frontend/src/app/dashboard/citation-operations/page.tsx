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
  Globe,
  AlertTriangle,
  CheckCircle,
  Clock,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

interface CitationDashboardData {
  total_submissions: number;
  by_status: Record<string, number>;
  success_rate: number;
  needs_retry_count: number;
  needs_verification_count: number;
  needs_retry_submissions: SubmissionSummary[];
  needs_verification_submissions: SubmissionSummary[];
}

interface SubmissionSummary {
  id: string;
  project_id: string;
  site_id: string;
  site_name: string | null;
  site_url: string | null;
  site_category: string | null;
  site_difficulty: number | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  listing_url: string | null;
}

interface BulkRetryResult {
  retries_created: number;
  submission_ids: string[];
}

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
  not_started: "outline",
  in_progress: "default",
  new_backlink: "success",
  already_exists: "secondary",
  failed: "destructive",
  verified: "success",
  pending: "warning",
  pending_review: "warning",
  rejected: "destructive",
};

const STATUS_ICONS: Record<string, string> = {
  not_started: "⏳",
  in_progress: "🔄",
  new_backlink: "✅",
  already_exists: "📋",
  failed: "❌",
  verified: "✔️",
};

function DifficultyBadge({ score }: { score: number }) {
  if (score <= 30) return <Badge variant="success" className="text-xs">Easy</Badge>;
  if (score <= 60) return <Badge variant="warning" className="text-xs">Medium</Badge>;
  return <Badge variant="destructive" className="text-xs">Hard</Badge>;
}

export default function CitationOperationsPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");

  const { data: dashboard, isLoading, error } = useApiDetail<CitationDashboardData>(
    ENDPOINTS.CITATION_OPERATIONS,
    "dashboard"
  );

  const bulkRetry = useApiCreate<BulkRetryResult, void>(
    `${ENDPOINTS.CITATION_OPERATIONS}/bulk-retry`,
    {
      invalidateKeys: [ENDPOINTS.CITATION_OPERATIONS],
      successMessage: "Failed submissions queued for retry",
    }
  );

  const retrySubmissions = dashboard?.needs_retry_submissions || [];
  const verificationSubmissions = dashboard?.needs_verification_submissions || [];

  const filteredRetries = searchQuery
    ? retrySubmissions.filter(
        (s) =>
          (s.site_name && s.site_name.toLowerCase().includes(searchQuery.toLowerCase())) ||
          (s.site_url && s.site_url.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : retrySubmissions;

  if (isLoading) {
    return <LoadingSpinner size="lg" className="py-20" />;
  }

  if (error) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="py-8 text-center">
          <p className="text-red-400 text-sm">Failed to load citation operations. Please try again.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Citation Operations</h1>
          <p className="text-slate-400 mt-1">Track submissions, retries, and verifications</p>
        </div>
        <Button
          onClick={() => bulkRetry.mutate(undefined as never)}
          disabled={bulkRetry.isPending || (dashboard?.needs_retry_count || 0) === 0}
          className="gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          {bulkRetry.isPending ? "Retrying..." : `Retry Failed (${dashboard?.needs_retry_count || 0})`}
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <Globe className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{dashboard?.total_submissions || 0}</p>
                <p className="text-xs text-slate-400">Total Submissions</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/10 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">
                  {dashboard ? `${(dashboard.success_rate * 100).toFixed(1)}%` : "0%"}
                </p>
                <p className="text-xs text-slate-400">Success Rate</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-500/10 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{dashboard?.needs_retry_count || 0}</p>
                <p className="text-xs text-slate-400">Needs Retry</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-500/10 rounded-lg">
                <Clock className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{dashboard?.needs_verification_count || 0}</p>
                <p className="text-xs text-slate-400">Needs Verification</p>
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

      {/* Needs Retry Section */}
      {retrySubmissions.length > 0 && (
        <Card className="border-red-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-5 h-5" />
              Failed — Needs Retry ({retrySubmissions.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="relative max-w-sm mb-4">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                placeholder="Search sites..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <div className="space-y-2">
              {filteredRetries.map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center justify-between p-3 bg-surface-darker/50 rounded-lg border border-surface-border hover:border-red-500/30 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="destructive" className="text-xs">Failed</Badge>
                      {sub.site_difficulty !== null && <DifficultyBadge score={sub.site_difficulty} />}
                      {sub.site_category && (
                        <Badge variant="outline" className="text-xs">{sub.site_category}</Badge>
                      )}
                    </div>
                    <p className="text-sm text-slate-200 truncate">{sub.site_name || "Unknown Site"}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{sub.site_url}</p>
                  </div>
                  <div className="text-right ml-4 shrink-0">
                    {sub.completed_at && (
                      <p className="text-xs text-slate-500">{formatDate(sub.completed_at)}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Needs Verification Section */}
      {verificationSubmissions.length > 0 && (
        <Card className="border-amber-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-400">
              <Clock className="w-5 h-5" />
              Needs Verification ({verificationSubmissions.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {verificationSubmissions.map((sub) => (
                <div
                  key={sub.id}
                  className="flex items-center justify-between p-3 bg-surface-darker/50 rounded-lg border border-surface-border hover:border-amber-500/30 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="warning" className="text-xs">New Backlink</Badge>
                      {sub.site_difficulty !== null && <DifficultyBadge score={sub.site_difficulty} />}
                    </div>
                    <p className="text-sm text-slate-200 truncate">{sub.site_name || "Unknown Site"}</p>
                    <p className="text-xs text-slate-400 mt-0.5">{sub.site_url}</p>
                  </div>
                  <div className="flex items-center gap-2 ml-4 shrink-0">
                    {sub.listing_url && (
                      <a
                        href={sub.listing_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    )}
                    {sub.completed_at && (
                      <p className="text-xs text-slate-500">{formatDate(sub.completed_at)}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Empty State */}
      {retrySubmissions.length === 0 && verificationSubmissions.length === 0 && (
        <EmptyState
          icon={<CheckCircle className="w-8 h-8" />}
          title="All submissions on track"
          description="No failed submissions need retry and none are pending verification."
        />
      )}
    </div>
  );
}
