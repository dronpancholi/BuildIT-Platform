"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  Plus, Search, Users, Globe, Building2, Briefcase,
  ArrowRight, ChevronLeft, ChevronRight, Loader2,
  Archive, RotateCcw, AlertTriangle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import { useApiList, useApiCreate } from "@/services/hooks";
import { fetchApi, clientApi } from "@/lib/api";
import { ENDPOINTS } from "@/services/endpoints";
import { formatDate, cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/error-boundary";
import { Select } from "@/components/ui/select";
import { safeArr, safeStr, safeNum, safeUpper, safeLower, safeFixed, safeLocale, safePct, safeDate, safeDateTime, safeTime, safeReplace, safeSplit, safeSlice, safeStartsWith, safeFind, safeIncludes, safeSort, safeObj, safeKeys, safeValues, safeEntries, safeInitials } from "@/lib/safe";

const NICHE_OPTIONS = [
  "B2B SaaS", "E-commerce", "Healthcare", "Legal", "Real Estate",
  "Local Services", "Content Publishing", "Agency", "Education",
  "Finance", "Technology", "Hospitality", "Manufacturing", "Non-profit",
];

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
}

interface CreateClientPayload {
  name: string;
  domain: string;
  niche?: string;
  business_type?: string;
}

const PAGE_SIZE = 20;

const statusVariant = (s: string) => {
  if (s === "active") return "success" as const;
  if (s === "archived") return "secondary" as const;
  return "outline" as const;
};

export default function ClientsListPage() {
  return (
    <ErrorBoundary>
      <ClientsListPageContent />
    </ErrorBoundary>
  );
}

