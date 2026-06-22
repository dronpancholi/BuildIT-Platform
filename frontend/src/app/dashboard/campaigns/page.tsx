"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useApiList, useApiCreate } from "@/services/hooks";
import { ENDPOINTS } from "@/services/endpoints";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { formatDate } from "@/lib/utils";
import { Plus, FileText, Search } from "lucide-react";
import type { Campaign, Client } from "@/types/models";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface CampaignWithType extends Campaign {
  campaign_type: string;
}

const STATUS_TABS = [
  { label: "All", value: "" },
  { label: "Active", value: "active" },
  { label: "Paused", value: "paused" },
  { label: "Completed", value: "completed" },
] as const;

const CAMPAIGN_TYPES = [
  { label: "Guest Post", value: "guest_post" },
  { label: "Broken Link", value: "broken_link" },
  { label: "Resource Page", value: "resource_page" },
];

const CAMPAIGN_TYPE_VARIANT: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
  guest_post: "default",
  broken_link: "secondary",
  resource_page: "outline",
};

const STATUS_VARIANT: Record<string, "default" | "secondary" | "outline" | "success" | "warning" | "destructive"> = {
  active: "success",
  paused: "warning",
  completed: "secondary",
  draft: "outline",
};

export default function CampaignsPage() {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: "",
    client_id: "",
    campaign_type: "guest_post",
  });

  const params: Record<string, string | number | boolean | undefined> = {};
  if (statusFilter) params.status = statusFilter;
  if (searchQuery) params.search = searchQuery;

  const { data: campaigns, isLoading, error } = useApiList<CampaignWithType>(
    ENDPOINTS.CAMPAIGNS,
    params
  );

  const { data: clients } = useApiList<Client>(ENDPOINTS.CLIENTS);

  const createMutation = useApiCreate<Campaign, typeof createForm>(
    ENDPOINTS.CAMPAIGNS,
    {
      invalidateKeys: [ENDPOINTS.CAMPAIGNS],
      successMessage: "Campaign created successfully",
    }
  );

  const handleCreate = () => {
    createMutation.mutate(createForm, {
      onSuccess: () => {
        setShowCreateDialog(false);
        setCreateForm({ name: "", client_id: "", campaign_type: "guest_post" });
      },
    });
  };

  const clientMap = new Map(safeArr<Client>(clients).map((c) => [c.id, c.name]));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100">Campaigns</h1>
          <p className="text-slate-400 mt-1">Manage your outreach campaigns</p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="w-4 h-4" />
          New Campaign
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <Input
            placeholder="Search campaigns..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex items-center gap-1 bg-surface-card border border-surface-border rounded-lg p-1">
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setStatusFilter(tab.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${
                statusFilter === tab.value
                  ? "bg-surface-darker text-slate-100 shadow-sm"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <LoadingSpinner size="lg" className="py-20" />
      ) : error ? (
        <Card className="border-red-500/20 bg-red-500/5">
          <CardContent className="py-8 text-center">
            <p className="text-red-400 text-sm">Failed to load campaigns. Please try again.</p>
          </CardContent>
        </Card>
      ) : !campaigns || safeArr<CampaignWithType>(campaigns).length === 0 ? (
        <EmptyState
          icon={<FileText className="w-8 h-8" />}
          title="No campaigns found"
          description={
            searchQuery || statusFilter
              ? "No campaigns match your filters. Try adjusting your search."
              : "Create your first campaign to start tracking outreach."
          }
          action={
            !searchQuery && !statusFilter
              ? { label: "New Campaign", onClick: () => setShowCreateDialog(true) }
              : undefined
          }
        />
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-surface-border">
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Name</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Client</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Type</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Status</th>
                  <th className="text-left px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {safeArr<CampaignWithType>(campaigns).map((campaign) => (
                  <tr
                    key={campaign.id}
                    onClick={() => router.push(`/dashboard/campaigns/${campaign.id}`)}
                    className="hover:bg-surface-card/50 cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-slate-200">{campaign.name}</td>
                    <td className="px-4 py-3 text-slate-400">
                      {clientMap.get(campaign.client_id) || campaign.client_id}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={CAMPAIGN_TYPE_VARIANT[(campaign as CampaignWithType).campaign_type] || "outline"}>
                        {(campaign as CampaignWithType).campaign_type?.replace(/_/g, " ") || "—"}
                      </Badge>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={STATUS_VARIANT[campaign.status] || "outline"}>
                        {campaign.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {formatDate(campaign.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Campaign</DialogTitle>
            <DialogDescription>Set up a new outreach campaign</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="campaign-name">Campaign Name</Label>
              <Input
                id="campaign-name"
                placeholder="e.g., Q1 Link Building"
                value={createForm.name}
                onChange={(e) => setCreateForm({ ...createForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="campaign-client">Client</Label>
              <Select
                id="campaign-client"
                placeholder="Select a client"
                options={safeArr<Client>(clients).map((c) => ({ label: c.name, value: c.id }))}
                value={createForm.client_id}
                onChange={(e) => setCreateForm({ ...createForm, client_id: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="campaign-type">Campaign Type</Label>
              <Select
                id="campaign-type"
                options={CAMPAIGN_TYPES}
                value={createForm.campaign_type}
                onChange={(e) => setCreateForm({ ...createForm, campaign_type: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!createForm.name || !createForm.client_id || createMutation.isPending}
            >
              {createMutation.isPending ? "Creating..." : "Create Campaign"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
