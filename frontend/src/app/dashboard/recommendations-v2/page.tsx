'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';
import { useState } from 'react';

export default function RecommendationsV2Page() {
  const [clientId, setClientId] = useState('');
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => fetchApi(`/clients?tenant_id=${MOCK_TENANT_ID}`),
  });

  const { data: recs, isLoading } = useQuery({
    queryKey: ['recs-v2', clientId],
    queryFn: () => fetchApi(`/recommendations-v2/client/${clientId}?tenant_id=${MOCK_TENANT_ID}`),
    enabled: !!clientId,
  });

  const { data: nextAction } = useQuery({
    queryKey: ['next-action', clientId],
    queryFn: () => fetchApi(`/recommendations-v2/client/${clientId}/next-action?tenant_id=${MOCK_TENANT_ID}`),
    enabled: !!clientId,
  });

  const clientList = (clients as any)?.data || [];
  const data = (recs as any)?.data;
  const next = (nextAction as any)?.data;

  const impactColors: Record<string, string> = {
    CRITICAL: 'bg-red-100 text-red-800 border-red-200',
    HIGH: 'bg-orange-100 text-orange-800 border-orange-200',
    MEDIUM: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    LOW: 'bg-blue-100 text-blue-800 border-blue-200',
    MINIMAL: 'bg-gray-100 text-gray-600 border-gray-200',
  };

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Smart Recommendations</h1>

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

      {/* Next Action Banner */}
      {next && next.next_action !== 'No urgent actions needed. All systems appear healthy.' && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-bold text-blue-800 mb-1">What To Do Next</h3>
          <p className="text-blue-700">{next.next_action}</p>
          <div className="mt-2 flex gap-4 text-xs text-blue-600">
            <span>Impact: {next.impact} ({next.impact_score})</span>
            <span>Effort: {next.estimated_effort} ({next.estimated_days} days)</span>
            <span>Confidence: {next.confidence}%</span>
          </div>
          {next.reason && <p className="mt-2 text-sm text-blue-600">{next.reason}</p>}
        </div>
      )}

      {isLoading && <div className="animate-pulse h-32 bg-gray-100 rounded-lg" />}

      {/* Impact Summary */}
      {data && data.total > 0 && (
        <div className="flex gap-4">
          {Object.entries(data.impact_summary).map(([impact, count]) => (
            <div key={impact} className={`px-3 py-1 rounded-full text-sm font-medium ${impactColors[impact] || 'bg-gray-100'}`}>
              {impact}: {String(count)}
            </div>
          ))}
          <div className="text-sm text-gray-500">Total: {data.total}</div>
        </div>
      )}

      {/* Recommendations */}
      {data?.recommendations?.length > 0 ? (
        <div className="space-y-4">
          {data.recommendations.map((rec: any) => (
            <div key={rec.id} className={`border rounded-lg p-4 ${impactColors[rec.impact] || 'bg-gray-50'}`}>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs px-2 py-0.5 rounded-full ${impactColors[rec.impact]}`}>{rec.impact}</span>
                    <span className="font-bold">{rec.problem}</span>
                  </div>
                  <p className="text-sm text-gray-600 mt-1">{rec.reason}</p>
                  <div className="mt-2 text-xs text-gray-500">
                    <strong>Evidence:</strong> {rec.evidence}
                  </div>
                  <div className="mt-2 bg-white rounded p-2 text-sm">
                    <strong>Action:</strong> {rec.suggested_action}
                  </div>
                </div>
                <div className="text-right ml-4">
                  <div className="text-2xl font-bold">{rec.impact_score}</div>
                  <div className="text-xs text-gray-500">Impact</div>
                  <div className="mt-2 text-xs">
                    <div>Confidence: {rec.confidence}%</div>
                    <div>Benefit: {rec.estimated_benefit}</div>
                    <div>Effort: {rec.estimated_effort} ({rec.estimated_days}d)</div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        !isLoading && clientId && (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">No recommendations at this time.</p>
            <p className="text-sm mt-1">All systems appear healthy for this client.</p>
          </div>
        )
      )}
    </div>
  );
}
