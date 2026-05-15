"use client";

import { BarChart3, Network, Target, MessageSquare, GitBranch, Link2, Loader2, TrendingUp, Activity } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";

interface ProspectScore {
  domain: string;
  composite_score: number;
  domain_authority: number;
  relevance_score: number;
  confidence: number;
}

interface AuthorityPropagation {
  source_domain: string;
  target_domain: string;
  propagation_score: number;
  path_length: number;
}

interface OutreachPrediction {
  prospect_domain: string;
  success_probability: number;
  factors: Record<string, number>;
}

interface ResponseProbability {
  domain: string;
  response_probability: number;
  estimated_response_time_hours: number;
}

interface BrokenLink {
  source_url: string;
  target_url: string;
  domain_authority: number;
  relevance_score: number;
}

function scoreColor(score: number): string {
  if (score >= 0.7) return "text-emerald-400";
  if (score >= 0.5) return "text-amber-400";
  return "text-red-400";
}

function scoreBg(score: number): string {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.5) return "bg-amber-500";
  return "bg-red-500";
}

function probabilityLabel(p: number): string {
  if (p >= 0.7) return "HIGH";
  if (p >= 0.4) return "MEDIUM";
  return "LOW";
}

function probabilityColor(p: number): string {
  if (p >= 0.7) return "bg-emerald-500/10 text-emerald-400 border-emerald-500/20";
  if (p >= 0.4) return "bg-amber-500/10 text-amber-400 border-amber-500/20";
  return "bg-red-500/10 text-red-400 border-red-500/20";
}

