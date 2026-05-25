"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Edit2, Save, X, FileText } from "lucide-react";

export function EditableReport({ reportId, onSuccess }: any) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<any>(null);

  const { data: report, isLoading } = useQuery({
    queryKey: ["report", reportId],
    queryFn: () => fetchApi(`/reports/${reportId}`),
    enabled: !!reportId,
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => fetchApi(`/reports/${reportId}`, { method: "PATCH", body: JSON.stringify(data) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["report", reportId] });
      setIsEditing(false);
      onSuccess?.();
    },
  });

  if (isLoading || !report) return <div>Loading...</div>;
  const data = formData || report.data || report;

  return (
    <Card className="bg-surface-card border-surface-border">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-platform-400" />
          <div>
            <CardTitle className="text-sm font-medium text-slate-400">{isEditing ? "Editing Report" : "Report Details"}</CardTitle>
            {!isEditing && <h2 className="text-lg font-bold text-slate-100 mt-1">{data.report_type || "Report"}</h2>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {!isEditing ? (
            <Button size="sm" variant="outline" onClick={() => { setFormData(data); setIsEditing(true); }} className="h-8 border-platform-500/50 text-platform-400 hover:bg-platform-500/10">
              <Edit2 className="w-3.5 h-3.5 mr-1" /> Edit
            </Button>
          ) : (
            <>
              <Button size="sm" variant="outline" onClick={() => { setFormData(null); setIsEditing(false); }} className="h-8 border-slate-600 text-slate-400" disabled={updateMutation.isPending}><X className="w-3.5 h-3.5 mr-1" /> Cancel</Button>
              <Button size="sm" variant="default" onClick={() => updateMutation.mutate(formData)} className="h-8 bg-platform-600" disabled={updateMutation.isPending}><Save className="w-3.5 h-3.5 mr-1" /> Save</Button>
            </>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {isEditing ? (
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2"><Label>Report Type</Label><Input value={formData.report_type || ""} onChange={(e) => setFormData({...formData, report_type: e.target.value})} /></div>
            <div className="space-y-2"><Label>Status</Label><Input value={formData.status || ""} onChange={(e) => setFormData({...formData, status: e.target.value})} /></div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <div><p className="text-xs text-slate-500">Type</p><p className="text-sm font-medium">{data.report_type}</p></div>
            <div><p className="text-xs text-slate-500">Status</p><p className="text-sm font-medium">{data.status}</p></div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
