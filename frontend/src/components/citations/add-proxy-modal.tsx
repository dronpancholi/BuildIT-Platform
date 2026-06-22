"use client";

import { useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchApi } from "@/lib/api";

interface AddProxyModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function AddProxyModal({ isOpen, onClose, onSuccess }: AddProxyModalProps) {
  const [formData, setFormData] = useState({
    name: "",
    proxy_type: "residential",
    proxy_host: "",
    proxy_port: "8080",
    proxy_protocol: "http",
    proxy_auth_username: "",
    proxy_auth_password: "",
    assigned_sites: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.name || !formData.proxy_host || !formData.proxy_port) {
      setError("Name, host, and port are required");
      return;
    }

    try {
      setIsSubmitting(true);
      await fetchApi("/proxies/pools?tenant_id=00000000-0000-0000-0000-000000000001", {
        method: "POST",
        body: JSON.stringify({
          name: formData.name,
          proxy_type: formData.proxy_type,
          proxy_host: formData.proxy_host,
          proxy_port: parseInt(formData.proxy_port),
          proxy_protocol: formData.proxy_protocol,
          proxy_auth_username: formData.proxy_auth_username || null,
          proxy_auth_password: formData.proxy_auth_password || null,
          assigned_sites: formData.assigned_sites
            ? formData.assigned_sites.split(",").map((s) => s.trim())
            : [],
        }),
      });
      onSuccess?.();
      onClose();
      setFormData({
        name: "",
        proxy_type: "residential",
        proxy_host: "",
        proxy_port: "8080",
        proxy_protocol: "http",
        proxy_auth_username: "",
        proxy_auth_password: "",
        assigned_sites: "",
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add proxy");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface-dark border border-surface-border rounded-xl w-full max-w-md mx-4 shadow-2xl">
        <div className="flex items-center justify-between p-4 border-b border-surface-border">
          <h2 className="text-lg font-semibold text-slate-100">Add Proxy</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Name *</label>
            <Input
              value={formData.name}
              onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="My Proxy"
              className="bg-surface-darker border-surface-border text-slate-200"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Type *</label>
              <select
                value={formData.proxy_type}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, proxy_type: e.target.value }))
                }
                className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
              >
                <option value="residential">Residential</option>
                <option value="datacenter">Datacenter</option>
                <option value="mobile">Mobile</option>
                <option value="shared">Shared</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Protocol *</label>
              <select
                value={formData.proxy_protocol}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, proxy_protocol: e.target.value }))
                }
                className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
              >
                <option value="http">HTTP</option>
                <option value="https">HTTPS</option>
                <option value="socks5">SOCKS5</option>
                <option value="socks4">SOCKS4</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Host *</label>
              <Input
                value={formData.proxy_host}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, proxy_host: e.target.value }))
                }
                placeholder="proxy.example.com"
                className="bg-surface-darker border-surface-border text-slate-200"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Port *</label>
              <Input
                type="number"
                value={formData.proxy_port}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, proxy_port: e.target.value }))
                }
                placeholder="8080"
                className="bg-surface-darker border-surface-border text-slate-200"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Username (optional)</label>
            <Input
              value={formData.proxy_auth_username}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, proxy_auth_username: e.target.value }))
              }
              placeholder="username"
              className="bg-surface-darker border-surface-border text-slate-200"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">Password (optional)</label>
            <Input
              type="password"
              value={formData.proxy_auth_password}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, proxy_auth_password: e.target.value }))
              }
              placeholder="password"
              className="bg-surface-darker border-surface-border text-slate-200"
            />
          </div>

          <div>
            <label className="block text-xs text-slate-500 mb-1">
              Assigned Sites (comma-separated, optional)
            </label>
            <Input
              value={formData.assigned_sites}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, assigned_sites: e.target.value }))
              }
              placeholder="truelocal, yelp, google"
              className="bg-surface-darker border-surface-border text-slate-200"
            />
          </div>

          {error && (
            <p className="text-sm text-red-400 bg-red-500/10 p-2 rounded">{error}</p>
          )}

          <div className="flex items-center gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="w-4 h-4 mr-1 animate-spin" /> : null}
              Save Proxy
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
