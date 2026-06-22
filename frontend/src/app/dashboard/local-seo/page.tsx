'use client';

import { useQuery, useMutation } from '@tanstack/react-query';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';
import { useState } from 'react';

export default function LocalSEOPage() {
  const [clientId, setClientId] = useState('');
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => fetchApi(`/clients?tenant_id=${MOCK_TENANT_ID}`),
  });

  const { data: localSEO, isLoading } = useQuery({
    queryKey: ['local-seo', clientId],
    queryFn: () => fetchApi(`/local-seo/client/${clientId}?tenant_id=${MOCK_TENANT_ID}`),
    enabled: !!clientId,
  });

  const { data: opportunities } = useQuery({
    queryKey: ['local-opportunities', clientId],
    queryFn: () => fetchApi(`/local-seo/client/${clientId}/opportunities?tenant_id=${MOCK_TENANT_ID}`),
    enabled: !!clientId,
  });

  const clientList = (clients as any)?.data || [];
  const data = (localSEO as any)?.data;
  const opps = (opportunities as any)?.data?.opportunities || [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Local SEO Intelligence</h1>

      <select
        value={clientId}
        onChange={(e) => setClientId(e.target.value)}
        className="border rounded-lg px-3 py-2"
      >
        <option value="">Select client...</option>
        {clientList.map((c: any) => (
          <option key={c.id} value={c.id}>{c.name} ({c.domain})</option>
        ))}
      </select>

      {isLoading && <div className="animate-pulse h-32 bg-gray-100 rounded-lg" />}

      {data && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Business Profile */}
          <div className="bg-white border rounded-lg p-4">
            <h3 className="font-bold mb-3">Business Profile</h3>
            <div className="space-y-2 text-sm">
              <div><span className="text-gray-500">Name:</span> {data.business_profile?.name}</div>
              <div><span className="text-gray-500">City:</span> {data.business_profile?.city}</div>
              <div><span className="text-gray-500">State:</span> {data.business_profile?.state}</div>
              <div><span className="text-gray-500">Country:</span> {data.business_profile?.country}</div>
            </div>
          </div>

          {/* Local Authority */}
          <div className="bg-white border rounded-lg p-4">
            <h3 className="font-bold mb-3">Local Authority</h3>
            <div className="text-center">
              <div className="text-4xl font-bold">{data.local_authority?.score}</div>
              <div className="text-sm text-gray-500">/100</div>
            </div>
            <div className="mt-3 space-y-1">
              {data.local_authority && Object.entries(data.local_authority).filter(([k]) => !['score'].includes(k)).map(([key, val]: [string, any]) => (
                <div key={key} className="flex justify-between text-xs">
                  <span className="text-gray-500">{key.replace(/_/g, ' ')}</span>
                  <span>{val.score}/{val.max}</span>
                </div>
              ))}
            </div>
          </div>

          {/* NAP Consistency */}
          <div className="bg-white border rounded-lg p-4">
            <h3 className="font-bold mb-3">NAP Consistency</h3>
            <div className="text-center">
              <div className="text-4xl font-bold">{data.nap_consistency?.score}%</div>
              <div className="text-sm text-gray-500">Consistent Fields</div>
            </div>
            <div className="mt-3 text-xs text-gray-500">
              {data.nap_consistency?.consistent_fields}/{data.nap_consistency?.total_fields} fields match
            </div>
            {data.nap_consistency?.inconsistencies?.length > 0 && (
              <div className="mt-2 text-xs text-red-600">
                {data.nap_consistency.inconsistencies.map((inc: any, i: number) => (
                  <div key={i}>{inc.field}: "{inc.business_profile}" vs "{inc.citation_project}"</div>
                ))}
              </div>
            )}
          </div>

          {/* Citation Coverage */}
          <div className="bg-white border rounded-lg p-4">
            <h3 className="font-bold mb-3">Citation Coverage</h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{data.citation_coverage?.live_citations}</div>
                <div className="text-xs text-gray-500">Live</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{data.citation_coverage?.pending_submissions}</div>
                <div className="text-xs text-gray-500">Pending</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{data.citation_coverage?.failed_submissions}</div>
                <div className="text-xs text-gray-500">Failed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{data.citation_coverage?.coverage_rate}%</div>
                <div className="text-xs text-gray-500">Coverage</div>
              </div>
            </div>
          </div>

          {/* Opportunities */}
          <div className="lg:col-span-2 bg-white border rounded-lg p-4">
            <h3 className="font-bold mb-3">Citation Opportunities ({opps.length})</h3>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {opps.length === 0 && <p className="text-sm text-gray-500">No opportunities found. Add citation projects to see recommendations.</p>}
              {opps.map((opp: any, i: number) => (
                <div key={i} className="flex justify-between items-center border-b pb-2">
                  <div>
                    <div className="font-medium text-sm">{opp.site_name}</div>
                    <div className="text-xs text-gray-500">DA: {opp.domain_authority} | {opp.category} | {opp.is_free ? 'Free' : 'Paid'}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold">{opp.priority_score}</div>
                    <div className="text-xs text-gray-400">Priority</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
