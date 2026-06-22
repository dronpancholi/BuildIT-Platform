"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  ArrowLeft, Edit3, Archive, Globe, MapPin, Target,
  TrendingUp, Briefcase, Calendar, Activity, Loader2,
  AlertTriangle, BarChart3, Search, FileText, RotateCcw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { ErrorState } from "@/components/ui/error-state";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
  useApiDetail, useApiList, useApiUpdate,
} from "@/services/hooks";
import { fetchApi, clientApi } from "@/lib/api";
import { ENDPOINTS } from "@/services/endpoints";
import { formatDate, cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/error-boundary";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

interface Client {
  id: string;
  tenant_id: string;
  name: string;
  industry?: string;
  status?: string;
  archived_at?: string | null;
  created_at: string;
  updated_at?: string;
  domain?: string;
  niche?: string;
  business_type?: string;
  geo_focus?: string[];
  competitors?: string[];
  profile_data?: Record<string, unknown>;
}

interface Campaign {
  id: string;
  client_id: string;
  name: string;
  platform: string;
  status: string;
  budget?: number;
  start_date?: string;
  end_date?: string;
  created_at: string;
}

interface UpdateClientPayload {
  id: string;
  name: string;
  domain: string;
  industry: string;
}

const NICHE_OPTIONS = [
  "B2B SaaS", "E-commerce", "Healthcare", "Legal", "Real Estate",
  "Local Services", "Content Publishing", "Agency", "Education",
  "Finance", "Technology", "Hospitality", "Manufacturing", "Non-profit",
];

const TABS = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "campaigns", label: "Campaigns", icon: Target },
  { id: "keywords", label: "Keywords", icon: Search },
  { id: "plans", label: "Plans", icon: FileText },
  { id: "reports", label: "Reports", icon: BarChart3 },
  { id: "activity", label: "Activity", icon: TrendingUp },
];

const statusVariant = (s: string) => {
  if (s === "active") return "success" as const;
  if (s === "archived") return "secondary" as const;
  return "outline" as const;
};

const campaignStatusVariant = (s: string) => {
  if (s === "active") return "success" as const;
  if (s === "completed") return "default" as const;
  if (s === "paused") return "warning" as const;
  return "outline" as const;
};

function PlaceholderTab({ title, description }: { title: string; description: string }) {
  return (
    <EmptyState
      icon={<Search className="w-8 h-8" />}
      title={title}
      description={description}
    />
  );
}

