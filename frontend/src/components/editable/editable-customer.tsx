"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchApi, MOCK_TENANT_ID } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Edit2, Save, X, Check, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

interface EditableCustomerProps {
  customerId: string;
  onSuccess?: () => void;
}

export function EditableCustomer({ customerId, onSuccess }: EditableCustomerProps) {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState<any>(null);

  const { data: client, isLoading } = useQuery({
    queryKey: ["client", customerId],
    queryFn: () => fetchApi(`/clients/${customerId}`),
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) =>
      fetchApi(`/clients/${customerId}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["client", customerId] });
      queryClient.invalidateQueries({ queryKey: ["clients"] });
      setIsEditing(false);
      onSuccess?.();
    },
  });

  if (isLoading || !client) {
    return <div>Loading...</div>;
  }

  const customerData = formData || client.data || client;

  const handleSave = () => {
    updateMutation.mutate(formData);
  };

  const handleCancel = () => {
    setFormData(null);
    setIsEditing(false);
  };

  const startEditing = () => {
    setFormData(customerData);
    setIsEditing(true);
  };

  const updateField = (field: string, value: string) => {
    setFormData((prev: any) => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <Card className="bg-surface-card border-surface-border">
      <CardHeader className="flex flex-row items-center justify-between pb-4">
        <div>
          <CardTitle className="text-sm font-medium text-slate-400">
            {isEditing ? "Editing Customer" : "Customer Details"}
          </CardTitle>
          {!isEditing && (
            <div className="flex items-center gap-2 mt-2">
              <h2 className="text-xl font-bold text-slate-100">
                {customerData.name}
              </h2>
              <Badge variant="outline" className="text-xs">
                {customerData.status || "Active"}
              </Badge>
            </div>
          )}
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
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={(formData || customerData).name || ""}
                  onChange={(e) => updateField("name", e.target.value)}
                  className="bg-surface-darker border-surface-border"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="domain">Domain</Label>
                <Input
                  id="domain"
                  value={(formData || customerData).domain || ""}
                  onChange={(e) => updateField("domain", e.target.value)}
                  className="bg-surface-darker border-surface-border"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="niche">Niche</Label>
                <Input
                  id="niche"
                  value={(formData || customerData).niche || ""}
                  onChange={(e) => updateField("niche", e.target.value)}
                  className="bg-surface-darker border-surface-border"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="industry">Industry</Label>
                <Input
                  id="industry"
                  value={(formData || customerData).industry || ""}
                  onChange={(e) => updateField("industry", e.target.value)}
                  className="bg-surface-darker border-surface-border"
                />
              </div>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-slate-500">Name</p>
              <p className="text-sm font-medium">{customerData.name}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Domain</p>
              <p className="text-sm font-medium">{customerData.domain}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Niche</p>
              <p className="text-sm font-medium">{customerData.niche}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Industry</p>
              <p className="text-sm font-medium">{customerData.industry || "N/A"}</p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
