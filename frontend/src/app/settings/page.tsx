"use client";

import { useState } from "react";
import { Settings, Server, Key, Bell, Palette, Save, ShieldCheck, Globe } from "lucide-react";
import { cn } from "@/lib/utils";

export default function SettingsPage() {
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [apiKey, setApiKey] = useState("");
  const [notifications, setNotifications] = useState(true);
  const [theme, setTheme] = useState("dark");

  const handleSave = () => {
    console.log("Settings saved:", { backendUrl, apiKey, notifications, theme });
  };

  return (
    <div className="flex flex-col h-full bg-[#020617] overflow-y-auto">
      {/* Header */}
      <div className="px-8 py-10 border-b border-slate-800/50 bg-slate-900/20">
        <div className="max-w-4xl mx-auto flex items-center gap-4">
          <div className="p-3 rounded-2xl bg-slate-800 border border-slate-700">
            <Settings className="w-8 h-8 text-blue-400" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              System Configuration
            </h1>
            <p className="text-slate-400 mt-1 text-lg">Manage your HELIX environment and agent parameters.</p>
          </div>
        </div>
      </div>

      <div className="p-8 max-w-4xl mx-auto w-full space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Backend Connection */}
          <SettingsCard 
            icon={<Server className="w-5 h-5 text-blue-400" />}
            title="Backend Infrastructure"
            description="Core server connection settings."
          >
            <div className="space-y-4 pt-2">
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-2 block ml-1">
                  API Endpoint URL
                </label>
                <div className="relative group">
                  <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600 group-focus-within:text-blue-500 transition-colors" />
                  <input 
                    type="text"
                    value={backendUrl}
                    onChange={(e) => setBackendUrl(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 pl-10 pr-4 text-sm focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none text-slate-200 placeholder:text-slate-700 transition-all"
                    placeholder="http://localhost:8000"
                  />
                </div>
              </div>
            </div>
          </SettingsCard>

          {/* API Keys */}
          <SettingsCard 
            icon={<Key className="w-5 h-5 text-amber-400" />}
            title="Security & Auth"
            description="Manage external service credentials."
          >
            <div className="space-y-4 pt-2">
              <div>
                <label className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-2 block ml-1">
                  AWS Bedrock API Key
                </label>
                <div className="relative group">
                  <ShieldCheck className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-600 group-focus-within:text-amber-500 transition-colors" />
                  <input 
                    type="password"
                    value={apiKey}
                    onChange={(e) => setApiKey(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 pl-10 pr-4 text-sm focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 outline-none text-slate-200 placeholder:text-slate-700 transition-all"
                    placeholder="••••••••••••••••"
                  />
                </div>
                <p className="text-[10px] text-slate-600 mt-2 ml-1 italic font-medium italic">Defaults to server-side .env if left empty.</p>
              </div>
            </div>
          </SettingsCard>

          {/* Notifications */}
          <SettingsCard 
            icon={<Bell className="w-5 h-5 text-purple-400" />}
            title="System Alerts"
            description="Configure real-time notifications."
          >
            <div className="flex items-center justify-between p-4 rounded-xl bg-slate-950 border border-slate-800 mt-2">
              <div>
                <p className="text-sm font-bold text-slate-200">Push Notifications</p>
                <p className="text-[11px] text-slate-500 font-medium mt-0.5">Receive workforce status updates.</p>
              </div>
              <button
                onClick={() => setNotifications(!notifications)}
                className={cn(
                  "relative w-12 h-6 rounded-full transition-all duration-300",
                  notifications ? 'bg-blue-600 shadow-[0_0_10px_rgba(37,99,235,0.3)]' : 'bg-slate-800'
                )}
              >
                <span 
                  className={cn(
                    "absolute top-1 w-4 h-4 rounded-full bg-white transition-all duration-300 shadow-md",
                    notifications ? 'left-7' : 'left-1'
                  )}
                />
              </button>
            </div>
          </SettingsCard>

          {/* Appearance */}
          <SettingsCard 
            icon={<Palette className="w-5 h-5 text-emerald-400" />}
            title="Interface"
            description="Customization and theme options."
          >
            <div className="pt-2">
              <label className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-2 block ml-1">
                Visual Theme
              </label>
              <select 
                value={theme}
                onChange={(e) => setTheme(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-xl py-3 px-4 text-sm focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500/50 outline-none text-slate-200 transition-all appearance-none cursor-pointer"
              >
                <option value="dark">Deep Space (Dark)</option>
                <option value="light">Cloud (Light)</option>
                <option value="system">System Default</option>
              </select>
            </div>
          </SettingsCard>
        </div>

        {/* Action Bar */}
        <div className="flex items-center justify-end gap-4 pt-6 border-t border-slate-800/50">
          <button className="px-6 py-2.5 rounded-xl text-sm font-bold text-slate-400 hover:text-white transition-colors">
            Cancel
          </button>
          <button 
            onClick={handleSave}
            className="bg-blue-600 hover:bg-blue-500 text-white px-8 py-2.5 rounded-xl font-bold text-sm flex items-center gap-2 transition-all active:scale-95 shadow-lg shadow-blue-900/20"
          >
            <Save className="w-4 h-4" />
            Apply Changes
          </button>
        </div>
      </div>
    </div>
  );
}

function SettingsCard({ 
  icon, 
  title, 
  description, 
  children 
}: { 
  icon: React.ReactNode; 
  title: string; 
  description: string; 
  children: React.ReactNode;
}) {
  return (
    <div className="glass-card p-6 rounded-2xl flex flex-col gap-4 border border-slate-800/50">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-slate-950 border border-slate-800 shadow-inner">
          {icon}
        </div>
        <div>
          <h2 className="font-bold text-slate-200 tracking-tight">{title}</h2>
          <p className="text-[11px] text-slate-500 font-medium">{description}</p>
        </div>
      </div>
      <div className="flex-1">
        {children}
      </div>
    </div>
  );
}
