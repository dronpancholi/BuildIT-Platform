'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Activity, Zap, Clock, CheckCircle, XCircle, Pause, AlertTriangle } from 'lucide-react';

interface TemporalStatus {
  success: boolean;
  data: {
    temporal: { status: string; target: string; message: string };
    campaigns: Record<string, number>;
    approvals: Record<string, number>;
    recent_campaigns: Array<{
      id: string; name: string; status: string;
      created_at: string; updated_at: string;
    }>;
    failed_submissions: number;
    queues: Record<string, { status: string; workflows: number }>;
  };
}

const statusColors: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-800',
  active: 'bg-green-100 text-green-800',
  paused: 'bg-yellow-100 text-yellow-800',
  failed: 'bg-red-100 text-red-800',
  completed: 'bg-blue-100 text-blue-800',
  cancelled: 'bg-gray-100 text-gray-600',
  monitoring: 'bg-purple-100 text-purple-800',
};

export default function TemporalOpsPage() {
  const { data, isLoading } = useQuery<TemporalStatus>({
    queryKey: ['temporal-status'],
    queryFn: () => fetchApi(`/temporal/status?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 15000,
  });

  if (isLoading) return <div className="p-8">Loading temporal status...</div>;

  const temporal = data?.data?.temporal;
  const is_connected = temporal?.status === 'connected';

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Temporal Operations Center</h1>
        <p className="text-muted-foreground mt-1">Workflow engine status and controls</p>
      </div>

      {/* Connection Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {is_connected ? (
              <CheckCircle className="h-5 w-5 text-green-500" />
            ) : (
              <XCircle className="h-5 w-5 text-red-500" />
            )}
            Temporal Server
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Badge className={is_connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
              {is_connected ? 'CONNECTED' : 'DISCONNECTED'}
            </Badge>
            <span className="text-sm text-muted-foreground">{temporal?.message}</span>
          </div>
          {!is_connected && (
            <div className="mt-4 p-4 bg-red-50 rounded-lg">
              <p className="font-medium text-red-800">Temporal is not running</p>
              <p className="text-sm text-red-600 mt-1">Workflows cannot execute without Temporal. To start:</p>
              <code className="block mt-2 p-2 bg-white rounded text-sm">temporal server start-dev</code>
              <p className="text-xs text-muted-foreground mt-2">This starts a local Temporal development server on port 7233.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Queue Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Task Queues
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(data?.data?.queues || {}).map(([name, queue]) => (
              <div key={name} className="p-3 border rounded-lg">
                <p className="font-medium text-sm">{name}</p>
                <Badge className={queue.status === 'ready' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>
                  {queue.status.toUpperCase()}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Campaign Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {Object.entries(data?.data?.campaigns || {}).map(([status, count]) => (
          <Card key={status}>
            <CardContent className="pt-4">
              <p className="text-sm text-muted-foreground capitalize">{status}</p>
              <p className="text-2xl font-bold">{count as number}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Recent Campaigns */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Campaigns</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {data?.data?.recent_campaigns?.map((campaign) => (
              <div key={campaign.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <p className="font-medium">{campaign.name}</p>
                  <p className="text-xs text-muted-foreground">Updated: {campaign.updated_at}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge className={statusColors[campaign.status] || 'bg-gray-100'}>
                    {campaign.status.toUpperCase()}
                  </Badge>
                  {campaign.status === 'failed' && (
                    <Button size="sm" variant="outline">Retry</Button>
                  )}
                  {campaign.status === 'active' && (
                    <Button size="sm" variant="outline">Pause</Button>
                  )}
                  {campaign.status === 'paused' && (
                    <Button size="sm" variant="outline">Resume</Button>
                  )}
                </div>
              </div>
            ))}
            {(!data?.data?.recent_campaigns || data.data.recent_campaigns.length === 0) && (
              <p className="text-center text-muted-foreground py-4">No campaigns yet</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Failed Items */}
      {data?.data?.failed_submissions ? (
        <Card className="border-red-200">
          <CardHeader>
            <CardTitle className="text-red-600 flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Failed Items ({data.data.failed_submissions})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              {data.data.failed_submissions} citation submissions have failed.
              <Button variant="link" className="p-0 h-auto ml-1">Go to Recovery →</Button>
            </p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
