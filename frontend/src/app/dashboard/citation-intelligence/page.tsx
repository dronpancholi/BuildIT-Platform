'use client';

import { useQuery } from '@tanstack/react-query';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';
import { useState } from 'react';

export default function CitationIntelligencePage() {
  const [clientId, setClientId] = useState('');
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => fetchApi(`/clients?tenant_id=${MOCK_TENANT_ID}`),
  });

  const { data: projects } = useQuery({
    queryKey: ['citation-projects', clientId],
    queryFn: () => fetchApi(`/citations/projects?tenant_id=${MOCK_TENANT_ID}`),
    enabled: !!clientId,
  });

  const projectList = (projects as any)?.data || [];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Citation Intelligence</h1>

      <select
        value={clientId}
        onChange={(e) => setClientId(e.target.value)}
        className="border rounded-lg px-3 py-2"
      >
        <option value="">Select client...</option>
        {((clients as any)?.data || []).map((c: any) => (
          <option key={c.id} value={c.id}>{c.name} ({c.domain})</option>
        ))}
      </select>

      {projectList.length === 0 && clientId && (
        <p className="text-gray-500">No citation projects found for this client.</p>
      )}

      {projectList.map((project: any) => (
        <ProjectCard key={project.id} projectId={project.id} projectName={project.business_name} />
      ))}
    </div>
  );
}

function ProjectCard({ projectId, projectName }: { projectId: string; projectName: string }) {
  const { data: intel } = useQuery({
    queryKey: ['citation-intel', projectId],
    queryFn: () => fetchApi(`/citation-intelligence/project/${projectId}?tenant_id=${MOCK_TENANT_ID}`),
  });

  const { data: recs } = useQuery({
    queryKey: ['citation-recs', projectId],
    queryFn: () => fetchApi(`/citation-intelligence/project/${projectId}/recommendations?tenant_id=${MOCK_TENANT_ID}`),
  });

  const data = (intel as any)?.data;
  const recList = (recs as any)?.data?.recommendations || [];

  if (!data) return <div className="border rounded-lg p-4 animate-pulse h-32" />;

  const tierColors: Record<string, string> = {
    EXCELLENT: 'bg-green-100 text-green-800',
    GOOD: 'bg-blue-100 text-blue-800',
    FAIR: 'bg-yellow-100 text-yellow-800',
    POOR: 'bg-orange-100 text-orange-800',
    CRITICAL: 'bg-red-100 text-red-800',
    NO_DATA: 'bg-gray-100 text-gray-600',
  };

  return (
    <div className="border rounded-lg p-4 space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="font-bold text-lg">{projectName}</h3>
        <div className="text-right">
          <div className="text-3xl font-bold">{data.health?.score}</div>
          <span className={`text-xs px-2 py-1 rounded-full ${tierColors[data.health?.tier] || 'bg-gray-100'}`}>
            {data.health?.tier}
          </span>
        </div>
      </div>

      {/* Health Breakdown */}
      {data.health?.breakdown && (
        <div className="grid grid-cols-5 gap-2">
          {Object.entries(data.health.breakdown).map(([key, val]: [string, any]) => (
            <div key={key} className="text-center">
              <div className="text-sm font-medium">{val.score ?? val.penalty ?? 0}/{val.max ?? 50}</div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                <div
                  className="bg-blue-600 h-2 rounded-full"
                  style={{ width: `${Math.max(0, ((val.score ?? 0) / (val.max ?? 50)) * 100)}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 mt-1">{key.replace(/_/g, ' ')}</div>
            </div>
          ))}
        </div>
      )}

      {/* NAP Confidence */}
      <div className="border-t pt-3">
        <h4 className="font-medium text-sm mb-2">NAP Confidence: {data.nap_confidence?.confidence}%</h4>
        <div className="text-xs text-gray-500">
          Completeness: {data.nap_confidence?.nap_completeness?.percentage}% | 
          Social: {data.nap_confidence?.profile_completeness?.social_profiles ? 'Yes' : 'No'} |
          Hours: {data.nap_confidence?.profile_completeness?.business_hours ? 'Yes' : 'No'}
        </div>
      </div>

      {/* Site Scores */}
      {data.site_scores?.length > 0 && (
        <div className="border-t pt-3">
          <h4 className="font-medium text-sm mb-2">Site Quality Scores</h4>
          <div className="space-y-1">
            {data.site_scores.map((site: any, i: number) => (
              <div key={i} className="flex justify-between items-center text-sm">
                <span>{site.site_name} (DA: {site.domain_authority})</span>
                <div className="flex gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded ${site.quality_tier === 'A' ? 'bg-green-100' : site.quality_tier === 'B' ? 'bg-blue-100' : 'bg-gray-100'}`}>
                    Q: {site.quality_score}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded ${site.probability_tier === 'HIGH' ? 'bg-green-100' : site.probability_tier === 'MEDIUM' ? 'bg-yellow-100' : 'bg-red-100'}`}>
                    P: {site.success_probability}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {recList.length > 0 && (
        <div className="border-t pt-3">
          <h4 className="font-medium text-sm mb-2">Site Recommendations ({recList.length})</h4>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {recList.map((rec: any, i: number) => (
              <div key={i} className="flex justify-between items-center text-sm border-b pb-1">
                <div>
                  <span className="font-medium">{rec.site_name}</span>
                  <span className="text-xs text-gray-500 ml-2">DA: {rec.domain_authority}</span>
                </div>
                <div className="text-right">
                  <div className="font-bold">{rec.priority_score}</div>
                  <div className="text-xs text-gray-400">{rec.reasons?.join(', ')}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
