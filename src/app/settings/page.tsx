"use client";

import { useState } from "react";
import { Settings, Server, Key, Bell, Palette, Save } from "lucide-react";

export default function SettingsPage() {
  const [backendUrl, setBackendUrl] = useState("http://localhost:8000");
  const [apiKey, setApiKey] = useState("");
  const [notifications, setNotifications] = useState(true);
  const [theme, setTheme] = useState("dark");

  const handleSave = () => {
    // Save settings logic would go here
    console.log("Settings saved:", { backendUrl, apiKey, notifications, theme });
  };

  return (
    <div className="flex flex-col h-full overflow-auto p-6 gap-6 bg-slate-950">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Settings className="w-6 h-6 text-slate-400" />
            Settings
          </h1>
          <p className="text-slate-400 text-sm mt-1">Configure your HELIX environment.</p>
        </div>
      </div>

      {/* Settings Sections */}
      <div className="max-w-2xl space-y-6">
        
        {/* Backend Connection */}
        <SettingsSection 
          icon={<Server className="w-5 h-5" />}
          title="Backend Connection"
          description="Configure the connection to your HELIX backend server."
        >
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 block">
                Backend URL
              </label>
              <input 
                type="text"
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-slate-200 placeholder:text-slate-600"
                placeholder="http://localhost:8000"
              />
            </div>
          </div>
        </SettingsSection>

        {/* API Keys */}
        <SettingsSection 
          icon={<Key className="w-5 h-5" />}
          title="API Keys"
          description="Manage API keys for external services."
        >
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 block">
                AWS Bedrock API Key (Optional Override)
              </label>
              <input 
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-slate-200 placeholder:text-slate-600"
                placeholder="••••••••••••••••"
              />
              <p className="text-xs text-slate-500 mt-1">Leave empty to use server-side configuration.</p>
            </div>
          </div>
        </SettingsSection>

        {/* Notifications */}
        <SettingsSection 
          icon={<Bell className="w-5 h-5" />}
          title="Notifications"
          description="Configure notification preferences."
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-slate-200">Enable Notifications</p>
              <p className="text-xs text-slate-500">Receive alerts for HITL checkpoints and pipeline completions.</p>
            </div>
            <button
              onClick={() => setNotifications(!notifications)}
              className={`relative w-12 h-6 rounded-full transition-colors ${notifications ? 'bg-blue-600' : 'bg-slate-700'}`}
            >
              <span 
                className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${notifications ? 'left-7' : 'left-1'}`}
              />
            </button>
          </div>
        </SettingsSection>

        {/* Appearance */}
        <SettingsSection 
          icon={<Palette className="w-5 h-5" />}
          title="Appearance"
          description="Customize the look and feel."
        >
          <div>
            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 block">
              Theme
            </label>
            <select 
              value={theme}
              onChange={(e) => setTheme(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-slate-200"
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="system">System</option>
            </select>
          </div>
        </SettingsSection>

        {/* Save Button */}
        <div className="pt-4">
          <button 
            onClick={handleSave}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-colors"
          >
            <Save className="w-4 h-4" />
            Save Settings
          </button>
        </div>

      </div>
    </div>
  );
}

function SettingsSection({ 
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
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6">
      <div className="flex items-center gap-2 mb-1 text-slate-200">
        {icon}
        <h2 className="font-semibold">{title}</h2>
      </div>
      <p className="text-xs text-slate-500 mb-4">{description}</p>
      {children}
    </div>
  );
}
