"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useApiList, useApiDetail } from "@/services/hooks";
import { ENDPOINTS } from "@/services/endpoints";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { EmptyState } from "@/components/ui/empty-state";
import { formatDate } from "@/lib/utils";
import { Search, Activity, AlertTriangle, CheckCircle, Clock, Eye } from "lucide-react";

interface CampaignOverviewData {
  total: number;
  by_status: Record<string, number>;
  needs_attention: CampaignOverviewItem[];
  campaigns: CampaignOverviewItem[];
  recent_activity: TimelineEvent[];
}

interface CampaignOverviewItem {
  id: string;
  name: string;
  status: string;
  type: string;
  client_name: string | null;
  health_score: number;
  acquired_links: number;
  target_links: number;
  last_activity: string | null;
}

interface TimelineEvent {
  id: string;
  step_name: string;
  status: string;
  message: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
  active: "success",
  paused: "warning",
  complete: "secondary",
  draft: "outline",
  cancelled: "destructive",
  monitoring: "default",
  archived: "secondary",
};

function HealthBadge({ score }: { score: number }) {
  if (score >= 0.85) return <Badge variant="success">Excellent</Badge>;
  if (score >= 0.70) return <Badge variant="default">Good</Badge>;
  if (score >= 0.50) return <Badge variant="warning">Fair</Badge>;
  if (score >= 0.30) return <Badge variant="destructive">Poor</Badge>;
  return <Badge variant="destructive">Critical</Badge>;
}

function ProgressBar({ acquired, target }: { acquired: number; target: number }) {
  const pct = target > 0 ? Math.round((acquired / target) * 100) : 0;
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{acquired} / {target} links</span>
        <span>{pct}%</span>
      </div>
      <div className="w-full bg-surface-darker rounded-full h-2">
        <div
          className="bg-blue-500 h-2 rounded-full transition-all"
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function CampaignOperationsPage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");

  const { data: overview, isLoading, error } = useApiDetail<CampaignOverviewData>(
    ENDPOINTS.CAMPAIGN_OPERATIONS,
    "overview"
  );

  const campaigns = overview?.campaigns || [];
  const filteredCampaigns = searchQuery
    ? campaigns.filter(
        (c) =>
          c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (c.client_name && c.client_name.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : campaigns;

  if (isLoading) {
    return <LoadingSpinner size="lg" className="py-20" />;
  }

  if (error) {
    return (
      <Card className="border-red-500/20 bg-red-500/5">
        <CardContent className="py-8 text-center">
          <p className="text-red-400 text-sm">Failed to load campaign operations. Please try again.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-slate-100">Campaign Operations</h1>
        <p className="text-slate-400 mt-1">Unified view of all campaign activity</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <Activity className="w-5 h-5 text-blue-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{overview?.total || 0}</p>
                <p className="text-xs text-slate-400">Total Campaigns</p>
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
                <p className="text-2xl font-bold text-slate-100">{overview?.by_status?.active || 0}</p>
                <p className="text-xs text-slate-400">Active</p>
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
                <p className="text-2xl font-bold text-slate-100">{overview?.needs_attention?.length || 0}</p>
                <p className="text-xs text-slate-400">Needs Attention</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-slate-500/10 rounded-lg">
                <Clock className="w-5 h-5 text-slate-400" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-100">{overview?.by_status?.draft || 0}</p>
                <p className="text-xs text-slate-400">Drafts</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Needs Attention Section */}
      {overview?.needs_attention && overview.needs_attention.length > 0 && (
        <Card className="border-amber-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-400">
              <AlertTriangle className="w-5 h-5" />
              Needs Attention
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {overview.needs_attention.map((campaign) => (
                <div
                  key={campaign.id}
                  onClick={() => router.push(`/dashboard/campaign-operations/${campaign.id}`)}
                  className="p-3 bg-surface-darker/50 rounded-lg border border-surface-border hover:border-amber-500/30 cursor-pointer transition-colors"
                >
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-medium text-slate-200 text-sm">{campaign.name}</h4>
                    <Badge variant="warning" className="text-xs">Attention</Badge>
                  </div>
                  <p className="text-xs text-slate-400 mb-2">{campaign.client_name || "No client"}</p>
                  <ProgressBar acquired={campaign.acquired_links} target={campaign.target_links} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <Input
          placeholder="Search campaigns..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Campaign List */}
      {filteredCampaigns.length === 0 ? (
        <EmptyState
          icon={<Activity className="w-8 h-8" />}
          title="No campaigns found"
          description={searchQuery ? "No campaigns match your search." : "No campaigns yet."}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCampaigns.map((campaign) => (
            <Card
              key={campaign.id}
              className="hover:border-slate-600 cursor-pointer transition-colors"
              onClick={() => router.push(`/dashboard/campaign-operations/${campaign.id}`)}
            >
              <CardContent className="p-4">
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-medium text-slate-200">{campaign.name}</h3>
                    <p className="text-xs text-slate-400 mt-0.5">{campaign.client_name || "No client"}</p>
                  </div>
                  <Badge variant={STATUS_VARIANT[campaign.status] || "outline"}>
                    {campaign.status}
                  </Badge>
                </div>

                <div className="flex items-center gap-4 mb-3">
                  <Badge variant="outline" className="text-xs">
                    {campaign.type?.replace(/_/g, " ") || "—"}
                  </Badge>
                  <HealthBadge score={campaign.health_score} />
                </div>

                <ProgressBar acquired={campaign.acquired_links} target={campaign.target_links} />

                <div className="flex justify-between items-center mt-3 pt-3 border-t border-surface-border">
                  <span className="text-xs text-slate-500">
                    {campaign.last_activity ? formatDate(campaign.last_activity) : "No activity"}
                  </span>
                  <Button variant="ghost" size="sm" className="h-7 text-xs">
                    <Eye className="w-3 h-3 mr-1" />
                    View
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Recent Activity */}
      {overview?.recent_activity && overview.recent_activity.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-slate-200">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {overview.recent_activity.slice(0, 10).map((event) => (
                <div
                  key={event.id}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-darker/30"
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      event.status === "completed"
                        ? "bg-green-400"
                        : event.status === "failed"
                        ? "bg-red-400"
                        : "bg-blue-400"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-300 truncate">{event.message || event.step_name}</p>
                    <p className="text-xs text-slate-500">{formatDate(event.timestamp)}</p>
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
