"use client";

import { useEffect, useState } from "react";
import {
  Loader2,
  Plus,
  RefreshCw,
  Shield,
  ShieldAlert,
  ShieldCheck,
  ShieldX,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CredentialCard } from "@/components/citations/credential-card";
import { AddCredentialModal } from "@/components/citations/add-credential-modal";
import { fetchApi } from "@/lib/api";

interface VaultSummary {
  total: number;
  active: number;
  locked: number;
  banned: number;
  suspended: number;
  avg_health: number;
}

interface Credential {
  id: string;
  tenant_id: string;
  site_slug: string;
  site_name: string;
  email: string;
  status: string;
  health_score: number;
  use_count: number;
  failure_count: number;
  last_used_at: string | null;
  last_success_at: string | null;
  last_failure_at: string | null;
  last_failure_reason: string | null;
  notes: string | null;
}

export default function VaultPage() {
  const [credentials, setCredentials] = useState<Credential[]>([]);
  const [summary, setSummary] = useState<VaultSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [filterSite, setFilterSite] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [unlockingId, setUnlockingId] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams({
        tenant_id: "00000000-0000-0000-0000-000000000001",
      });
      if (filterSite) params.append("site_slug", filterSite);
      if (filterStatus) params.append("status", filterStatus);

      const result = await fetchApi<{ credentials: Credential[]; summary: VaultSummary }>(
        `/credentials/vault?${params.toString()}`
      );
      setCredentials(result.credentials);
      setSummary(result.summary);
    } catch {
      // Handle error silently
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filterSite, filterStatus]);

  const handleUnlock = async (id: string) => {
    try {
      setUnlockingId(id);
      await fetchApi(`/credentials/vault/${id}/unlock?tenant_id=00000000-0000-0000-0000-000000000001`, {
        method: "POST",
      });
      loadData();
    } catch {
      // Handle error silently
    } finally {
      setUnlockingId(null);
    }
  };

  const uniqueSites = [...new Set(credentials.map((c) => c.site_slug))];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-100 font-mono">
              CREDENTIAL_VAULT
            </h1>
            <Badge variant="outline" className="text-xs">
              Phase 4
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Encrypted credential storage with health tracking
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Credential
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-5 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <Shield className="w-6 h-6 text-slate-400 mx-auto" />
              <div className="text-2xl font-mono font-bold text-slate-200 mt-2">
                {summary.total}
              </div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Total
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <ShieldCheck className="w-6 h-6 text-emerald-400 mx-auto" />
              <div className="text-2xl font-mono font-bold text-emerald-400 mt-2">
                {summary.active}
              </div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Active
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <ShieldAlert className="w-6 h-6 text-amber-400 mx-auto" />
              <div className="text-2xl font-mono font-bold text-amber-400 mt-2">
                {summary.locked}
              </div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Locked
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <ShieldX className="w-6 h-6 text-red-400 mx-auto" />
              <div className="text-2xl font-mono font-bold text-red-400 mt-2">
                {summary.banned}
              </div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Banned
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-mono font-bold text-platform-400 mt-2">
                {summary.avg_health}%
              </div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Avg Health
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <select
          value={filterSite}
          onChange={(e) => setFilterSite(e.target.value)}
          className="bg-surface-dark border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
        >
          <option value="">All Sites</option>
          {uniqueSites.map((slug) => (
            <option key={slug} value={slug}>
              {slug}
            </option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-surface-dark border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="locked">Locked</option>
          <option value="banned">Banned</option>
          <option value="suspended">Suspended</option>
        </select>
      </div>

      {/* Credentials List */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-platform-400 animate-spin" />
        </div>
      ) : credentials.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <Shield className="w-10 h-10 text-slate-600 mx-auto" />
            <p className="text-slate-500 mt-2">No credentials found.</p>
            <Button className="mt-4" onClick={() => setShowAddModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add First Credential
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {credentials.map((cred) => (
            <CredentialCard
              key={cred.id}
              credential={cred}
              onUnlock={handleUnlock}
              onRefresh={loadData}
            />
          ))}
        </div>
      )}

      {/* Add Credential Modal */}
      <AddCredentialModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={loadData}
      />
    </div>
  );
}
