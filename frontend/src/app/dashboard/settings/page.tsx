"use client";

import { Settings, Shield, Bell, Database, Globe, Sliders } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-slate-100 tracking-tight">Settings</h1>
        <p className="text-slate-400 mt-1">Configure platform behavior and enterprise integrations.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        <div className="md:col-span-1 space-y-1">
          <SettingsTab icon={<Sliders size={18} />} label="General" active />
          <SettingsTab icon={<Shield size={18} />} label="Security" />
          <SettingsTab icon={<Bell size={18} />} label="Notifications" />
          <SettingsTab icon={<Database size={18} />} label="Integrations" />
          <SettingsTab icon={<Globe size={18} />} label="Public Profile" />
        </div>

        <div className="md:col-span-3 space-y-6">
          <div className="glass-panel p-6 space-y-6">
            <div>
              <h3 className="text-lg font-medium text-slate-200 mb-4">Operational Mode</h3>
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-surface-darker border border-surface-border">
                  <div>
                    <p className="text-sm font-medium text-slate-200">Zero-Cost Operationalization</p>
                    <p className="text-xs text-slate-500">Use local scraping engines instead of paid APIs.</p>
                  </div>
                  <div className="w-12 h-6 rounded-full bg-platform-600 relative p-1 cursor-pointer">
                    <div className="w-4 h-4 rounded-full bg-white ml-auto"></div>
                  </div>
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-surface-darker border border-surface-border">
                  <div>
                    <p className="text-sm font-medium text-slate-200">AI Safety Governance</p>
                    <p className="text-xs text-slate-500">Require human approval for high-risk outreach.</p>
                  </div>
                  <div className="w-12 h-6 rounded-full bg-platform-600 relative p-1 cursor-pointer">
                    <div className="w-4 h-4 rounded-full bg-white ml-auto"></div>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-6 border-t border-surface-border">
              <h3 className="text-lg font-medium text-slate-200 mb-4">Platform Identity</h3>
              <div className="grid grid-cols-1 gap-4">
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tenant Display Name</label>
                  <input 
                    type="text" 
                    placeholder="Enter tenant display name"
                    className="w-full bg-surface-darker border border-surface-border rounded-md py-2 px-4 text-sm text-slate-200 focus:outline-none focus:border-platform-500/50 transition-colors"
                  />
                </div>
              </div>
            </div>

            <div className="pt-6 flex justify-end">
              <button className="px-6 py-2 bg-platform-600 hover:bg-platform-500 text-white rounded-md text-sm font-medium transition-all shadow-lg shadow-platform-900/20">
                Save Changes
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SettingsTab({ icon, label, active }: { icon: React.ReactNode, label: string, active?: boolean }) {
  return (
    <button className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${active ? 'bg-surface-border text-platform-400' : 'text-slate-400 hover:text-slate-200 hover:bg-surface-border/50'}`}>
      {icon}
      {label}
    </button>
  );
}
