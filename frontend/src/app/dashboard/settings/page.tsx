"use client";

import { useState, useEffect } from "react";
import {
  Settings,
  Cpu,
  Bell,
  Database,
  Shield,
  Loader2,
  CheckCircle2,
  Save,
  ChevronRight,
  Server,
  RefreshCw,
  AlertTriangle,
} from "lucide-react";
import { usePreferencesStore } from "@/stores/preferences-store";
import { useTenantStore } from "@/stores/tenant-store";
import { toast } from "sonner";

// ---------------------------------------------------------------------------
// Settings Types
// ---------------------------------------------------------------------------

interface ProviderConfig {
  id: string;
  name: string;
  type: "seo" | "email" | "ai" | "scraper";
  enabled: boolean;
  status: "healthy" | "degraded" | "down";
  lastChecked: string;
}

interface ExecutionSettings {
  autoRetryOnFailure: boolean;
  maxRetryCount: number;
  rateLimitPerProvider: number;
  browserTimeout: number;
}

interface NotificationSettings {
  emailOnFailure: boolean;
  dailyDigest: boolean;
  alertThreshold: number;
}

interface SystemSettings {
  databaseStatus: "healthy" | "degraded" | "down";
  redisStatus: "healthy" | "degraded" | "down";
  version: string;
  uptime: string;
}

interface AllSettings {
  providers: ProviderConfig[];
  execution: ExecutionSettings;
  notifications: NotificationSettings;
  system: SystemSettings;
}

// ---------------------------------------------------------------------------
// Defaults
// ---------------------------------------------------------------------------

const DEFAULT_PROVIDERS: ProviderConfig[] = [
  { id: "searxng", name: "SearXNG", type: "seo", enabled: true, status: "healthy", lastChecked: new Date().toISOString() },
  { id: "scrapling", name: "Scrapling", type: "scraper", enabled: true, status: "healthy", lastChecked: new Date().toISOString() },
  { id: "mailhog", name: "MailHog SMTP", type: "email", enabled: true, status: "healthy", lastChecked: new Date().toISOString() },
  { id: "nvidia-nim", name: "NVIDIA NIM", type: "ai", enabled: true, status: "healthy", lastChecked: new Date().toISOString() },
  { id: "hackertarget", name: "HackerTarget API", type: "seo", enabled: true, status: "healthy", lastChecked: new Date().toISOString() },
  { id: "dns-google", name: "Google DNS", type: "seo", enabled: true, status: "healthy", lastChecked: new Date().toISOString() },
];

const DEFAULT_EXECUTION: ExecutionSettings = {
  autoRetryOnFailure: true,
  maxRetryCount: 3,
  rateLimitPerProvider: 10,
  browserTimeout: 30000,
};

const DEFAULT_NOTIFICATIONS: NotificationSettings = {
  emailOnFailure: true,
  dailyDigest: false,
  alertThreshold: 5,
};

const DEFAULT_SYSTEM: SystemSettings = {
  databaseStatus: "healthy",
  redisStatus: "healthy",
  version: "2.1.0",
  uptime: "14d 7h 32m",
};

const STORAGE_KEY = "buildit-settings-v2";

function loadSettings(): AllSettings {
  if (typeof window === "undefined") {
    return {
      providers: DEFAULT_PROVIDERS,
      execution: DEFAULT_EXECUTION,
      notifications: DEFAULT_NOTIFICATIONS,
      system: DEFAULT_SYSTEM,
    };
  }
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<AllSettings>;
      return {
        providers: parsed.providers ?? DEFAULT_PROVIDERS,
        execution: parsed.execution ?? DEFAULT_EXECUTION,
        notifications: parsed.notifications ?? DEFAULT_NOTIFICATIONS,
        system: parsed.system ?? DEFAULT_SYSTEM,
      };
    }
  } catch {
    // fall through
  }
  return {
    providers: DEFAULT_PROVIDERS,
    execution: DEFAULT_EXECUTION,
    notifications: DEFAULT_NOTIFICATIONS,
    system: DEFAULT_SYSTEM,
  };
}

