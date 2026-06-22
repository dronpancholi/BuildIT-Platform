'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface HealthComponent {
  name: string;
  status: 'healthy' | 'warning' | 'critical';
  response_time_ms: number;
  last_check: string;
  error: string | null;
  action: string | null;
  note?: string;
}

interface HealthResponse {
  success: boolean;
  data: {
    overall_status: string;
    components: HealthComponent[];
    broken_count: number;
    total_count: number;
    summary: string;
  };
}

const statusConfig = {
  healthy: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-50', badge: 'bg-green-100 text-green-800' },
  warning: { icon: AlertTriangle, color: 'text-yellow-500', bg: 'bg-yellow-50', badge: 'bg-yellow-100 text-yellow-800' },
  critical: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-50', badge: 'bg-red-100 text-red-800' },
};

export default function SystemHealthPage() {
  const { data, isLoading, refetch } = useQuery<HealthResponse>({
    queryKey: ['system-health'],
    queryFn: () => fetchApi(`/system/health?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="p-8">Loading system health...</div>;

  const health = data?.data;
  const overallConfig = statusConfig[health?.overall_status as keyof typeof statusConfig] || statusConfig.critical;

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">System Health Command Center</h1>
          <p className="text-muted-foreground mt-1">Real-time status of all platform components</p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Overall Status Banner */}
      <div className={`p-4 rounded-lg ${overallConfig.bg} border`}>
        <div className="flex items-center gap-3">
          <overallConfig.icon className={`h-6 w-6 ${overallConfig.color}`} />
          <div>
            <span className="font-semibold text-lg">{health?.summary || 'Checking...'}</span>
            <p className="text-sm text-muted-foreground">Last checked: {health?.components?.[0]?.last_check}</p>
          </div>
        </div>
      </div>

      {/* Component Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {health?.components?.map((component) => {
          const config = statusConfig[component.status];
          return (
            <Card key={component.name}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-medium">{component.name}</CardTitle>
                  <Badge className={config.badge}>{component.status.toUpperCase()}</Badge>
                </div>
              </CardHeader>
              <CardContent>
                {component.response_time_ms > 0 && (
                  <p className="text-xs text-muted-foreground">Response: {component.response_time_ms}ms</p>
                )}
                {component.error && (
                  <div className="mt-2 p-2 bg-red-50 rounded text-xs text-red-700">
                    <p className="font-medium">Error:</p>
                    <p>{component.error}</p>
                  </div>
                )}
                {component.action && (
                  <div className="mt-2 p-2 bg-blue-50 rounded text-xs text-blue-700">
                    <p className="font-medium">How to fix:</p>
                    <p>{component.action}</p>
                  </div>
                )}
                {component.note && (
                  <p className="mt-2 text-xs text-muted-foreground italic">{component.note}</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
