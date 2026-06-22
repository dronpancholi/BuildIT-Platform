"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  BarChart3,
  Bot,
  Download,
  ExternalLink,
  FileBarChart,
  Globe,
  Mail,
  MapPin,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { SubmissionRow } from "@/components/citations/submission-row";
import { StatusBadge } from "@/components/citations/status-badge";
import {
  citationApi,
  type CitationProject,
  type CitationSubmission,
  type CitationSite,
} from "@/lib/api";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<CitationProject | null>(null);
  const [submissions, setSubmissions] = useState<CitationSubmission[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDiscoverDialog, setShowDiscoverDialog] = useState(false);
  const [discoveredSites, setDiscoveredSites] = useState<CitationSite[]>([]);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [selectedSites, setSelectedSites] = useState<Set<string>>(new Set());
  const [isAdding, setIsAdding] = useState(false);
  const [searchFilter, setSearchFilter] = useState("");

  const loadProject = async () => {
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
    if (projectId) loadProject();
  }, [projectId]);

  const handleDiscover = async () => {
    try {
      setIsDiscovering(true);
      const sites = await citationApi.discoverSites(projectId);
      setDiscoveredSites(sites);
      setShowDiscoverDialog(true);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to discover sites");
    } finally {
      setIsDiscovering(false);
    }
  };

  const handleAddSites = async () => {
    if (selectedSites.size === 0) return;
    try {
      setIsAdding(true);
      const siteIds = Array.from(selectedSites);
      await citationApi.bulkCreateSubmissions(projectId, { site_ids: siteIds });
      setSelectedSites(new Set());
      setShowDiscoverDialog(false);
      await loadProject();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to add sites");
    } finally {
      setIsAdding(false);
    }
  };

  const handleExport = async (format: "csv" | "xlsx") => {
    try {
      const blob = format === "csv"
        ? await citationApi.exportCsv(projectId)
        : await citationApi.exportXlsx(projectId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${project?.business_name || "citations"}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Export failed");
    }
  };

  const filteredSubmissions = submissions.filter((s) => {
    if (!searchFilter) return true;
    const siteName = s.site?.name?.toLowerCase() || "";
    return siteName.includes(searchFilter.toLowerCase());
  });

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

  const stats = project.stats;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push("/dashboard/citations")}>
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-100">{project.business_name}</h1>
              <StatusBadge status={project.status} />
            </div>
            {project.website_url && (
              <div className="flex items-center gap-1 text-sm text-slate-500 mt-1">
                <Globe className="w-3.5 h-3.5" />
                <a href={project.website_url} target="_blank" rel="noopener noreferrer" className="hover:text-platform-400">
                  {project.website_url}
                </a>
              </div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => handleExport("csv")}>
            <Download className="w-4 h-4 mr-2" />
            CSV
          </Button>
          <Button variant="outline" onClick={() => handleExport("xlsx")}>
            <Download className="w-4 h-4 mr-2" />
            XLSX
          </Button>
          <Button onClick={handleDiscover} disabled={isDiscovering}>
            <Plus className="w-4 h-4 mr-2" />
            {isDiscovering ? "Discovering..." : "Add Sites"}
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push(`/dashboard/citations/${projectId}/automation`)}
          >
            <Bot className="w-4 h-4 mr-2" />
            Auto-Fill
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push(`/dashboard/citations/${projectId}/verification`)}
          >
            <Mail className="w-4 h-4 mr-2" />
            Verify Email
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push(`/dashboard/citations/${projectId}/recommendations`)}
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Recommendations
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push(`/dashboard/citations/${projectId}/analytics`)}
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            Analytics
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push(`/dashboard/citations/${projectId}/reports`)}
          >
            <FileBarChart className="w-4 h-4 mr-2" />
            Reports
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-5 gap-4">
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-slate-200">{stats.total_sites}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Total Sites</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-emerald-400">{stats.already_exists + stats.new_backlink}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Live</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-blue-400">{stats.in_progress}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">In Progress</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-amber-400">{stats.pending}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Pending</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 text-center">
            <div className="text-2xl font-mono font-bold text-red-400">{stats.failed}</div>
            <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Failed</div>
          </CardContent>
        </Card>
      </div>

      {/* Submissions List */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-mono uppercase tracking-wider text-slate-400">
              Submissions ({submissions.length})
            </CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <Input
                placeholder="Filter sites..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="pl-9 h-8 text-sm"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {filteredSubmissions.length === 0 ? (
            <div className="p-8 text-center">
              <p className="text-slate-500 text-sm">
                {searchFilter ? "No submissions match your filter." : "No submissions yet. Click 'Add Sites' to get started."}
              </p>
            </div>
          ) : (
            <div>
              {filteredSubmissions.map((sub) => (
                <SubmissionRow key={sub.id} submission={sub} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Discover Sites Dialog */}
      <Dialog open={showDiscoverDialog} onOpenChange={setShowDiscoverDialog}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
          <DialogHeader>
            <DialogTitle className="font-mono">DISCOVER SITES</DialogTitle>
            <DialogDescription>
              Select sites to add to this project. Found {discoveredSites.length} recommended sites.
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-y-auto space-y-2 pr-2">
            {discoveredSites.map((site) => (
              <div
                key={site.id}
                className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  selectedSites.has(site.id)
                    ? "border-platform-500/50 bg-platform-600/10"
                    : "border-surface-border hover:border-slate-600"
                }`}
                onClick={() => {
                  setSelectedSites((prev) => {
                    const next = new Set(prev);
                    if (next.has(site.id)) next.delete(site.id);
                    else next.add(site.id);
                    return next;
                  });
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedSites.has(site.id)}
                  onChange={() => {}}
                  className="accent-platform-500"
                />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-200">{site.name}</div>
                  <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                    <span className="bg-surface-darker px-1.5 py-0.5 rounded">{site.category}</span>
                    {site.geo_target && <span>{site.geo_target}</span>}
                    {site.difficulty_score <= 30 && (
                      <span className="text-emerald-400">Easy</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDiscoverDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleAddSites}
              disabled={isAdding || selectedSites.size === 0}
            >
              {isAdding ? "Adding..." : `Add ${selectedSites.size} Sites`}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
