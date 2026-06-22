'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';

export default function SEOHealthPage() {
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => fetchApi(`/clients?tenant_id=${MOCK_TENANT_ID}`),
  });

  const clientList = (clients as any)?.data || [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">SEO Health Dashboard</h1>

      <div className="grid grid-cols-1 gap-6">
        {clientList.map((client: any) => (
          <ClientHealthCard key={client.id} clientId={client.id} clientName={client.name} domain={client.domain} />
        ))}
        {clientList.length === 0 && (
          <p className="text-gray-500">No clients found. Add a client first.</p>
        )}
      </div>
    </div>
  );
}

function ClientHealthCard({ clientId, clientName, domain }: { clientId: string; clientName: string; domain: string }) {
  const { data: health } = useQuery({
    queryKey: ['seo-health', clientId],
    queryFn: () => fetchApi(`/seo-health/client/${clientId}?tenant_id=${MOCK_TENANT_ID}`),
  });

  const { data: visibility } = useQuery({
    queryKey: ['visibility', clientId],
    queryFn: () => fetchApi(`/seo-health/visibility/${clientId}?tenant_id=${MOCK_TENANT_ID}`),
  });

  const h = (health as any)?.data;
  const v = (visibility as any)?.data;

  if (!h) return <div className="border rounded-lg p-4 animate-pulse h-32" />;

  const tierColors: Record<string, string> = {
    HEALTHY: 'bg-green-100 text-green-800',
    MODERATE: 'bg-yellow-100 text-yellow-800',
    AT_RISK: 'bg-orange-100 text-orange-800',
    CRITICAL: 'bg-red-100 text-red-800',
    FAILING: 'bg-red-200 text-red-900',
    NO_DATA: 'bg-gray-100 text-gray-600',
  };

  return (
    <div className="border rounded-lg p-4 space-y-4">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="font-bold text-lg">{clientName}</h3>
          <p className="text-sm text-gray-500">{domain}</p>
        </div>
        <div className="text-right">
          <div className="text-3xl font-bold">{h.overall_score}</div>
          <span className={`text-xs px-2 py-1 rounded-full ${tierColors[h.tier] || 'bg-gray-100'}`}>{h.tier}</span>
        </div>
      </div>

      {/* Components */}
      <div className="grid grid-cols-5 gap-2">
        {h.components && Object.entries(h.components).map(([key, comp]: [string, any]) => (
          <div key={key} className="text-center">
            <div className="text-sm font-medium">{comp.score}/{comp.max}</div>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
              <div
                className="bg-blue-600 h-2 rounded-full"
                style={{ width: `${(comp.score / comp.max) * 100}%` }}
              />
            </div>
            <div className="text-xs text-gray-500 mt-1">{key.replace(/_/g, ' ')}</div>
            <div className="text-xs text-gray-400">{comp.detail}</div>
          </div>
        ))}
      </div>

      {/* Visibility */}
      {v && (
        <div className="border-t pt-3">
          <h4 className="font-medium text-sm mb-2">Visibility Score: {v.overall_score}/100 ({v.tier})</h4>
          <div className="grid grid-cols-4 gap-2">
            {v.components && Object.entries(v.components).map(([key, comp]: [string, any]) => (
              <div key={key} className="text-center">
                <div className="text-sm font-medium">{comp.score}/{comp.max}</div>
                <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1">
                  <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${(comp.score / comp.max) * 100}%` }} />
                </div>
                <div className="text-xs text-gray-500">{key.replace(/_/g, ' ')}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
