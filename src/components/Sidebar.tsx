import { ReactNode } from 'react';
import Link from 'next/link';
import { Layers, Rocket, Code2, BrainCircuit, Settings, Activity } from 'lucide-react';

export default function Sidebar() {
  return (
    <div className="w-64 bg-secondary/30 border-r border-border h-screen flex flex-col">
      <div className="p-4 border-b border-border flex items-center gap-2">
        <Layers className="h-6 w-6 text-primary" />
        <span className="font-bold text-lg tracking-tight">HELIX</span>
      </div>
      
      <div className="flex-1 overflow-y-auto py-4">
        <div className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Pillars
        </div>
        <nav className="space-y-1 px-2">
          <SidebarItem href="/" icon={<Activity />} label="Dashboard" />
          <SidebarItem href="/pillar1" icon={<Rocket />} label="Founding Team" />
          <SidebarItem href="/pillar2" icon={<Code2 />} label="Engineering" />
          <SidebarItem href="/pillar3" icon={<BrainCircuit />} label="Codebase Sage" />
        </nav>

        <div className="px-3 mt-8 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          System
        </div>
        <nav className="space-y-1 px-2">
          <SidebarItem href="/settings" icon={<Settings />} label="Settings" />
        </nav>
      </div>

      <div className="p-4 border-t border-border">
        <div className="text-xs text-muted-foreground flex justify-between items-center">
          <span>Status: <span className="text-green-500 font-medium">Online</span></span>
          <span>v0.1.0</span>
        </div>
      </div>
    </div>
  );
}

function SidebarItem({ href, icon, label }: { href: string; icon: ReactNode; label: string }) {
  return (
    <Link 
      href={href}
      className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium hover:bg-secondary transition-colors"
    >
      <span className="text-muted-foreground">{icon}</span>
      {label}
    </Link>
  );
}
