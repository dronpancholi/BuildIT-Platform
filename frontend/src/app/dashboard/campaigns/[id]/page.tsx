"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { useApiDetail } from "@/services/hooks";
import { fetchApi } from "@/lib/api";
import { ENDPOINTS } from "@/services/endpoints";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatDate } from "@/lib/utils";
import { ArrowLeft, Pause, Play, Archive, XCircle, Link2, Calendar, BarChart3, FileText } from "lucide-react";
import { toast } from "sonner";
import type { Campaign } from "@/types/models";

interface CampaignDetail extends Campaign {
  campaign_type: string;
  target_link_count: number;
  acquired_link_count: number;
}

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
  active: "success",
  paused: "warning",
  completed: "secondary",
  draft: "outline",
  cancelled: "destructive",
};

const TYPE_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  guest_post: "default",
  broken_link: "secondary",
  resource_page: "outline",
};

export default function CampaignDetailPage() {
  const params = useParams();
  const router = useRouter();
  const campaignId = params.id as string;
  const queryClient = useQueryClient();

  const { data: campaign, isLoading, error } = useApiDetail<CampaignDetail>(
    ENDPOINTS.CAMPAIGNS,
    campaignId
  );

  const statusMutation = useMutation({
    mutationFn: async (action: "pause" | "resume" | "archive") => {
      return fetchApi(`${ENDPOINTS.CAMPAIGNS}/${campaignId}/${action}`, {
        method: "POST",
      });
    },
    onSuccess: (_data, action) => {
      const labels: Record<string, string> = {
        pause: "Campaign paused",
        resume: "Campaign resumed",
        archive: "Campaign archived",
      };
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.CAMPAIGNS] });
      queryClient.invalidateQueries({ queryKey: [`${ENDPOINTS.CAMPAIGNS}/${campaignId}`] });
    },
    onError: (error: any, action) => {
      const errorMessage = error?.detail || error?.message || "Action failed";
      const labels: Record<string, string> = {
        pause: "Failed to pause campaign",
        resume: "Failed to resume campaign",
        archive: "Failed to archive campaign",
      };
      toast.error(labels[action] || "Action failed", {
        description: errorMessage,
      });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: async () => {
      return fetchApi(`${ENDPOINTS.CAMPAIGNS}/${campaignId}/cancel`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.CAMPAIGNS] });
      queryClient.invalidateQueries({ queryKey: [`${ENDPOINTS.CAMPAIGNS}/${campaignId}`] });
      toast.success("Campaign cancelled");
    },
    onError: (error: any) => {
      toast.error("Failed to cancel campaign", {
        description: error?.detail || error?.message || "Unknown error",
      });
    },
  });

  const handleStatusChange = (action: "pause" | "resume" | "archive") => {
    statusMutation.mutate(action);
  };

  const handleCancel = () => {
    if (confirm("Are you sure you want to cancel this campaign? This action cannot be undone.")) {
      cancelMutation.mutate();
    }
  };

  if (isLoading) {
    return <LoadingSpinner size="lg" className="py-20" />;
  }

  if (error || !campaign) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" onClick={() => router.push("/dashboard/campaigns")}>
          <ArrowLeft className="w-4 h-4" />
          Back to Campaigns
        </Button>
        <Card className="border-red-500/20 bg-red-500/5">
          <CardContent className="py-8 text-center">
            <p className="text-red-400 text-sm">Campaign not found or failed to load.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const detail = campaign as CampaignDetail;
  const progress = detail.target_link_count
    ? Math.round(((detail.acquired_link_count || 0) / detail.target_link_count) * 100)
    : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => router.push("/dashboard/campaigns")}
          >
            <ArrowLeft className="w-4 h-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-100">{campaign.name}</h1>
              <Badge variant={TYPE_VARIANT[detail.campaign_type] || "outline"}>
                {detail.campaign_type?.replace(/_/g, " ") || "—"}
              </Badge>
              <Badge variant={STATUS_VARIANT[campaign.status] || "outline"}>
                {campaign.status}
              </Badge>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {["active", "monitoring", "prospecting", "scoring", "outreach_prep", "awaiting_approval"].includes(campaign.status) ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleStatusChange("pause")}
              disabled={statusMutation.isPending}
            >
              <Pause className="w-4 h-4" />
              Pause
            </Button>
          ) : campaign.status === "paused" ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleStatusChange("resume")}
              disabled={statusMutation.isPending}
            >
              <Play className="w-4 h-4" />
              Resume
            </Button>
          ) : null}
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleStatusChange("archive")}
            disabled={statusMutation.isPending}
          >
            <Archive className="w-4 h-4" />
            Archive
          </Button>
          {!["cancelled", "archived", "complete"].includes(campaign.status) && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={cancelMutation.isPending}
              className="text-red-400 border-red-500/30 hover:bg-red-500/10"
            >
              <XCircle className="w-4 h-4" />
              Cancel
            </Button>
          )}
        </div>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="keywords">Keywords</TabsTrigger>
          <TabsTrigger value="reports">Reports</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                  <Link2 className="w-4 h-4" />
                  Link Progress
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-bold text-slate-100">
                  {detail.acquired_link_count || 0}
                  <span className="text-lg text-slate-500 font-normal">
                    /{detail.target_link_count || 0}
                  </span>
                </div>
                <div className="mt-2 w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                  <div
                    className="h-full bg-platform-500 rounded-full transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500 mt-1">{progress}% complete</p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  Campaign Type
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold text-slate-100 capitalize">
                  {detail.campaign_type?.replace(/_/g, " ") || "—"}
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Platform: {campaign.platform || "—"}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-slate-400 flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Dates
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div>
                    <p className="text-xs text-slate-500">Created</p>
                    <p className="text-sm text-slate-200">{formatDate(campaign.created_at)}</p>
                  </div>
                  {campaign.end_date && (
                    <div>
                      <p className="text-xs text-slate-500">End Date</p>
                      <p className="text-sm text-slate-200">{formatDate(campaign.end_date)}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="timeline">
          <Card>
            <CardContent className="py-12">
              <EmptyState
                icon={<Calendar className="w-8 h-8" />}
                title="NO TIMELINE EVENTS"
                description="Timeline events are recorded when the campaign workflow runs steps (discovery, enrichment, outreach, replies). This will populate after the campaign workflow is started."
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="keywords">
          <Card>
            <CardContent className="py-12">
              <EmptyState
                icon={<FileText className="w-8 h-8" />}
                title="NO KEYWORDS LINKED"
                description="No keywords are linked to this campaign yet. Add keywords to this campaign from the Keywords page to track ranking changes driven by backlink work."
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="reports">
          <Card>
            <CardContent className="py-12">
              <EmptyState
                icon={<BarChart3 className="w-8 h-8" />}
                title="NO CAMPAIGN REPORTS"
                description="No reports have been generated for this campaign. Reports require campaign activity (prospects discovered, outreach sent, replies received, links acquired). Generate a report from the Reports page once the campaign has run."
              />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
