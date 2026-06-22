"use client";

import { ExternalLink, CheckCircle2, Clock, XCircle, AlertTriangle } from "lucide-react";
import { StatusBadge } from "./status-badge";
import type { CitationSubmission } from "@/lib/api";

export function SubmissionRow({ submission }: { submission: CitationSubmission }) {
  const site = submission.site;

  return (
    <div className="flex items-center gap-4 px-4 py-3 hover:bg-surface-darker/50 transition-colors border-b border-surface-border last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-200 truncate">
            {site?.name || "Unknown Site"}
          </span>
          {site?.category && (
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 bg-surface-darker px-1.5 py-0.5 rounded">
              {site.category}
            </span>
          )}
        </div>
        {site?.url && (
          <div className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
            <ExternalLink className="w-3 h-3" />
            <span className="truncate max-w-[300px]">{site.url}</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <div className="flex items-center gap-1">
          {submission.account_created ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <Clock className="w-3.5 h-3.5 text-slate-600" />
          )}
          <span className="text-[10px] text-slate-500">Acct</span>
        </div>
        <div className="flex items-center gap-1">
          {submission.email_verified ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <Clock className="w-3.5 h-3.5 text-slate-600" />
          )}
          <span className="text-[10px] text-slate-500">Verify</span>
        </div>
        <div className="flex items-center gap-1">
          {submission.listing_claimed ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <Clock className="w-3.5 h-3.5 text-slate-600" />
          )}
          <span className="text-[10px] text-slate-500">Claim</span>
        </div>
      </div>

      <StatusBadge status={submission.status} />

      {submission.listing_url && (
        <a
          href={submission.listing_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-platform-400 hover:text-platform-300"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="w-4 h-4" />
        </a>
      )}
    </div>
  );
}