function saveSettings(settings: AllSettings) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // private mode
  }
}

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("providers");
  const [settings, setSettings] = useState<AllSettings>(loadSettings);
  const [isSaving, setIsSaving] = useState(false);
  const [justSaved, setJustSaved] = useState(false);

  const updateExecution = <K extends keyof ExecutionSettings>(key: K, value: ExecutionSettings[K]) => {
    setSettings((s) => ({ ...s, execution: { ...s.execution, [key]: value } }));
    setJustSaved(false);
  };

  const updateNotifications = <K extends keyof NotificationSettings>(key: K, value: NotificationSettings[K]) => {
    setSettings((s) => ({ ...s, notifications: { ...s.notifications, [key]: value } }));
    setJustSaved(false);
  };

  const toggleProvider = (id: string) => {
    setSettings((s) => ({
      ...s,
      providers: s.providers.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p)),
    }));
    setJustSaved(false);
  };

  const handleSave = async () => {
    setIsSaving(true);
    setJustSaved(false);
    try {
      await new Promise((r) => setTimeout(r, 200));
      saveSettings(settings);
      toast.success("Settings saved", {
        description: "All preferences persisted to local storage.",
      });
      setJustSaved(true);
    } catch (e) {
      const message = e instanceof Error ? e.message : "Unknown error";
      toast.error("Failed to save settings", { description: message });
    } finally {
      setIsSaving(false);
    }
  };

  const TABS = [
    { id: "providers", label: "Providers", icon: <Cpu size={18} /> },
    { id: "execution", label: "Execution", icon: <Settings size={18} /> },
    { id: "notifications", label: "Notifications", icon: <Bell size={18} /> },
    { id: "system", label: "System", icon: <Server size={18} /> },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Settings</h1>
        <p className="text-slate-400 mt-1">Configure platform providers, execution behavior, and notifications.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        {/* Sidebar tabs */}
        <div className="md:col-span-1 space-y-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? "bg-surface-border text-platform-400"
                  : "text-slate-400 hover:text-slate-200 hover:bg-surface-border/50"
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="md:col-span-3 space-y-6">
          {/* ---- Providers Tab ---- */}
          {activeTab === "providers" && (
            <div className="glass-panel p-6 space-y-6">
              <div>
                <h3 className="text-lg font-medium text-slate-200 mb-1">Provider Settings</h3>
                <p className="text-xs text-slate-500">Toggle providers on or off. Disabled providers will not be used for any operations.</p>
              </div>
              <div className="space-y-3">
                {settings.providers.map((provider) => (
                  <div
                    key={provider.id}
                    className="flex items-center justify-between p-4 rounded-lg bg-surface-darker border border-surface-border"
                  >
                    <div className="flex items-center gap-4">
                      <div className={`w-2.5 h-2.5 rounded-full ${
                        provider.status === "healthy"
                          ? "bg-emerald-400"
                          : provider.status === "degraded"
                            ? "bg-amber-400"
                            : "bg-red-400"
                      }`} />
                      <div>
                        <p className="text-sm font-medium text-slate-200">{provider.name}</p>
                        <p className="text-xs text-slate-500 capitalize">{provider.type} provider</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      role="switch"
                      aria-checked={provider.enabled}
                      onClick={() => toggleProvider(provider.id)}
                      className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors ${
                        provider.enabled ? "bg-platform-600" : "bg-surface-border"
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          provider.enabled ? "translate-x-6" : "translate-x-1"
                        }`}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ---- Execution Tab ---- */}
          {activeTab === "execution" && (
            <div className="glass-panel p-6 space-y-6">
              <div>
                <h3 className="text-lg font-medium text-slate-200 mb-1">Execution Settings</h3>
                <p className="text-xs text-slate-500">Control retry behavior, rate limits, and browser timeouts.</p>
              </div>
              <div className="space-y-4">
                <ToggleRow
                  label="Auto-retry on failure"
                  description="Automatically retry failed tasks up to the max retry count."
                  value={settings.execution.autoRetryOnFailure}
                  onChange={(v) => updateExecution("autoRetryOnFailure", v)}
                />
                <NumberInputRow
                  label="Max retry count"
                  description="Maximum number of retry attempts per task."
                  value={settings.execution.maxRetryCount}
                  onChange={(v) => updateExecution("maxRetryCount", v)}
                  min={0}
                  max={10}
                />
                <NumberInputRow
                  label="Rate limit per provider"
                  description="Maximum concurrent requests per provider."
                  value={settings.execution.rateLimitPerProvider}
                  onChange={(v) => updateExecution("rateLimitPerProvider", v)}
                  min={1}
                  max={100}
                />
                <NumberInputRow
                  label="Browser timeout (ms)"
                  description="Timeout for browser-based scraping operations in milliseconds."
                  value={settings.execution.browserTimeout}
                  onChange={(v) => updateExecution("browserTimeout", v)}
                  min={5000}
                  max={120000}
                  step={1000}
                />
              </div>
            </div>
          )}

          {/* ---- Notifications Tab ---- */}
          {activeTab === "notifications" && (
            <div className="glass-panel p-6 space-y-6">
              <div>
                <h3 className="text-lg font-medium text-slate-200 mb-1">Notification Settings</h3>
                <p className="text-xs text-slate-500">Configure when and how you receive alerts.</p>
              </div>
              <div className="space-y-4">
                <ToggleRow
                  label="Email notifications on failure"
                  description="Send an email alert when a task or workflow fails."
                  value={settings.notifications.emailOnFailure}
                  onChange={(v) => updateNotifications("emailOnFailure", v)}
                />
                <ToggleRow
                  label="Daily digest"
                  description="Receive a daily summary of all platform activity."
                  value={settings.notifications.dailyDigest}
                  onChange={(v) => updateNotifications("dailyDigest", v)}
                />
                <NumberInputRow
                  label="Alert threshold"
                  description="Number of consecutive failures before triggering an alert."
                  value={settings.notifications.alertThreshold}
                  onChange={(v) => updateNotifications("alertThreshold", v)}
                  min={1}
                  max={50}
                />
              </div>
            </div>
          )}

          {/* ---- System Tab ---- */}
          {activeTab === "system" && (
            <div className="glass-panel p-6 space-y-6">
              <div>
                <h3 className="text-lg font-medium text-slate-200 mb-1">System Settings</h3>
                <p className="text-xs text-slate-500">Read-only system status and version information.</p>
              </div>
              <div className="space-y-3">
                <SystemRow
                  label="Database Status"
                  value={settings.system.databaseStatus}
                  icon={<Database size={16} />}
                />
                <SystemRow
                  label="Redis Status"
                  value={settings.system.redisStatus}
                  icon={<Server size={16} />}
                />
                <SystemRow
                  label="Version"
                  value={settings.system.version}
                  icon={<Cpu size={16} />}
                  isText
                />
                <SystemRow
                  label="Uptime"
                  value={settings.system.uptime}
                  icon={<RefreshCw size={16} />}
                  isText
                />
              </div>
            </div>
          )}

          {/* Save bar */}
          <div className="flex items-center justify-end gap-3">
            {justSaved && (
              <span className="flex items-center gap-1.5 text-xs text-emerald-400">
                <CheckCircle2 className="w-4 h-4" /> Saved
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-6 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-sm font-medium transition-all shadow-lg shadow-platform-900/20 flex items-center gap-2 disabled:opacity-60"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              {isSaving ? "Saving…" : "Save Changes"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ToggleRow({
  label,
  description,
  value,
  onChange,
}: {
  label: string;
  description: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between p-4 rounded-lg bg-surface-darker border border-surface-border">
      <div className="pr-4">
        <p className="text-sm font-medium text-slate-200">{label}</p>
        <p className="text-xs text-slate-500">{description}</p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        onClick={() => onChange(!value)}
        className={`relative inline-flex h-6 w-11 flex-shrink-0 items-center rounded-full transition-colors ${
          value ? "bg-platform-600" : "bg-surface-border"
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            value ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}

function NumberInputRow({
  label,
  description,
  value,
  onChange,
  min,
  max,
  step = 1,
}: {
  label: string;
  description: string;
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
}) {
  return (
    <div className="flex items-center justify-between p-4 rounded-lg bg-surface-darker border border-surface-border">
      <div className="pr-4">
        <p className="text-sm font-medium text-slate-200">{label}</p>
        <p className="text-xs text-slate-500">{description}</p>
      </div>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(e) => {
          const v = Number(e.target.value);
          if (!isNaN(v)) onChange(Math.min(max, Math.max(min, v)));
        }}
        className="w-24 bg-surface-card border border-surface-border rounded-md py-1.5 px-3 text-sm text-slate-200 text-right focus:outline-none focus:border-platform-500/50 transition-colors"
      />
    </div>
  );
}

function SystemRow({
  label,
  value,
  icon,
  isText = false,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  isText?: boolean;
}) {
  const isHealthy = value === "healthy";
  const isDegraded = value === "degraded";

  return (
    <div className="flex items-center justify-between p-4 rounded-lg bg-surface-darker border border-surface-border">
      <div className="flex items-center gap-3">
        <span className="text-slate-500">{icon}</span>
        <p className="text-sm font-medium text-slate-200">{label}</p>
      </div>
      {isText ? (
        <span className="text-sm text-slate-300 font-mono">{value}</span>
      ) : (
        <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-full ${
          isHealthy
            ? "bg-emerald-500/10 text-emerald-400"
            : isDegraded
              ? "bg-amber-500/10 text-amber-400"
              : "bg-red-500/10 text-red-400"
        }`}>
          {isHealthy ? <CheckCircle2 size={12} /> : isDegraded ? <AlertTriangle size={12} /> : <AlertTriangle size={12} />}
          {value.charAt(0).toUpperCase() + value.slice(1)}
        </span>
      )}
    </div>
  );
}