export default function BacklinkIntelligencePage() {
  const { data: prospects, isLoading: loadingProspects } = useQuery<ProspectScore[]>({
    queryKey: ["backlink-intelligence", "prospects", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/backlink-intelligence/prospects?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 60000,
  });

  const { data: authority, isLoading: loadingAuthority } = useQuery<AuthorityPropagation[]>({
    queryKey: ["backlink-intelligence", "authority", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/backlink-intelligence/authority-propagation?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 120000,
  });

  const { data: predictions, isLoading: loadingPredictions } = useQuery<OutreachPrediction[]>({
    queryKey: ["backlink-intelligence", "predictions", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/backlink-intelligence/outreach-predictions?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 60000,
  });

  const { data: responseProb, isLoading: loadingResponse } = useQuery<ResponseProbability[]>({
    queryKey: ["backlink-intelligence", "response-probability", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/backlink-intelligence/response-probability?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 60000,
  });

  const { data: brokenLinks, isLoading: loadingBroken } = useQuery<BrokenLink[]>({
    queryKey: ["backlink-intelligence", "broken-links", MOCK_TENANT_ID],
    queryFn: () => fetchApi(`/backlink-intelligence/broken-links?tenant_id=${MOCK_TENANT_ID}`),
    refetchInterval: 300000,
  });

  const prospectList = prospects ?? [];
  const authorityList = authority ?? [];
  const predictionList = predictions ?? [];
  const responseList = responseProb ?? [];
  const brokenList = brokenLinks ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">BACKLINK_INTELLIGENCE</h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">Prospect scoring & outreach analytics</p>
        </div>
        <div className="px-3 py-1.5 rounded-md bg-surface-darker border border-surface-border text-xs font-mono text-slate-400 flex items-center gap-2">
          <Network className="w-4 h-4" />
          {prospectList.length} PROSPECTS
        </div>
      </div>

      {/* Prospect Quality Score Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <BarChart3 className="w-5 h-5 text-platform-500" />
            PROSPECT_QUALITY_DISTRIBUTION
          </h3>
          {loadingProspects ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
            </div>
          ) : prospectList.length === 0 ? (
            <div className="text-center py-12 text-slate-500 font-mono">NO_PROSPECT_DATA</div>
          ) : (
            <div className="space-y-3">
              {prospectList.slice(0, 15).map((p, i) => (
                <div key={i} className="space-y-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-300 truncate max-w-[180px]">{p.domain}</span>
                    <span className={`text-xs font-mono font-bold ${scoreColor(p.composite_score)}`}>
                      {Math.round(p.composite_score * 100)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-surface-darker rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${scoreBg(p.composite_score)}`} style={{ width: `${p.composite_score * 100}%` }} />
                  </div>
                  <div className="flex justify-between text-[9px] font-mono text-slate-600">
                    <span>DA: {Math.round(p.domain_authority * 100)}</span>
                    <span>REL: {Math.round(p.relevance_score * 100)}</span>
                    <span>CONF: {Math.round(p.confidence * 100)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Authority Propagation */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <GitBranch className="w-5 h-5 text-purple-500" />
            AUTHORITY_PROPAGATION
          </h3>
          {loadingAuthority ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 text-platform-500 animate-spin" />
            </div>
          ) : authorityList.length === 0 ? (
            <div className="text-center py-12 text-slate-500 font-mono">NO_AUTHORITY_DATA</div>
          ) : (
            <div className="space-y-3">
              {authorityList.slice(0, 10).map((a, i) => (
                <div key={i} className="p-3 rounded-md bg-surface-darker/50 border border-surface-border/50">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-mono text-slate-300 truncate max-w-[120px]">{a.source_domain}</span>
                    <span className="text-[10px] text-slate-600">&rarr;</span>
                    <span className="text-xs font-mono text-slate-300 truncate max-w-[120px]">{a.target_domain}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-surface-darker rounded-full overflow-hidden">
                      <div className="h-full bg-purple-500 rounded-full" style={{ width: `${a.propagation_score * 100}%` }} />
                    </div>
                    <span className="text-[10px] font-mono text-purple-400">{Math.round(a.propagation_score * 100)}%</span>
                  </div>
                  <p className="text-[9px] font-mono text-slate-600 mt-1">Path: {a.path_length} hops</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Outreach Success Prediction */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Target className="w-5 h-5 text-emerald-500" />
            OUTREACH_PREDICTIONS
          </h3>
          {loadingPredictions ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : predictionList.length === 0 ? (
            <div className="text-center py-8 text-slate-500 font-mono">NO_PREDICTION_DATA</div>
          ) : (
            <div className="space-y-2 max-h-[300px] overflow-auto">
              {predictionList.map((p, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded bg-surface-darker/50 border border-surface-border/50">
                  <span className="text-xs font-mono text-slate-300 truncate max-w-[130px]">{p.prospect_domain}</span>
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${probabilityColor(p.success_probability)}`}>
                    {probabilityLabel(p.success_probability)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Response Probability */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <MessageSquare className="w-5 h-5 text-indigo-500" />
            RESPONSE_PROBABILITY
          </h3>
          {loadingResponse ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : responseList.length === 0 ? (
            <div className="text-center py-8 text-slate-500 font-mono">NO_RESPONSE_DATA</div>
          ) : (
            <div className="space-y-2 max-h-[300px] overflow-auto">
              {responseList.map((r, i) => (
                <div key={i} className="p-2 rounded bg-surface-darker/50 border border-surface-border/50">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-mono text-slate-300 truncate max-w-[130px]">{r.domain}</span>
                    <span className={`text-xs font-mono font-bold ${scoreColor(r.response_probability)}`}>
                      {Math.round(r.response_probability * 100)}%
                    </span>
                  </div>
                  <div className="w-full h-1 bg-surface-darker rounded-full overflow-hidden mt-1">
                    <div className={`h-full rounded-full ${scoreBg(r.response_probability)}`} style={{ width: `${r.response_probability * 100}%` }} />
                  </div>
                  <p className="text-[9px] font-mono text-slate-600 mt-1">Est. response: {r.estimated_response_time_hours}h</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Broken Link Opportunities */}
        <div className="glass-panel p-6">
          <h3 className="text-lg font-medium text-slate-200 mb-4 flex items-center gap-2 font-mono">
            <Link2 className="w-5 h-5 text-rose-500" />
            BROKEN_LINK_OPPORTUNITIES
          </h3>
          {loadingBroken ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 text-platform-500 animate-spin" />
            </div>
          ) : brokenList.length === 0 ? (
            <div className="text-center py-8 text-slate-500 font-mono">NO_BROKEN_LINKS</div>
          ) : (
            <div className="space-y-2 max-h-[300px] overflow-auto">
              {brokenList.map((b, i) => (
                <div key={i} className="p-2 rounded bg-surface-darker/50 border border-surface-border/50">
                  <p className="text-[10px] font-mono text-slate-400 truncate">{b.source_url}</p>
                  <p className="text-[9px] font-mono text-slate-600 truncate">&rarr; {b.target_url}</p>
                  <div className="flex gap-2 mt-1 text-[9px] font-mono text-slate-500">
                    <span>DA: {Math.round(b.domain_authority * 100)}</span>
                    <span>REL: {Math.round(b.relevance_score * 100)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
