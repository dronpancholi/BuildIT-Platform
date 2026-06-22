'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchApi, MOCK_TENANT_ID } from '@/lib/api';
import { useState } from 'react';

const ENDPOINTS = {
  COMPARE: '/competitor-intelligence/compare',
  CONTENT_GAP: '/competitor-intelligence/content-gap',
  BACKLINK_GAP: '/competitor-intelligence/backlink-gap',
};

export default function CompetitorIntelligencePage() {
  const queryClient = useQueryClient();
  const [clientDomain, setClientDomain] = useState('');
  const [competitorDomain, setCompetitorDomain] = useState('');
  const [activeTab, setActiveTab] = useState<'compare' | 'content' | 'backlink'>('compare');

  const compareMutation = useMutation({
    mutationFn: (data: { client_domain: string; competitor_domain: string }) =>
      fetchApi(`${ENDPOINTS.COMPARE}?tenant_id=${MOCK_TENANT_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
  });

  const contentGapMutation = useMutation({
    mutationFn: (data: { client_domain: string; competitor_domain: string }) =>
      fetchApi(`${ENDPOINTS.CONTENT_GAP}?tenant_id=${MOCK_TENANT_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
  });

  const backlinkGapMutation = useMutation({
    mutationFn: (data: { client_domain: string; competitor_domain: string }) =>
      fetchApi(`${ENDPOINTS.BACKLINK_GAP}?tenant_id=${MOCK_TENANT_ID}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
  });

  const handleAnalyze = () => {
    if (!clientDomain || !competitorDomain) return;
    const data = { client_domain: clientDomain, competitor_domain: competitorDomain };
    compareMutation.mutate(data);
    contentGapMutation.mutate(data);
    backlinkGapMutation.mutate(data);
  };

  const compareData = compareMutation.data as any;
  const contentData = contentGapMutation.data as any;
  const backlinkData = backlinkGapMutation.data as any;

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Competitor Intelligence</h1>

      {/* Input */}
      <div className="flex gap-4 items-end">
        <div className="flex-1">
          <label className="block text-sm font-medium mb-1">Your Domain</label>
          <input
            type="text"
            value={clientDomain}
            onChange={(e) => setClientDomain(e.target.value)}
            placeholder="acme.com"
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium mb-1">Competitor Domain</label>
          <input
            type="text"
            value={competitorDomain}
            onChange={(e) => setCompetitorDomain(e.target.value)}
            placeholder="competitor.com"
            className="w-full border rounded-lg px-3 py-2"
          />
        </div>
        <button
          onClick={handleAnalyze}
          disabled={!clientDomain || !competitorDomain || compareMutation.isPending}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg disabled:opacity-50"
        >
          {compareMutation.isPending ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>

      <div className="flex gap-2 border-b">
        {(['compare', 'content', 'backlink'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 font-medium ${activeTab === tab ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-500'}`}
          >
            {tab === 'compare' ? 'Domain Comparison' : tab === 'content' ? 'Content Gap' : 'Backlink Gap'}
          </button>
        ))}
      </div>

      {/* Results */}
      {activeTab === 'compare' && compareData && (
        <div className="grid grid-cols-2 gap-6">
          {['client', 'competitor'].map((side) => (
            <div key={side} className="bg-white border rounded-lg p-4">
              <h3 className="font-bold text-lg mb-3">{side === 'client' ? 'Your Domain' : 'Competitor'}</h3>
              <div className="space-y-2">
                {Object.entries(compareData.data[side] || {}).map(([key, val]) => (
                  <div key={key} className="flex justify-between">
                    <span className="text-gray-600">{key.replace(/_/g, ' ')}</span>
                    <span className="font-medium">{String(val)}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
          <div className="col-span-2 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <h3 className="font-bold mb-2">Gaps</h3>
            <div className="grid grid-cols-3 gap-4">
              {compareData.data.gaps && Object.entries(compareData.data.gaps).map(([key, val]) => (
                <div key={key} className="text-center">
                  <div className="text-2xl font-bold">{String(val)}</div>
                  <div className="text-sm text-gray-600">{key.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'content' && contentData && (
        <div className="space-y-4">
          <div className="bg-blue-50 border rounded-lg p-4">
            <h3 className="font-bold mb-2">Keyword Gap Summary</h3>
            <pre className="text-sm">{JSON.stringify(contentData.data.summary, null, 2)}</pre>
          </div>
          {contentData.data.opportunities?.length > 0 ? (
            <div className="space-y-2">
              {contentData.data.opportunities.map((opp: any, i: number) => (
                <div key={i} className="bg-white border rounded-lg p-3 flex justify-between items-center">
                  <div>
                    <span className="font-medium">{opp.keyword}</span>
                    <span className="text-sm text-gray-500 ml-2">Volume: {opp.search_volume}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold">{opp.opportunity_score}</div>
                    <div className="text-xs text-gray-500">Opportunity</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No keyword gaps found. Add keywords to both domains for comparison.</p>
          )}
          <p className="text-xs text-gray-400">{contentData.data.limitation}</p>
        </div>
      )}

      {activeTab === 'backlink' && backlinkData && (
        <div className="space-y-4">
          <div className="bg-blue-50 border rounded-lg p-4">
            <h3 className="font-bold mb-2">Backlink Gap Summary</h3>
            <div className="grid grid-cols-4 gap-4">
              {backlinkData.data.summary && Object.entries(backlinkData.data.summary).map(([key, val]) => (
                <div key={key} className="text-center">
                  <div className="text-2xl font-bold">{String(val)}</div>
                  <div className="text-sm text-gray-600">{key.replace(/_/g, ' ')}</div>
                </div>
              ))}
            </div>
          </div>
          {backlinkData.data.opportunities?.length > 0 ? (
            <div className="space-y-2">
              {backlinkData.data.opportunities.map((opp: any, i: number) => (
                <div key={i} className="bg-white border rounded-lg p-3 flex justify-between items-center">
                  <div>
                    <span className="font-medium">{opp.domain}</span>
                    <span className="text-sm text-gray-500 ml-2">DA: {opp.domain_authority}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold">{opp.opportunity_score}</div>
                    <div className="text-xs text-gray-500">Score</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No backlink gaps found. Competitor may not be in your prospect database.</p>
          )}
          <p className="text-xs text-gray-400">{backlinkData.data.limitation}</p>
        </div>
      )}
    </div>
  );
}
