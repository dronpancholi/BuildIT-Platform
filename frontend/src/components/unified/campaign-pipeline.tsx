"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle, Clock, AlertCircle, TrendingUp, TrendingDown, Minus, Activity } from "lucide-react";

const Campaign = Activity;
import { cn } from "@/lib/utils";

interface CampaignPipelineProps {
  className?: string;
}

type Stage = "research" | "prospecting" | "outreach" | "replies" | "acquired" | "completed";

interface PipelineCampaign {
  id: string;
  name: string;
  stage: Stage;
  health: number;
  prospects: number;
  emailsSent: number;
  linksAcquired: number;
  customer: string;
}

export function CampaignPipeline({ className }: CampaignPipelineProps) {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["campaigns-pipeline"],
    queryFn: () => fetchApi("/campaigns/list"),
    refetchInterval: 30000,
  });

  const campaigns = data?.data?.campaigns || [];

  const stages: { id: Stage; label: string; color: string }[] = [
    { id: "research", label: "Research", color: "bg-blue-500" },
    { id: "prospecting", label: "Prospecting", color: "bg-purple-500" },
    { id: "outreach", label: "Outreach", color: "bg-amber-500" },
    { id: "replies", label: "Replies", color: "bg-orange-500" },
    { id: "acquired", label: "Acquired", color: "bg-emerald-500" },
    { id: "completed", label: "Completed", color: "bg-green-500" },
  ];

  const getCampaignsByStage = (stage: Stage) => {
    return campaigns.filter((c: any) => c.stage === stage);
  };

  const getHealthColor = (health: number) => {
    if (health >= 0.8) return "text-emerald-400";
    if (health >= 0.6) return "text-amber-400";
    return "text-red-400";
  };

  const getHealthIcon = (health: number) => {
    if (health >= 0.8) return <TrendingUp className="w-3 h-3" />;
    if (health >= 0.6) return <Minus className="w-3 h-3" />;
    return <TrendingDown className="w-3 h-3" />;
  };

  return (
    <Card className={cn("bg-surface-card border-surface-border", className)}>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-slate-400">Campaign Pipeline</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-platform-500"></div>
          </div>
        ) : campaigns.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            No campaigns yet. Create your first campaign to get started.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            {stages.map((stage) => {
              const stageCampaigns = getCampaignsByStage(stage.id);
              return (
                <div key={stage.id} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className={cn("w-2 h-2 rounded-full", stage.color)} />
                    <h3 className="text-xs font-medium text-slate-300">{stage.label}</h3>
                    <span className="ml-auto text-xs text-slate-500">{stageCampaigns.length}</span>
                  </div>
                  <div className="space-y-2">
                    {stageCampaigns.map((campaign: any) => (
                      <div
                        key={campaign.id}
                        className="p-3 rounded-lg bg-surface-darker border border-surface-border hover:border-platform-500/50 transition-colors cursor-pointer"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <h4 className="text-xs font-medium text-slate-200 line-clamp-2">
                            {campaign.name}
                          </h4>
                          <Badge
                            variant="outline"
                            className={cn(
                              "text-[10px] border-0",
                              getHealthColor(campaign.health_score || 0)
                            )}
                          >
                            {getHealthIcon(campaign.health_score || 0)}
                            {(campaign.health_score * 100).toFixed(0)}%
                          </Badge>
                        </div>
                        <div className="flex items-center gap-2 text-xs text-slate-500">
                          <span className="truncate">{campaign.customer_name}</span>
                        </div>
                        <div className="flex items-center gap-3 mt-2 text-xs">
                          <div className="flex items-center gap-1 text-slate-500">
                            <Clock className="w-3 h-3" />
                            <span>{campaign.prospects || 0}</span>
                          </div>
                          <div className="flex items-center gap-1 text-slate-500">
                            <CheckCircle className="w-3 h-3" />
                            <span>{campaign.links_acquired || 0}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
