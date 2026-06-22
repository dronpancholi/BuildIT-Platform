"use client";

import { useEffect, useState } from "react";
import {
  Globe,
  Loader2,
  Plus,
  RefreshCw,
  Server,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AddProxyModal } from "@/components/citations/add-proxy-modal";
import { fetchApi } from "@/lib/api";

interface ProxySummary {
  total: number;
  active: number;
  suspended: number;
  expired: number;
  avg_health: number;
  total_requests: number;
  success_rate: number;
}

interface Proxy {
  id: string;
  name: string;
  proxy_type: string;
  proxy_host: string;
  proxy_port: number;
  proxy_protocol: string;
  status: string;
  health_score: number;
  total_requests: number;
  successful_requests: number;
  failed_requests: number;
  assigned_sites: string[] | null;
}

export default function ProxiesPage() {
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [summary, setSummary] = useState<ProxySummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [filterType, setFilterType] = useState<string>("");
  const [filterStatus, setFilterStatus] = useState<string>("");

  const loadData = async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams({
        tenant_id: "00000000-0000-0000-0000-000000000001",
      });
      if (filterType) params.append("proxy_type", filterType);
      if (filterStatus) params.append("status", filterStatus);

      const result = await fetchApi<{ proxies: Proxy[]; summary: ProxySummary }>(
        `/proxies/pools?${params.toString()}`
      );
      setProxies(result.proxies);
      setSummary(result.summary);
    } catch {
      // Handle error silently
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [filterType, filterStatus]);

  const handleDelete = async (id: string) => {
    if (!confirm("Are you sure you want to delete this proxy?")) return;
    try {
      await fetchApi(`/proxies/pools/${id}?tenant_id=00000000-0000-0000-0000-000000000001`, {
        method: "DELETE",
      });
      loadData();
    } catch {
      // Handle error silently
    }
  };

  const handleBlacklist = async (id: string) => {
    try {
      await fetchApi(
        `/proxies/pools/${id}/blacklist?tenant_id=00000000-0000-0000-0000-000000000001&reason=Manual+blacklist`,
        { method: "POST" }
      );
      loadData();
    } catch {
      // Handle error silently
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "active":
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      case "suspended":
        return <ShieldAlert className="w-4 h-4 text-amber-400" />;
      case "expired":
        return <Shield className="w-4 h-4 text-red-400" />;
      default:
        return <Shield className="w-4 h-4 text-slate-500" />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case "residential":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
      case "datacenter":
        return "bg-blue-500/10 text-blue-400 border-blue-500/20";
      case "mobile":
        return "bg-purple-500/10 text-purple-400 border-purple-500/20";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/20";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-100 font-mono">
              PROXY_POOLS
            </h1>
            <Badge variant="outline" className="text-xs">
              Phase 5
            </Badge>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Proxy rotation and rate limiting infrastructure
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={loadData}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Proxy
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      {summary && (
        <div className="grid grid-cols-6 gap-4">
          <Card>
            <CardContent className="p-4 text-center">
              <Server className="w-6 h-6 text-slate-400 mx-auto" />
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
                {summary.suspended}
              </div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Suspended
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
          <Card>
            <CardContent className="p-4 text-center">
              <Globe className="w-6 h-6 text-slate-400 mx-auto" />
              <div className="text-2xl font-mono font-bold text-slate-200 mt-2">
                {summary.total_requests.toLocaleString()}
              </div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Requests
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 text-center">
              <div className="text-2xl font-mono font-bold text-emerald-400 mt-2">
                {summary.success_rate}%
              </div>
              <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Success
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4">
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-surface-dark border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
        >
          <option value="">All Types</option>
          <option value="residential">Residential</option>
          <option value="datacenter">Datacenter</option>
          <option value="mobile">Mobile</option>
          <option value="shared">Shared</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="bg-surface-dark border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="suspended">Suspended</option>
          <option value="expired">Expired</option>
        </select>
      </div>

      {/* Proxies List */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="w-8 h-8 text-platform-400 animate-spin" />
        </div>
      ) : proxies.length === 0 ? (
        <Card>
          <CardContent className="p-8 text-center">
            <Server className="w-10 h-10 text-slate-600 mx-auto" />
            <p className="text-slate-500 mt-2">No proxies configured.</p>
            <Button className="mt-4" onClick={() => setShowAddModal(true)}>
              <Plus className="w-4 h-4 mr-2" />
              Add First Proxy
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {proxies.map((proxy) => (
            <Card key={proxy.id} className="border-surface-border hover:border-platform-500/30 transition-colors">
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(proxy.status)}
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-slate-200">{proxy.name}</p>
                        <Badge variant="outline" className={`text-[10px] ${getTypeColor(proxy.proxy_type)}`}>
                          {proxy.proxy_type}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-500 font-mono">
                        {proxy.proxy_protocol}://{proxy.proxy_host}:{proxy.proxy_port}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button size="sm" variant="outline" onClick={() => handleBlacklist(proxy.id)}>
                      Blacklist
                    </Button>
                    <Button size="sm" variant="outline" onClick={() => handleDelete(proxy.id)}>
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-4 gap-4 mt-3 pt-3 border-t border-surface-border">
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase">Health</p>
                    <p className={`text-sm font-mono font-bold ${proxy.health_score > 70 ? "text-emerald-400" : proxy.health_score > 40 ? "text-amber-400" : "text-red-400"}`}>
                      {proxy.health_score}%
                    </p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase">Requests</p>
                    <p className="text-sm font-mono text-slate-300">{proxy.total_requests.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase">Success</p>
                    <p className="text-sm font-mono text-emerald-400">{proxy.successful_requests.toLocaleString()}</p>
                  </div>
                  <div>
                    <p className="text-[10px] text-slate-500 uppercase">Failed</p>
                    <p className="text-sm font-mono text-red-400">{proxy.failed_requests.toLocaleString()}</p>
                  </div>
                </div>

                {proxy.assigned_sites && proxy.assigned_sites.length > 0 && (
                  <div className="mt-2">
                    <p className="text-[10px] text-slate-500">Assigned Sites:</p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {proxy.assigned_sites.map((site) => (
                        <Badge key={site} variant="outline" className="text-[10px]">
                          {site}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Add Proxy Modal */}
      <AddProxyModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSuccess={loadData}
      />
    </div>
  );
}
