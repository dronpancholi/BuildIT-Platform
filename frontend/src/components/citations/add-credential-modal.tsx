"use client";

import { useState } from "react";
import { Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { fetchApi } from "@/lib/api";

interface AddCredentialModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

const SITE_OPTIONS = [
  { slug: "truelocal", name: "True Local" },
  { slug: "yellow_pages_au", name: "Yellow Pages Australia" },
  { slug: "hotfrog_australia", name: "Hotfrog Australia" },
  { slug: "start_local", name: "StartLocal" },
  { slug: "brownbook", name: "Brownbook" },
  { slug: "cybo", name: "Cybo" },
  { slug: "showmelocal", name: "ShowMeLocal" },
  { slug: "iglobal", name: "iGlobal" },
  { slug: "tupalo", name: "Tupalo" },
  { slug: "2findlocal", name: "2FindLocal" },
  { slug: "cylex_australia", name: "Cylex Australia" },
  { slug: "yalwa", name: "Yalwa" },
  { slug: "business_australia", name: "Business Australia" },
  { slug: "google_business", name: "Google Business Profile" },
  { slug: "bing_places", name: "Bing Places" },
  { slug: "yelp", name: "Yelp" },
  { slug: "facebook_business", name: "Facebook Business" },
  { slug: "foursquare", name: "Foursquare" },
  { slug: "apple_maps", name: "Apple Maps Connect" },
  { slug: "here_maps", name: "HERE Maps" },
];

export function AddCredentialModal({ isOpen, onClose, onSuccess }: AddCredentialModalProps) {
  const [formData, setFormData] = useState({
    site_slug: "",
    site_name: "",
    email: "",
    password: "",
    confirmPassword: "",
    recovery_email: "",
    recovery_phone: "",
    notes: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSiteChange = (slug: string) => {
    const site = SITE_OPTIONS.find((s) => s.slug === slug);
    setFormData((prev) => ({
      ...prev,
      site_slug: slug,
      site_name: site?.name || "",
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (!formData.site_slug || !formData.email || !formData.password) {
      setError("Site, email, and password are required");
      return;
    }

    try {
      setIsSubmitting(true);
      await fetchApi("/credentials/vault?tenant_id=00000000-0000-0000-0000-000000000001", {
        method: "POST",
        body: JSON.stringify({
          site_slug: formData.site_slug,
          site_name: formData.site_name,
          email: formData.email,
          password: formData.password,
          recovery_email: formData.recovery_email || null,
          recovery_phone: formData.recovery_phone || null,
          notes: formData.notes || null,
        }),
      });
      onSuccess?.();
      onClose();
      setFormData({
        site_slug: "",
        site_name: "",
        email: "",
        password: "",
        confirmPassword: "",
        recovery_email: "",
        recovery_phone: "",
        notes: "",
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add credential");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface-dark border border-surface-border rounded-xl w-full max-w-md mx-4 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-surface-border">
          <h2 className="text-lg font-semibold text-slate-100">Add Credential</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {/* Site */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">Site *</label>
            <select
              value={formData.site_slug}
              onChange={(e) => handleSiteChange(e.target.value)}
              className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500"
              required
            >
              <option value="">Select site...</option>
              {SITE_OPTIONS.map((site) => (
                <option key={site.slug} value={site.slug}>
                  {site.name}
                </option>
              ))}
            </select>
          </div>

          {/* Email */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">Email *</label>
            <Input
              type="email"
              value={formData.email}
              onChange={(e) => setFormData((prev) => ({ ...prev, email: e.target.value }))}
              placeholder="account@example.com"
              className="bg-surface-darker border-surface-border text-slate-200"
              required
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">Password *</label>
            <Input
              type="password"
              value={formData.password}
              onChange={(e) => setFormData((prev) => ({ ...prev, password: e.target.value }))}
              placeholder="Enter password"
              className="bg-surface-darker border-surface-border text-slate-200"
              required
            />
          </div>

          {/* Confirm Password */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">Confirm Password *</label>
            <Input
              type="password"
              value={formData.confirmPassword}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, confirmPassword: e.target.value }))
              }
              placeholder="Confirm password"
              className="bg-surface-darker border-surface-border text-slate-200"
              required
            />
          </div>

          {/* Recovery Email */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">Recovery Email (optional)</label>
            <Input
              type="email"
              value={formData.recovery_email}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, recovery_email: e.target.value }))
              }
              placeholder="backup@example.com"
              className="bg-surface-darker border-surface-border text-slate-200"
            />
          </div>

          {/* Recovery Phone */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">Recovery Phone (optional)</label>
            <Input
              type="tel"
              value={formData.recovery_phone}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, recovery_phone: e.target.value }))
              }
              placeholder="+61 400 000 000"
              className="bg-surface-darker border-surface-border text-slate-200"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="block text-xs text-slate-500 mb-1">Notes (optional)</label>
            <textarea
              value={formData.notes}
              onChange={(e) => setFormData((prev) => ({ ...prev, notes: e.target.value }))}
              placeholder="Additional notes..."
              rows={2}
              className="w-full bg-surface-darker border border-surface-border rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-platform-500 resize-none"
            />
          </div>

          {/* Error */}
          {error && (
            <p className="text-sm text-red-400 bg-red-500/10 p-2 rounded">{error}</p>
          )}

          {/* Actions */}
          <div className="flex items-center gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 mr-1 animate-spin" />
              ) : null}
              Save Credential
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
