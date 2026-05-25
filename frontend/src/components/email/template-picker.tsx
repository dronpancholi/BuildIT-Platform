"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { FileText, Search, ChevronDown, ChevronUp, Plus, Archive } from "lucide-react";
import { cn } from "@/lib/utils";

interface Template {
  id: string;
  title: string;
  category: string;
  subject: string;
  body: string;
  variables: string[];
  is_archived: boolean;
}

interface TemplatePickerProps {
  onSelect: (template: Template) => void;
  onCreateNew?: () => void;
}

const CATEGORIES = [
  { value: "all", label: "All Templates" },
  { value: "outreach", label: "Outreach" },
  { value: "followup", label: "Follow-up" },
  { value: "link_insertion", label: "Link Insertion" },
  { value: "partnership", label: "Partnership" },
  { value: "report", label: "Report" },
];

export function TemplatePicker({ onSelect, onCreateNew }: TemplatePickerProps) {
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedTemplate, setExpandedTemplate] = useState<string | null>(null);
  const [showArchived, setShowArchived] = useState(false);

  const { data: templatesData, isLoading } = useQuery({
    queryKey: ["communication-templates", selectedCategory, showArchived],
    queryFn: async () => {
      const params = new URLSearchParams({
        tenant_id: "00000000-0000-0000-0000-000000000001",
        ...(selectedCategory !== "all" && { category: selectedCategory }),
        ...(showArchived && { include_archived: "true" }),
      });
      const response = await fetch("/api/v1/communication-templates?" + params.toString());
      if (!response.ok) {
        return { data: [], total: 0 };
      }
      const result = await response.json();
      return result.data || { data: [], total: 0 };
    },
  });

  const templates: Template[] = (templatesData as any)?.data || [];

  const filteredTemplates = templates.filter((tpl: Template) => {
    const matchesSearch = tpl.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         tpl.subject.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const handleSelect = (template: Template) => {
    onSelect(template);
  };

  return (
    <Card className="bg-surface-card border-surface-border">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-platform-400" />
            <CardTitle className="text-sm font-medium text-slate-400">
              Email Templates
            </CardTitle>
          </div>
          {onCreateNew && (
            <Button
              size="sm"
              variant="outline"
              onClick={onCreateNew}
              className="h-8 border-platform-500/50 text-platform-400 hover:bg-platform-500/10"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              New Template
            </Button>
          )}
        </div>

        <div className="mt-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <Input
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 bg-surface-darker border-surface-border"
            />
          </div>
        </div>

        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={cn(
                "px-3 py-1 text-xs rounded-full transition-colors",
                selectedCategory === cat.value
                  ? "bg-platform-600 text-white"
                  : "bg-surface-darker text-slate-400 hover:text-slate-200"
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-platform-500" />
          </div>
        ) : filteredTemplates.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            {searchQuery ? "No templates match your search" : "No templates found"}
            {onCreateNew && (
              <Button
                variant="link"
                onClick={onCreateNew}
                className="text-platform-400 mt-2"
              >
                Create your first template
              </Button>
            )}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredTemplates.map((template) => (
              <div
                key={template.id}
                className="p-3 rounded-lg border transition-colors cursor-pointer bg-surface-darker border-surface-border hover:border-platform-500/50"
                onClick={() => handleSelect(template)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-sm font-medium text-slate-200">
                        {template.title}
                      </h4>
                      <Badge
                        variant="outline"
                        className="text-[10px] border-slate-600 text-slate-400"
                      >
                        {template.category}
                      </Badge>
                    </div>
                    <p className="text-xs text-slate-500 mb-2">
                      {template.subject}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-slate-600">
                      <span>{template.variables?.length || 0} variables</span>
                      {template.variables && template.variables.length > 0 && (
                        <span className="flex gap-1">
                          {template.variables.slice(0, 3).map((v) => (
                            <span
                              key={v}
                              className="text-platform-400 bg-platform-500/10 px-1 rounded"
                            >
                              {v}
                            </span>
                          ))}
                          {template.variables.length > 3 && (
                            <span className="text-slate-500">
                              +{template.variables.length - 3}
                            </span>
                          )}
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setExpandedTemplate(
                        expandedTemplate === template.id ? null : template.id
                      );
                    }}
                    className="text-slate-500 hover:text-slate-300"
                  >
                    {expandedTemplate === template.id ? (
                      <ChevronUp className="w-4 h-4" />
                    ) : (
                      <ChevronDown className="w-4 h-4" />
                    )}
                  </button>
                </div>

                {expandedTemplate === template.id && (
                  <div className="mt-3 pt-3 border-t border-slate-600">
                    <p className="text-xs text-slate-400 whitespace-pre-wrap">
                      {template.body}
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <div className="mt-4 flex items-center justify-center">
          <button
            onClick={() => setShowArchived(!showArchived)}
            className="text-xs text-slate-500 hover:text-slate-400 flex items-center gap-1"
          >
            <Archive className="w-3 h-3" />
            {showArchived ? "Hide" : "Show"} archived templates
          </button>
        </div>
      </CardContent>
    </Card>
  );
}
