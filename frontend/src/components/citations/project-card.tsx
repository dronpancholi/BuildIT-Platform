"use client";

import { useRouter } from "next/navigation";
import { Building2, ExternalLink, Globe, MapPin } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "./status-badge";
import type { CitationProject } from "@/lib/api";

function ProgressBar({
  total,
  completed,
  inProgress,
  failed,
}: {
  total: number;
  completed: number;
  inProgress: number;
  failed: number;
}) {
  if (total === 0) return null;
  const completedPct = (completed / total) * 100;
  const inProgressPct = (inProgress / total) * 100;
  const failedPct = (failed / total) * 100;

  return (
    <div className="h-1.5 bg-surface-darker rounded-full overflow-hidden flex">
      {completedPct > 0 && (
        <div className="bg-emerald-500" style={{ width: `${completedPct}%` }} />
      )}
      {inProgressPct > 0 && (
        <div className="bg-blue-500" style={{ width: `${inProgressPct}%` }} />
      )}
      {failedPct > 0 && (
        <div className="bg-red-500" style={{ width: `${failedPct}%` }} />
      )}
    </div>
  );
}

export function ProjectCard({ project }: { project: CitationProject }) {
  const router = useRouter();
  const stats = project.stats;

  return (
    <Card
      className="cursor-pointer hover:border-platform-500/30 transition-colors group"
      onClick={() => router.push(`/dashboard/citations/${project.id}`)}
    >
      <CardContent className="p-5">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-platform-600/10 border border-platform-500/20 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-platform-400" />
            </div>
            <div>
              <h3 className="font-medium text-slate-200 group-hover:text-platform-400 transition-colors">
                {project.business_name}
              </h3>
              {project.website_url && (
                <div className="flex items-center gap-1 text-xs text-slate-500 mt-0.5">
                  <Globe className="w-3 h-3" />
                  <span className="truncate max-w-[200px]">{project.website_url}</span>
                </div>
              )}
            </div>
          </div>
          <StatusBadge status={project.status} />
        </div>

        <div className="grid grid-cols-4 gap-3 mt-4">
          <div className="text-center">
            <div className="text-lg font-mono font-bold text-slate-200">{stats.total_sites}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Sites</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-mono font-bold text-emerald-400">{stats.already_exists + stats.new_backlink}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Live</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-mono font-bold text-blue-400">{stats.in_progress}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Active</div>
          </div>
          <div className="text-center">
            <div className="text-lg font-mono font-bold text-red-400">{stats.failed}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Failed</div>
          </div>
        </div>

        <div className="mt-4">
          <ProgressBar
            total={stats.total_sites}
            completed={stats.already_exists + stats.new_backlink}
            inProgress={stats.in_progress}
            failed={stats.failed}
          />
        </div>

        <div className="flex items-center justify-between mt-3 text-xs text-slate-500">
          <span>{stats.completion_pct.toFixed(0)}% complete</span>
          <span>{new Date(project.created_at).toLocaleDateString()}</span>
        </div>
      </CardContent>
    </Card>
  );
}
