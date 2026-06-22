"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Search, MapPin, Building2, Globe, RefreshCw, Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ProjectCard } from "@/components/citations/project-card";
import { StatusBadge } from "@/components/citations/status-badge";
import { citationApi, type CitationProject, type CitationSubmission } from "@/lib/api";

export default function CitationsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<CitationProject[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newProject, setNewProject] = useState({
    business_name: "",
    website_url: "",
    category: "",
    description: "",
    phone: "",
    email: "",
    city: "",
    state: "",
    country: "Australia",
  });

  const loadProjects = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await citationApi.listProjects();
      setProjects(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load projects");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async () => {
    if (!newProject.business_name.trim()) return;
    try {
      setIsCreating(true);
      const created = await citationApi.createProject(newProject);
      setProjects((prev) => [created, ...prev]);
      setShowCreateDialog(false);
      setNewProject({
        business_name: "",
        website_url: "",
        category: "",
        description: "",
        phone: "",
        email: "",
        city: "",
        state: "",
        country: "Australia",
      });
      router.push(`/dashboard/citations/${created.id}`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to create project");
    } finally {
      setIsCreating(false);
    }
  };

  const filteredProjects = projects.filter((p) =>
    p.business_name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-100 tracking-tight font-mono">
            CITATION_TRACKER
          </h1>
          <p className="text-slate-400 mt-1 font-mono text-sm uppercase tracking-wider">
            Manual Directory Submission Tracker
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Project
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-sm">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <Input
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Content */}
      {isLoading ? (
        <LoadingSpinner size="lg" className="py-20" />
      ) : error ? (
        <Card className="border-red-500/20 bg-red-500/5">
          <CardContent className="p-6 text-center">
            <p className="text-red-400">{error}</p>
            <Button variant="outline" className="mt-4" onClick={loadProjects}>
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : filteredProjects.length === 0 ? (
        <EmptyState
          icon={<MapPin className="w-8 h-8" />}
          title={searchQuery ? "NO MATCHING PROJECTS" : "NO CITATION PROJECTS"}
          description={
            searchQuery
              ? "No projects match your search. Try a different query."
              : "Create your first citation project to start tracking directory submissions."
          }
          action={
            !searchQuery
              ? { label: "New Project", onClick: () => setShowCreateDialog(true) }
              : undefined
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-mono">NEW CITATION PROJECT</DialogTitle>
            <DialogDescription>
              Set up a new project to track directory submissions for a business.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="business_name">Business Name *</Label>
              <Input
                id="business_name"
                value={newProject.business_name}
                onChange={(e) =>
                  setNewProject((p) => ({ ...p, business_name: e.target.value }))
                }
                placeholder="e.g. Smith Plumbing Sydney"
              />
            </div>
            <div>
              <Label htmlFor="website_url">Website URL</Label>
              <Input
                id="website_url"
                value={newProject.website_url}
                onChange={(e) =>
                  setNewProject((p) => ({ ...p, website_url: e.target.value }))
                }
                placeholder="https://example.com.au"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="category">Category</Label>
                <Input
                  id="category"
                  value={newProject.category}
                  onChange={(e) =>
                    setNewProject((p) => ({ ...p, category: e.target.value }))
                  }
                  placeholder="e.g. Plumbing"
                />
              </div>
              <div>
                <Label htmlFor="phone">Phone</Label>
                <Input
                  id="phone"
                  value={newProject.phone}
                  onChange={(e) =>
                    setNewProject((p) => ({ ...p, phone: e.target.value }))
                  }
                  placeholder="+61 400 000 000"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="city">City</Label>
                <Input
                  id="city"
                  value={newProject.city}
                  onChange={(e) =>
                    setNewProject((p) => ({ ...p, city: e.target.value }))
                  }
                  placeholder="Sydney"
                />
              </div>
              <div>
                <Label htmlFor="state">State</Label>
                <Input
                  id="state"
                  value={newProject.state}
                  onChange={(e) =>
                    setNewProject((p) => ({ ...p, state: e.target.value }))
                  }
                  placeholder="NSW"
                />
              </div>
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={newProject.description}
                onChange={(e) =>
                  setNewProject((p) => ({ ...p, description: e.target.value }))
                }
                placeholder="Brief business description..."
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={isCreating || !newProject.business_name.trim()}>
              {isCreating ? "Creating..." : "Create Project"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