function ClientsListPageContent() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [showCreate, setShowCreate] = useState(false);
  const [showArchive, setShowArchive] = useState<string | null>(null);
  const [form, setForm] = useState<CreateClientPayload>({
    name: "",
    domain: "",
    niche: "",
    business_type: "",
  });

  const params = useMemo(
    () => ({
      offset,
      limit: PAGE_SIZE,
      search: search || undefined,
      status: statusFilter === "all" ? undefined : statusFilter,
    }),
    [offset, search, statusFilter]
  );

  const { data: clients = [], isLoading, isError, error, refetch } = useApiList<Client>(
    ENDPOINTS.CLIENTS,
    params
  );

  const createMutation = useApiCreate<Client, CreateClientPayload>(ENDPOINTS.CLIENTS, {
    invalidateKeys: [ENDPOINTS.CLIENTS],
    successMessage: "Client created successfully",
  });

  const archiveMutation = useMutation({
    mutationFn: (clientId: string) => clientApi.archiveClient(clientId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.CLIENTS] });
      setShowArchive(null);
    },
  });

  const restoreMutation = useMutation({
    mutationFn: (clientId: string) => clientApi.restoreClient(clientId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [ENDPOINTS.CLIENTS] });
    },
  });

  const total = safeArr<Client>(clients).length;
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const hasMore = offset + PAGE_SIZE < total;

  const handleCreate = () => {
    createMutation.mutate(form, {
      onSuccess: () => {
        setShowCreate(false);
        setForm({ name: "", domain: "", niche: "", business_type: "" });
      },
    });
  };

  if (isError) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Clients</h1>
          </div>
        </div>
        <ErrorState
          error={error}
          message="Failed to load clients"
          onRetry={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100 tracking-tight">Clients</h1>
          <p className="text-slate-500 text-sm mt-0.5">
            {total} client{total !== 1 ? "s" : ""}
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-2">
          <Plus className="w-4 h-4" /> New Client
        </Button>
      </div>

      <div className="flex items-center gap-4">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <Input
            placeholder="Search by name or domain..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
            className="pl-10"
          />
        </div>
        <div className="flex items-center gap-1 bg-surface-darker/50 rounded-lg p-1">
          {[
            { id: "all", label: "All" },
            { id: "active", label: "Active" },
            { id: "archived", label: "Archived" },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setStatusFilter(tab.id);
                setOffset(0);
              }}
              className={cn(
                "px-3 py-1.5 text-xs font-mono rounded-md transition-all",
                statusFilter === tab.id
                  ? "bg-platform-600 text-white"
                  : "text-slate-400 hover:text-slate-200 hover:bg-surface-border"
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="glass-panel overflow-hidden">
          <div className="divide-y divide-surface-border">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="px-5 py-4 flex items-center gap-4 animate-pulse">
                <div className="w-10 h-10 rounded-lg bg-surface-darker" />
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-32 bg-surface-darker rounded" />
                  <div className="h-2.5 w-20 bg-surface-darker rounded" />
                </div>
                <div className="h-2.5 w-16 bg-surface-darker rounded" />
                <div className="h-2.5 w-16 bg-surface-darker rounded" />
                <div className="h-2.5 w-24 bg-surface-darker rounded" />
              </div>
            ))}
          </div>
        </div>
      ) : safeArr<Client>(clients).length === 0 ? (
        <EmptyState
          icon={<Users className="w-8 h-8" />}
          title="No clients found"
          description={
            search
              ? "No clients match your search. Try different keywords."
              : "Add your first client to get started."
          }
          action={
            !search
              ? { label: "New Client", onClick: () => setShowCreate(true) }
              : undefined
          }
        />
      ) : (
        <>
          <div className="glass-panel overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-[9px] text-slate-500 uppercase bg-surface-darker border-b border-surface-border">
                  <tr>
                    <th className="px-5 py-3 font-mono font-medium">Name</th>
                    <th className="px-5 py-3 font-mono font-medium">Domain</th>
                    <th className="px-5 py-3 font-mono font-medium">Niche</th>
                    <th className="px-5 py-3 font-mono font-medium">Business Type</th>
                    <th className="px-5 py-3 font-mono font-medium">Status</th>
                    <th className="px-5 py-3 font-mono font-medium">Created</th>
                    <th className="px-5 py-3 w-20" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {safeArr<Client>(clients).map((client: Client, i: number) => {
                    const isArchived = client.status === "archived";
                    return (
                      <motion.tr
                        key={client.id}
                        initial={{ opacity: 0, y: 6 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.03 }}
                        className={cn(
                          "hover:bg-surface-border/30 transition-colors cursor-pointer group",
                          isArchived && "opacity-60"
                        )}
                        onClick={() => router.push(`/dashboard/clients/${client.id}`)}
                      >
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-9 h-9 rounded-lg bg-platform-600/20 border border-platform-500/20 flex items-center justify-center text-platform-400 font-bold text-xs shrink-0">
                              {client.name
                                .split(" ")
                                .map((w: string) => w[0])
                                .join("")
                                .slice(0, 2)
                                .toUpperCase()}
                            </div>
                            <span className="font-medium text-slate-200 text-sm group-hover:text-platform-400 transition-colors">
                              {client.name}
                            </span>
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-1.5 text-xs text-slate-400">
                            <Globe className="w-3 h-3 text-slate-500" />
                            {client.domain || "—"}
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <span className="text-xs text-slate-400">
                            {client.niche || client.industry || "—"}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-1.5 text-xs text-slate-400">
                            <Briefcase className="w-3 h-3 text-slate-500" />
                            {client.business_type || "—"}
                          </div>
                        </td>
                        <td className="px-5 py-3">
                          <Badge variant={statusVariant(client.status ?? "")}>
                            {(client.status ?? "—").toUpperCase()}
                          </Badge>
                        </td>
                        <td className="px-5 py-3">
                          <span className="text-[11px] font-mono text-slate-500">
                            {formatDate(client.created_at)}
                          </span>
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                            {isArchived ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => restoreMutation.mutate(client.id)}
                                disabled={restoreMutation.isPending}
                                className="h-7 px-2 text-xs gap-1"
                              >
                                <RotateCcw className="w-3 h-3" />
                                Restore
                              </Button>
                            ) : (
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setShowArchive(client.id)}
                                className="h-7 px-2 text-xs gap-1 text-red-400 hover:text-red-300 hover:bg-red-500/10"
                              >
                                <Archive className="w-3 h-3" />
                                Archive
                              </Button>
                            )}
                          </div>
                        </td>
                      </motion.tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between px-5 py-3 border-t border-surface-border bg-surface-darker/50">
              <span className="text-[10px] font-mono text-slate-500">
                Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                  disabled={offset === 0}
                  className="gap-1"
                >
                  <ChevronLeft className="w-3.5 h-3.5" /> Prev
                </Button>
                <span className="text-[10px] font-mono text-slate-400">
                  {currentPage} / {totalPages || 1}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                  disabled={!hasMore}
                  className="gap-1"
                >
                  Next <ChevronRight className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          </div>
        </>
      )}

      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>New Client</DialogTitle>
            <DialogDescription>Add a new client to your portfolio.</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">Client Name</label>
              <Input
                name="name"
                placeholder="Acme Corp"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">Domain</label>
              <Input
                name="domain"
                placeholder="acme.com"
                value={form.domain}
                onChange={(e) => setForm((f) => ({ ...f, domain: e.target.value }))}
              />
            </div>
            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">Niche</label>
              <Select
                options={[
                  { label: "B2B SaaS", value: "B2B SaaS" },
                  { label: "E-commerce", value: "E-commerce" },
                  { label: "Healthcare", value: "Healthcare" },
                  { label: "Finance", value: "Finance" },
                  { label: "Technology", value: "Technology" },
                  { label: "Other", value: "Other" },
                ]}
                value={form.niche}
                onChange={(e: any) => setForm((f) => ({ ...f, niche: e.target.value }))}
                placeholder="Select niche..."
              />
            </div>
            <div>
              <label className="text-xs font-mono text-slate-400 mb-1.5 block">Business Type</label>
              <Input
                placeholder="Technology"
                value={form.business_type}
                onChange={(e) => setForm((f) => ({ ...f, business_type: e.target.value }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!form.name || createMutation.isPending}
            >
              {createMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              Create Client
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Archive Confirmation Dialog */}
      <Dialog open={!!showArchive} onOpenChange={() => setShowArchive(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <AlertTriangle className="w-5 h-5" />
              Archive Client
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to archive this client? They will be moved to the archived list and can be restored later.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowArchive(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => showArchive && archiveMutation.mutate(showArchive)}
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
