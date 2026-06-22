'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';
import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { CheckCircle, XCircle, Settings, TestTube, ExternalLink } from 'lucide-react';

interface Provider {
  id: string; name: string; category: string; description: string;
  required_for: string[]; config_fields: string[];
  test_url: string | null; docs_url: string | null;
  status: 'configured' | 'not_configured' | 'active' | 'available_free' | 'available_local';
}

interface CatalogResponse { success: boolean; data: Provider[]; }

const statusConfig: Record<string, { badge: string; label: string }> = {
  configured: { badge: 'bg-green-100 text-green-800', label: 'CONFIGURED' },
  active: { badge: 'bg-green-100 text-green-800', label: 'ACTIVE' },
  not_configured: { badge: 'bg-gray-100 text-gray-600', label: 'NOT CONFIGURED' },
  available_free: { badge: 'bg-blue-100 text-blue-800', label: 'FREE TIER' },
  available_local: { badge: 'bg-purple-100 text-purple-800', label: 'LOCAL' },
};

export default function ProvidersV2Page() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState('');
  const [testResults, setTestResults] = useState<Record<string, { status: string; message: string }>>({});

  const { data, isLoading } = useQuery<CatalogResponse>({
    queryKey: ['provider-catalog'],
    queryFn: () => fetchApi(`/providers/catalog?tenant_id=${MOCK_TENANT_ID}`),
  });

  const configureMutation = useMutation({
    mutationFn: (config: { provider: string; api_key: string }) =>
      fetchApi(`/providers/configure?tenant_id=${MOCK_TENANT_ID}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['provider-catalog'] }); setEditingId(null); setApiKey(''); },
  });

  const testMutation = useMutation({
    mutationFn: (providerId: string) =>
      fetchApi(`/providers/${providerId}/test?tenant_id=${MOCK_TENANT_ID}`, { method: 'POST' }),
    onSuccess: (data: any, providerId: string) => {
      setTestResults(prev => ({ ...prev, [providerId]: data.data }));
    },
  });

  if (isLoading) return <div className="p-8">Loading providers...</div>;

  const providers = data?.data || [];
  const categories = [...new Set(providers.map(p => p.category))];

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Provider Management Center</h1>
        <p className="text-muted-foreground mt-1">Configure API keys and manage external service connections</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">Configured</p>
            <p className="text-2xl font-bold text-green-600">{providers.filter(p => p.status === 'configured' || p.status === 'active').length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">Not Configured</p>
            <p className="text-2xl font-bold text-gray-500">{providers.filter(p => p.status === 'not_configured').length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <p className="text-sm text-muted-foreground">Total</p>
            <p className="text-2xl font-bold">{providers.length}</p>
          </CardContent>
        </Card>
      </div>

      {/* Provider Categories */}
      {categories.map(category => (
        <div key={category}>
          <h2 className="text-lg font-semibold mb-3">{category}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {providers.filter(p => p.category === category).map(provider => {
              const config = statusConfig[provider.status] || statusConfig.not_configured;
              const testResult = testResults[provider.id];
              return (
                <Card key={provider.id}>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">{provider.name}</CardTitle>
                      <Badge className={config.badge}>{config.label}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground mb-3">{provider.description}</p>
                    <div className="text-xs text-muted-foreground mb-3">
                      <p className="font-medium">Required for:</p>
                      <ul className="list-disc list-inside">{provider.required_for.map(f => <li key={f}>{f}</li>)}</ul>
                    </div>

                    {/* Configure Section */}
                    {editingId === provider.id ? (
                      <div className="space-y-2 p-3 bg-gray-50 rounded">
                        <Input type="password" placeholder="API Key" value={apiKey} onChange={e => setApiKey(e.target.value)} />
                        <div className="flex gap-2">
                          <Button size="sm" onClick={() => configureMutation.mutate({ provider: provider.id, api_key: apiKey })}>
                            Save
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => { setEditingId(null); setApiKey(''); }}>Cancel</Button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex gap-2">
                        {provider.config_fields.length > 0 && provider.status !== 'active' && (
                          <Button size="sm" variant="outline" onClick={() => setEditingId(provider.id)}>
                            <Settings className="h-3 w-3 mr-1" /> Configure
                          </Button>
                        )}
                        {provider.test_url && (
                          <Button size="sm" variant="outline" onClick={() => testMutation.mutate(provider.id)}>
                            <TestTube className="h-3 w-3 mr-1" /> Test
                          </Button>
                        )}
                        {provider.docs_url && (
                          <a href={provider.docs_url} target="_blank" rel="noopener noreferrer">
                            <Button size="sm" variant="ghost"><ExternalLink className="h-3 w-3" /></Button>
                          </a>
                        )}
                      </div>
                    )}

                    {/* Test Result */}
                    {testResult && (
                      <div className={`mt-3 p-2 rounded text-xs ${testResult.status === 'connected' ? 'bg-green-50 text-green-700' : testResult.status === 'not_configured' ? 'bg-gray-50 text-gray-600' : 'bg-red-50 text-red-700'}`}>
                        {testResult.message}
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
