"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Edit2, Save, X, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface EditableCampaignProps {
  campaignId: string;
  onSuccess?: () => void;
}

export function EditableCampaign({ campaignId, onSuccess }: EditableCampaignProps) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<any>(null);

  const { data: campaign, isLoading } = useQuery({
    queryKey: ["campaign", campaignId],
    queryFn: () => fetchApi(`/campaigns/${campaignId}`),
    enabled: !!campaignId,
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) =>
      fetchApi(`/campaigns/${campaignId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["campaign", campaignId] });
      queryClient.invalidateQueries({ queryKey: ["campaigns"] });
      setIsEditing(false);
      onSuccess?.();
    },
  });

  if (isLoading || !campaign) {
    return <div className="text-slate-500 text-sm">Loading...</div>;
  }

  const campaignData = formData || campaign.data || campaign;

  const handleSave = () => {
    if (!formData) return;
    updateMutation.mutate(formData);
  };

  const handleCancel = () => {
    setFormData(null);
    setIsEditing(false);
  };

  const startEditing = () => {
    setFormData(campaignData);
    setIsEditing(true);
  };

  const updateField = (field: string, value: any) => {
    setFormData((prev: any) => ({
      ...prev,
      [field]: value,
    }));
  };

  const getHealthColor = (score: number) => {
    if (score >= 0.8) return "text-emerald-400";
    if (score >= 0.6) return "text-amber-400";
    return "text-red-400";
  };

  const getHealthIcon = (score: number) => {
    if (score >= 0.8) return <TrendingUp className="w-3 h-3" />;
    if (score >= 0.6) return <Minus className="w-3 h-3" />;
    return <TrendingDown className="w-3 h-3" />;
  };

  return (
    <Card className="bg-surface-card border-surface-border">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div>
          <CardTitle className="text-sm font-medium text-slate-400">
            {isEditing ? "Editing Campaign" : "Campaign Details"}
          </CardTitle>
          {!isEditing && (
            <div className="flex items-center gap-2 mt-2">
              <h2 className="text-lg font-bold text-slate-100">
                {campaignData.name}
              </h2>
              <Badge variant="outline" className="text-xs">
                {campaignData.status}
              </Badge>
              <div className={cn("flex items-center gap-1 text-xs", getHealthColor(campaignData.health_score)}>
                {getHealthIcon(campaignData.health_score)}
                {(campaignData.health_score * 100).toFixed(0)}%
              </div>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {!isEditing ? (
            <Button
              size="sm"
              variant="outline"
              onClick={startEditing}
              className="h-8 border-platform-500/50 text-platform-400 hover:bg-platform-500/10"
            >
              <Edit2 className="w-3.5 h-3.5 mr-1" />
              Edit
            </Button>
          ) : (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancel}
                className="h-8 border-slate-600 text-slate-400 hover:bg-slate-800"
                disabled={updateMutation.isPending}
              >
                <X className="w-3.5 h-3.5 mr-1" />
                Cancel
              </Button>
              <Button
                size="sm"
                variant="default"
                onClick={handleSave}
                className="h-8 bg-platform-600 hover:bg-platform-500"
                disabled={updateMutation.isPending}
              >
                <Save className="w-3.5 h-3.5 mr-1" />
                Save
              </Button>
            </>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isEditing ? (
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={(formData || campaignData).name || ""}
                onChange={(e) => updateField("name", e.target.value)}
                className="bg-surface-darker border-surface-border"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="status">Status</Label>
              <select
                id="status"
                value={(formData || campaignData).status || "draft"}
                onChange={(e) => updateField("status", e.target.value)}
                className="flex h-10 w-full rounded-md border border-slate-600 bg-surface-darker px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-platform-500 text-slate-200"
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
                <option value="complete">Complete</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="target_link_count">Target Links</Label>
              <Input
                id="target_link_count"
                type="number"
                value={(formData || campaignData).target_link_count || 0}
                onChange={(e) => updateField("target_link_count", parseInt(e.target.value))}
                className="bg-surface-darker border-surface-border"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="health_score">Health Score (0-1)</Label>
              <Input
                id="health_score"
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={(formData || campaignData).health_score || 0}
                onChange={(e) => updateField("health_score", parseFloat(e.target.value))}
                className="bg-surface-darker border-surface-border"
              />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-slate-500">Name</p>
              <p className="text-sm font-medium">{campaignData.name}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Status</p>
              <p className="text-sm font-medium">{campaignData.status}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Target Links</p>
              <p className="text-sm font-medium">{campaignData.target_link_count}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Acquired Links</p>
              <p className="text-sm font-medium">{campaignData.acquired_link_count}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Health Score</p>
              <div className={cn("text-sm font-medium flex items-center gap-1", getHealthColor(campaignData.health_score)}>
                {getHealthIcon(campaignData.health_score)}
                {(campaignData.health_score * 100).toFixed(2)}%
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500">Total Prospects</p>
              <p className="text-sm font-medium">{campaignData.total_prospects}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
