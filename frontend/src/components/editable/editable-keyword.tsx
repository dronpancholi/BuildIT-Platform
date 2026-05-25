"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Edit2, Save, X, Search } from "lucide-react";

interface EditableKeywordProps {
  keywordId: string;
  onSuccess?: () => void;
}

export function EditableKeyword({ keywordId, onSuccess }: EditableKeywordProps) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<any>(null);

  const { data: keyword, isLoading } = useQuery({
    queryKey: ["keyword", keywordId],
    queryFn: () => fetchApi(`/keywords/${keywordId}`),
    enabled: !!keywordId,
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) =>
      fetchApi(`/keywords/${keywordId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["keyword", keywordId] });
      queryClient.invalidateQueries({ queryKey: ["keywords"] });
      setIsEditing(false);
      onSuccess?.();
    },
  });

  if (isLoading || !keyword) {
    return <div className="text-slate-500 text-sm">Loading...</div>;
  }

  const keywordData = formData || keyword.data || keyword;

  const handleSave = () => {
    if (!formData) return;
    updateMutation.mutate(formData);
  };

  const handleCancel = () => {
    setFormData(null);
    setIsEditing(false);
  };

  const startEditing = () => {
    setFormData(keywordData);
    setIsEditing(true);
  };

  const updateField = (field: string, value: any) => {
    setFormData((prev: any) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <Card className="bg-surface-card border-surface-border">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center gap-2">
          <Search className="w-4 h-4 text-platform-400" />
          <div>
            <CardTitle className="text-sm font-medium text-slate-400">
              {isEditing ? "Editing Keyword" : "Keyword Details"}
            </CardTitle>
            {!isEditing && (
              <h2 className="text-lg font-bold text-slate-100 mt-1">
                {keywordData.keyword}
              </h2>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!isEditing ? (
            <Button
              size="sm"
              variant="outline"
              onClick={startEditing}
              className="h-8 border-platform-500/50 text-platform-400 hover:bg-platform-500/10"
            >
              <Edit2 className="w-3.5 h-3.5 mr-1" />
              Edit
            </Button>
          ) : (
            <>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancel}
                className="h-8 border-slate-600 text-slate-400 hover:bg-slate-800"
                disabled={updateMutation.isPending}
              >
                <X className="w-3.5 h-3.5 mr-1" />
                Cancel
              </Button>
              <Button
                size="sm"
                variant="default"
                onClick={handleSave}
                className="h-8 bg-platform-600 hover:bg-platform-500"
                disabled={updateMutation.isPending}
              >
                <Save className="w-3.5 h-3.5 mr-1" />
                Save
              </Button>
            </>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isEditing ? (
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="keyword">Keyword</Label>
              <Input
                id="keyword"
                value={(formData || keywordData).keyword || ""}
                onChange={(e) => updateField("keyword", e.target.value)}
                className="bg-surface-darker border-surface-border"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="search_volume">Search Volume</Label>
              <Input
                id="search_volume"
                type="number"
                value={(formData || keywordData).search_volume || 0}
                onChange={(e) => updateField("search_volume", parseInt(e.target.value))}
                className="bg-surface-darker border-surface-border"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="difficulty">Difficulty (0-100)</Label>
              <Input
                id="difficulty"
                type="number"
                min="0"
                max="100"
                value={(formData || keywordData).difficulty || 0}
                onChange={(e) => updateField("difficulty", parseInt(e.target.value))}
                className="bg-surface-darker border-surface-border"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="cpc">CPC ($)</Label>
              <Input
                id="cpc"
                type="number"
                step="0.01"
                value={(formData || keywordData).cpc || 0}
                onChange={(e) => updateField("cpc", parseFloat(e.target.value))}
                className="bg-surface-darker border-surface-border"
              />
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-slate-500">Keyword</p>
              <p className="text-sm font-medium">{keywordData.keyword}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Search Volume</p>
              <p className="text-sm font-medium">{keywordData.search_volume?.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Difficulty</p>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium">{keywordData.difficulty}</p>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[10px] border-0",
                    keywordData.difficulty < 30
                      ? "bg-emerald-500/10 text-emerald-400"
                      : keywordData.difficulty < 70
                      ? "bg-amber-500/10 text-amber-400"
                      : "bg-red-500/10 text-red-400"
                  )}
                >
                  {keywordData.difficulty < 30 ? "Easy" : keywordData.difficulty < 70 ? "Medium" : "Hard"}
                </Badge>
              </div>
            </div>
            <div>
              <p className="text-xs text-slate-500">CPC</p>
              <p className="text-sm font-medium">${keywordData.cpc?.toFixed(2)}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