function ClientDetailPageContent() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const clientId = params.id as string;

  const [activeTab, setActiveTab] = useState("overview");
  const [showEdit, setShowEdit] = useState(false);
  const [showArchive, setShowArchive] = useState(false);
  const [editForm, setEditForm] = useState({
    name: "",
    domain: "",
    industry: "",
  });

  const {
    data: client,
    isLoading,
    isError,
    error,
    refetch,
  } = useApiDetail<Client>(ENDPOINTS.CLIENTS, clientId);

  const {
    data: campaigns = [],
    isLoading: campaignsLoading,
  } = useApiList<Campaign>(
    ENDPOINTS.CAMPAIGNS,
    { client_id: clientId },
    { enabled: !!clientId && activeTab === "campaigns" }
  );

  const updateMutation = useApiUpdate<Client, UpdateClientPayload>(
    ENDPOINTS.CLIENTS,
    {
      invalidateKeys: [ENDPOINTS.CLIENTS, ENDPOINTS.CAMPAIGNS],
      successMessage: "Client updated successfully",
    }
  );

  const archiveMutation = useMutation({
    mutationFn: () => clientApi.archiveClient(clientId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.CLIENTS] });
      queryClient.invalidateQueries({ queryKey: [`${ENDPOINTS.CLIENTS}/${clientId}`] });
      setShowArchive(false);
    },
  });

  const restoreMutation = useMutation({
    mutationFn: () => clientApi.restoreClient(clientId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.CLIENTS] });
      queryClient.invalidateQueries({ queryKey: [`${ENDPOINTS.CLIENTS}/${clientId}`] });
    },
  });

  const handleOpenEdit = () => {
    if (!client) return;
    setEditForm({
      name: client.name,
      domain: client.domain || "",
      industry: client.industry || "",
    });
    setShowEdit(true);
  };

  const handleSaveEdit = () => {
    updateMutation.mutate(
      { id: clientId, ...editForm },
      { onSuccess: () => setShowEdit(false) }
    );
  };

  const handleArchive = () => {
    archiveMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (isError || !client) {
    return (
      <div className="space-y-6">
        <button
          onClick={() => router.push("/dashboard/clients")}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Clients
        </button>
        <ErrorState
          error={error}
          message="Client not found"
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  const profile = (client.profile_data as Record<string, unknown>) || {};
  const geoFocus = client.geo_focus ?? (profile.geo_focus as string[]) ?? [];
  const competitors = client.competitors ?? (profile.competitors as string[]) ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push("/dashboard/clients")}
            className="p-2 rounded-lg hover:bg-surface-border/30 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400 font-bold text-lg shrink-0">
              {client.name
                .split(" ")
                .map((w: string) => w[0])
                .join("")
                .slice(0, 2)
                .toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-100 tracking-tight">
                  {client.name}
                </h1>
                <Badge variant={statusVariant(client.status ?? "active")}>
                  {safeUpper(client.status ?? "active")}
                </Badge>
              </div>
              <div className="flex items-center gap-3 mt-1">
                {client.domain && (
                  <span className="text-xs text-slate-500 flex items-center gap-1.5">
                    <Globe className="w-3 h-3" />
                    {client.domain}
                  </span>
                )}
                {(client.niche || client.industry) && (
                  <Badge variant="outline" className="text-[10px]">
                    {client.niche || client.industry}
                  </Badge>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={handleOpenEdit} className="gap-1.5">
            <Edit3 className="w-3.5 h-3.5" /> Edit
          </Button>
          {client.status === "archived" ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => restoreMutation.mutate()}
              disabled={restoreMutation.isPending}
              className="gap-1.5"
            >
              {restoreMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <RotateCcw className="w-3.5 h-3.5" />
              )}
              Restore
            </Button>
          ) : (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setShowArchive(true)}
              className="gap-1.5"
            >
              <Archive className="w-3.5 h-3.5" /> Archive
            </Button>
          )}
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="glass-panel overflow-hidden">
        <div className="flex items-center gap-1 p-1 bg-surface-darker/50 border-b border-surface-border overflow-x-auto">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-2 text-xs font-mono rounded-md transition-all whitespace-nowrap",
                  isActive
                    ? "bg-platform-600 text-white"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-border"
                )}
              >
                <Icon className="w-3.5 h-3.5" />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === "overview" && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-6"
            >
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-xs font-mono uppercase tracking-wider">
                      Client Information
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Name</span>
                        <span className="text-slate-200 font-medium">{client.name}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Domain</span>
                        <span className="text-slate-200 flex items-center gap-1.5">
                          <Globe className="w-3 h-3 text-slate-500" />
                          {client.domain || "—"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Niche</span>
                        <span className="text-slate-200">{client.niche || client.industry || "—"}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Business Type</span>
                        <span className="text-slate-200 flex items-center gap-1.5">
                          <Briefcase className="w-3 h-3 text-slate-500" />
                          {client.business_type || "—"}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Status</span>
                        <Badge variant={statusVariant(client.status ?? "active")}>
                          {safeUpper(client.status ?? "active")}
                        </Badge>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Created</span>
                        <span className="text-slate-200 font-mono text-xs">
                          {formatDate(client.created_at)}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-xs font-mono uppercase tracking-wider">
                      Profile Data
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {safeKeys(profile).length > 0 ? (
                      <div className="space-y-2">
                        {safeEntries(profile).slice(0, 8).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-sm">
                            <span className="text-slate-500 capitalize">
                              {key.replace(/_/g, " ")}
                            </span>
                            <span className="text-slate-200 font-mono text-xs max-w-[200px] truncate">
                              {typeof value === "object" ? JSON.stringify(value) : String(value)}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 py-4 text-center">
                        No profile data available.
                      </p>
                    )}
                  </CardContent>
                </Card>
              </div>

              {safeArr<string>(geoFocus).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-xs font-mono uppercase tracking-wider flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-platform-400" />
                      Geographic Focus
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {safeArr<string>(geoFocus).map((geo: string, i: number) => (
                        <Badge key={i} variant="outline">
                          {geo}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {safeArr<string>(competitors).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-xs font-mono uppercase tracking-wider flex items-center gap-2">
                      <TrendingUp className="w-3.5 h-3.5 text-platform-400" />
                      Competitors
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex flex-wrap gap-2">
                      {safeArr<string>(competitors).map((comp: string, i: number) => (
                        <Badge key={i} variant="outline">
                          {comp}
                        </Badge>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              <div className="glass-panel p-4">
                <div className="flex items-center gap-2 text-[10px] font-mono text-slate-600">
                  <Calendar className="w-3 h-3" />
                  <span>Created {formatDate(client.created_at)}</span>
                  <span className="text-slate-700">·</span>
                  <span>Updated {formatDate(client.updated_at)}</span>
                </div>
              </div>
            </motion.div>
          )}

          {/* Campaigns Tab */}
          {activeTab === "campaigns" && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
            >
              {campaignsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <LoadingSpinner size="md" />
                </div>
              ) : safeArr<Campaign>(campaigns).length === 0 ? (
                <EmptyState
                  icon={<Target className="w-8 h-8" />}
                  title="No campaigns"
                  description="This client has no campaigns yet. Create one to get started."
                />
              ) : (
                <div className="glass-panel overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                      <thead className="text-[9px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
                        <tr>
                          <th className="px-5 py-3 font-mono font-medium">Campaign</th>
                          <th className="px-5 py-3 font-mono font-medium">Platform</th>
                          <th className="px-5 py-3 font-mono font-medium">Status</th>
                          <th className="px-5 py-3 font-mono font-medium text-right">Budget</th>
                          <th className="px-5 py-3 font-mono font-medium">Start Date</th>
                          <th className="px-5 py-3 font-mono font-medium">End Date</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border">
                        {safeArr<Campaign>(campaigns).map((c: Campaign, i: number) => (
                          <motion.tr
                            key={c.id}
                            initial={{ opacity: 0, y: 4 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.03 }}
                            className="hover:bg-surface-border/30 transition-colors cursor-pointer"
                            onClick={() => router.push(`/dashboard/campaigns/${c.id}`)}
                          >
                            <td className="px-5 py-3">
                              <span className="font-medium text-slate-200 text-sm">
                                {c.name}
                              </span>
                            </td>
                            <td className="px-5 py-3">
                              <span className="text-xs text-slate-400 capitalize">
                                {c.platform}
                              </span>
                            </td>
                            <td className="px-5 py-3">
                              <Badge variant={campaignStatusVariant(c.status)}>
                                {safeUpper(c.status)}
                              </Badge>
                            </td>
                            <td className="px-5 py-3 text-right">
                              <span className="text-xs font-mono text-slate-400">
                                {c.budget ? `$${safeLocale(c.budget)}` : "—"}
                              </span>
                            </td>
                            <td className="px-5 py-3">
                              <span className="text-[11px] font-mono text-slate-500">
                                {c.start_date ? formatDate(c.start_date) : "—"}
                              </span>
                            </td>
                            <td className="px-5 py-3">
                              <span className="text-[11px] font-mono text-slate-500">
                                {c.end_date ? formatDate(c.end_date) : "—"}
                              </span>
                            </td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </motion.div>
          )}

          {/* Keywords Tab */}
          {activeTab === "keywords" && (
            <PlaceholderTab
              title="NO KEYWORDS YET"
              description="No keywords have been researched for this client. To research keywords for this client, go to Keywords and assign them, or run a keyword research workflow on one of this client's campaigns."
            />
          )}

          {/* Plans Tab */}
          {activeTab === "plans" && (
            <PlaceholderTab
              title="NO PLANS YET"
              description="No strategic plans have been created for this client. Plans are built by SEO strategists from research and briefings. This tab will populate once a plan is created and linked to this client."
            />
          )}

          {/* Reports Tab */}
          {activeTab === "reports" && (
            <PlaceholderTab
              title="NO REPORTS YET"
              description="No reports have been generated for this client. Reports are generated after a campaign runs and produces measurable data (ranking changes, links acquired, traffic)."
            />
          )}

          {/* Activity Tab */}
          {activeTab === "activity" && (
            <div className="space-y-4">
              <div className="glass-panel p-6 text-center">
                <Activity className="w-8 h-8 text-slate-600 mx-auto mb-3" />
                <h3 className="text-sm font-medium text-slate-300 mb-1">
                  Recent Activity
                </h3>
                <p className="text-xs text-slate-500">
                  Activity feed will show recent changes, updates, and events for this client.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Edit Dialog */}
      <Dialog open={showEdit} onOpenChange={setShowEdit}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Client</DialogTitle>
            <DialogDescription>Update client information.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">Name</label>
              <Input
                value={editForm.name}
                onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">Domain</label>
              <Input
                value={editForm.domain}
                onChange={(e) => setEditForm((f) => ({ ...f, domain: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">Niche</label>
              <select
                value={editForm.industry}
                onChange={(e) => setEditForm((f) => ({ ...f, industry: e.target.value }))}
                className="flex h-10 w-full rounded-lg border border-surface-border bg-surface-darker px-3 py-2 text-sm text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-platform-500/50"
              >
                <option value="">Select niche...</option>
                {NICHE_OPTIONS.map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEdit(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleSaveEdit}
              disabled={!editForm.name || updateMutation.isPending}
            >
              {updateMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Archive Confirmation Dialog */}
      <Dialog open={showArchive} onOpenChange={setShowArchive}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-5 h-5" />
              Archive Client
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to archive <strong>{client.name}</strong>? This will mark the
              client as archived and they will no longer appear in active lists.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowArchive(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleArchive}
              disabled={archiveMutation.isPending}
            >
              {archiveMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Archive Client
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function ClientDetailPage() {
  return (
    <ErrorBoundary>
      <ClientDetailPageContent />
    </ErrorBoundary>
  );
}
