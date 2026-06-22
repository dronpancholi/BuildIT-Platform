"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Edit,
  Lock,
  Shield,
  TestTube,
  Unlock,
  XCircle,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface Credential {
  id: string;
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

interface CredentialCardProps {
  credential: Credential;
  onUnlock?: (id: string) => void;
  onRefresh?: () => void;
}

function getStatusIcon(status: string) {
  switch (status) {
    case "active":
      return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    case "locked":
      return <Lock className="w-4 h-4 text-amber-400" />;
    case "banned":
      return <XCircle className="w-4 h-4 text-red-400" />;
    case "suspended":
      return <AlertTriangle className="w-4 h-4 text-orange-400" />;
    default:
      return <Shield className="w-4 h-4 text-slate-500" />;
  }
}

function getStatusBadge(status: string) {
  const variants: Record<string, string> = {
    active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    locked: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    banned: "bg-red-500/10 text-red-400 border-red-500/20",
    suspended: "bg-orange-500/10 text-orange-400 border-orange-500/20",
    expired: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  };
  return (
    <Badge variant="outline" className={`text-[10px] ${variants[status] || ""}`}>
      {status}
    </Badge>
  );
}

function getHealthColor(score: number) {
  if (score > 70) return "text-emerald-400";
  if (score > 40) return "text-amber-400";
  return "text-red-400";
}

function timeAgo(dateStr: string | null) {
  if (!dateStr) return "Never";
  const date = new Date(dateStr);
  const now = new Date();
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function CredentialCard({ credential, onUnlock, onRefresh }: CredentialCardProps) {
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const handleTest = async () => {
    try {
      setIsTesting(true);
      setTestResult(null);
      const result = await fetchApi<{ success: boolean; message: string }>(
        `/credentials/vault/${credential.id}/test?tenant_id=${MOCK_TENANT_ID}`,
        { method: "POST" }
      );
      setTestResult(result);
    } catch {
      setTestResult({ success: false, message: "Test failed" });
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <Card className="border-surface-border hover:border-platform-500/30 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon(credential.status)}
            <div>
              <p className="text-sm font-medium text-slate-200">
                {credential.site_name}
              </p>
              <p className="text-xs text-slate-500">{credential.email}</p>
            </div>
          </div>
          {getStatusBadge(credential.status)}
        </div>

        <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-surface-border">
          <div>
            <p className="text-[10px] text-slate-500 uppercase">Health</p>
            <p className={`text-sm font-mono font-bold ${getHealthColor(credential.health_score)}`}>
              {credential.health_score}%
            </p>
          </div>
          <div>
            <p className="text-[10px] text-slate-500 uppercase">Used</p>
            <p className="text-sm font-mono text-slate-300">{credential.use_count}x</p>
          </div>
          <div>
            <p className="text-[10px] text-slate-500 uppercase">Last</p>
            <p className="text-sm text-slate-400">{timeAgo(credential.last_used_at)}</p>
          </div>
        </div>

        {credential.last_failure_reason && (
          <p className="text-xs text-red-400/70 mt-2 truncate">
            {credential.last_failure_reason}
          </p>
        )}

        {testResult && (
          <div
            className={`mt-2 p-2 rounded text-xs ${
              testResult.success
                ? "bg-emerald-500/10 text-emerald-400"
                : "bg-red-500/10 text-red-400"
            }`}
          >
            {testResult.message}
          </div>
        )}

        <div className="flex items-center gap-2 mt-3">
          <Button size="sm" variant="outline" onClick={handleTest} disabled={isTesting}>
            <TestTube className="w-3 h-3 mr-1" />
            Test
          </Button>
          {credential.status === "locked" && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onUnlock?.(credential.id)}
            >
              <Unlock className="w-3 h-3 mr-1" />
              Unlock
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
