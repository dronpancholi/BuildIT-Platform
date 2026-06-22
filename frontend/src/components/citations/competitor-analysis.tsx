"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, Trash2, ExternalLink, Users, AlertTriangle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface Competitor {
  id: string;
  competitor_name: string;
  competitor_domain: string | null;
}

interface Gap {
  site_id: string;
  site_name: string;
  site_url: string;
  site_importance: number | null;
  competitor_count: number;
  competitor_names: string[];
  is_client_listed: boolean;
}

interface CompetitorAnalysisProps {
  competitors: Competitor[];
  gaps: Gap[];
  stats: {
    unique_competitors: number;
    total_citations: number;
    unique_sites: number;
  };
  onAddCompetitor: (name: string, domain: string) => Promise<void>;
  onRemoveCompetitor?: (id: string) => void;
}

export function CompetitorAnalysis({
  competitors,
  gaps,
  stats,
  onAddCompetitor,
  onRemoveCompetitor,
}: CompetitorAnalysisProps) {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDomain, setNewDomain] = useState("");
  const [isAdding, setIsAdding] = useState(false);

  const handleAdd = async () => {
    if (!newName.trim() || !newDomain.trim()) return;
    setIsAdding(true);
    try {
      await onAddCompetitor(newName.trim(), newDomain.trim());
      setNewName("");
      setNewDomain("");
      setShowAddDialog(false);
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-3">
        <Card className="border-surface-border bg-surface-card">
          <CardContent className="p-3 text-center">
            <Users className="w-4 h-4 text-platform-400 mx-auto mb-1" />
            <p className="text-lg font-bold text-slate-100">{stats.unique_competitors}</p>
            <p className="text-[10px] text-slate-500 uppercase">Competitors</p>
          </CardContent>
        </Card>
        <Card className="border-surface-border bg-surface-card">
          <CardContent className="p-3 text-center">
            <AlertTriangle className="w-4 h-4 text-orange-400 mx-auto mb-1" />
            <p className="text-lg font-bold text-slate-100">{gaps.length}</p>
            <p className="text-[10px] text-slate-500 uppercase">Gaps Found</p>
          </CardContent>
        </Card>
        <Card className="border-surface-border bg-surface-card">
          <CardContent className="p-3 text-center">
            <ExternalLink className="w-4 h-4 text-green-400 mx-auto mb-1" />
            <p className="text-lg font-bold text-slate-100">{stats.unique_sites}</p>
            <p className="text-[10px] text-slate-500 uppercase">Unique Sites</p>
          </CardContent>
        </Card>
      </div>

      {/* Competitors List */}
      <Card className="border-surface-border bg-surface-card">
        <CardHeader className="p-3 flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-mono text-slate-200">COMPETITORS</CardTitle>
          <Button size="sm" variant="outline" className="h-7" onClick={() => setShowAddDialog(true)}>
            <Plus className="w-3 h-3 mr-1" />
            Add
          </Button>
        </CardHeader>
        <CardContent className="p-3 pt-0">
          {competitors.length === 0 ? (
            <p className="text-xs text-slate-500 text-center py-4">
              No competitors added yet. Add competitor domains to enable gap analysis.
            </p>
          ) : (
            <div className="space-y-2">
              {competitors.map((comp) => (
                <div key={comp.id} className="flex items-center justify-between p-2 rounded bg-surface-hover">
                  <div>
                    <p className="text-sm text-slate-200">{comp.competitor_name}</p>
                    <p className="text-[11px] text-slate-500">{comp.competitor_domain}</p>
                  </div>
                  {onRemoveCompetitor && (
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-6 w-6 p-0 text-slate-500 hover:text-red-400"
                      onClick={() => onRemoveCompetitor(comp.id)}
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Gap Analysis */}
      {gaps.length > 0 && (
        <Card className="border-surface-border bg-surface-card">
          <CardHeader className="p-3">
            <CardTitle className="text-sm font-mono text-slate-200">
              GAP ANALYSIS ({gaps.length} sites)
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 pt-0">
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {gaps.slice(0, 20).map((gap) => (
                <div key={gap.site_id} className="flex items-center justify-between p-2 rounded bg-surface-hover text-xs">
                  <div className="min-w-0">
                    <p className="text-slate-200 truncate">{gap.site_name}</p>
                    <p className="text-[10px] text-slate-500 truncate">{gap.site_url}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant="outline" className="text-[10px]">
                      {gap.competitor_count} competitor(s)
                    </Badge>
                    {gap.site_importance != null && (
                      <span className="text-[10px] text-slate-500">DA {gap.site_importance}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add Competitor Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="font-mono">ADD COMPETITOR</DialogTitle>
            <DialogDescription>
              Add a competitor domain to enable gap analysis.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="comp-name">Competitor Name</Label>
              <Input
                id="comp-name"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="e.g. Smith & Co Plumbing"
              />
            </div>
            <div>
              <Label htmlFor="comp-domain">Domain</Label>
              <Input
                id="comp-domain"
                value={newDomain}
                onChange={(e) => setNewDomain(e.target.value)}
                placeholder="e.g. smithplumbing.com.au"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAdd} disabled={isAdding || !newName.trim() || !newDomain.trim()}>
              {isAdding ? "Adding..." : "Add Competitor"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
