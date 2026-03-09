"use client";

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Rocket, 
  Code2, 
  Database, 
  Settings, 
  Zap,
  ChevronRight,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useHelixStore } from '@/store/helixStore';

const navItems = [
  {
    href: '/pillar1',
    label: 'Founding Team',
    description: 'AI startup analysis',
    icon: Rocket,
    color: '#f97316',
    pillar: 1,
  },
  {
    href: '/pillar2',
    label: 'Engineering',
    description: 'Code generation',
    icon: Code2,
    color: '#06b6d4',
    pillar: 2,
  },
  {
    href: '/pillar3',
    label: 'Codebase Intel',
    description: 'Ask your code',
    icon: Database,
    color: '#8b5cf6',
    pillar: 3,
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { isProcessing, activePillar, pipelineProgress } = useHelixStore();

  return (
    <aside className="w-64 bg-[#0a0f1a] border-r border-slate-800 flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-slate-800">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="p-2 rounded-xl bg-gradient-to-br from-orange-500/20 to-purple-500/20 border border-white/10 group-hover:border-white/20 transition-all">
            <Zap className="w-6 h-6 text-orange-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Helix
            </h1>
            <p className="text-[10px] text-slate-500 font-medium">
              Intelligence That Spirals Forward
            </p>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-1">
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] px-3 mb-3">
          Pillars
        </p>
        
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const isPillarProcessing = isProcessing && activePillar === item.pillar;
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-3 rounded-xl transition-all group relative overflow-hidden",
                isActive 
                  ? "bg-white/5 border border-white/10" 
                  : "hover:bg-white/5 border border-transparent"
              )}
            >
              {/* Progress bar for active pillar */}
              {isPillarProcessing && (
                <div 
                  className="absolute bottom-0 left-0 h-0.5 bg-gradient-to-r from-transparent transition-all duration-500"
                  style={{ 
                    width: `${pipelineProgress}%`,
                    background: `linear-gradient(to right, transparent, ${item.color})`,
                  }}
                />
              )}
              
              <div 
                className={cn(
                  "p-2 rounded-lg transition-all",
                  isActive ? "bg-white/10" : "bg-slate-800/50 group-hover:bg-slate-800"
                )}
                style={{ 
                  borderColor: isActive ? `${item.color}40` : 'transparent',
                  borderWidth: 1,
                }}
              >
                <item.icon 
                  className="w-4 h-4 transition-colors" 
                  style={{ color: isActive ? item.color : '#64748b' }}
                />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "text-sm font-medium transition-colors",
                    isActive ? "text-white" : "text-slate-400 group-hover:text-slate-300"
                  )}>
                    {item.label}
                  </span>
                  {isPillarProcessing && (
                    <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: item.color }} />
                  )}
                </div>
                <p className="text-[10px] text-slate-600 truncate">
                  {item.description}
                </p>
              </div>
              
              <ChevronRight className={cn(
                "w-4 h-4 transition-all",
                isActive ? "text-slate-400 opacity-100" : "text-slate-600 opacity-0 group-hover:opacity-100"
              )} />
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-slate-800">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all group",
            pathname === '/settings' 
              ? "bg-white/5 border border-white/10" 
              : "hover:bg-white/5 border border-transparent"
          )}
        >
          <div className={cn(
            "p-2 rounded-lg transition-all",
            pathname === '/settings' ? "bg-white/10" : "bg-slate-800/50 group-hover:bg-slate-800"
          )}>
            <Settings className={cn(
              "w-4 h-4 transition-colors",
              pathname === '/settings' ? "text-slate-300" : "text-slate-500"
            )} />
          </div>
          <span className={cn(
            "text-sm font-medium transition-colors",
            pathname === '/settings' ? "text-white" : "text-slate-400 group-hover:text-slate-300"
          )}>
            Settings
          </span>
        </Link>
        
        {/* Version */}
        <div className="mt-3 px-3">
          <p className="text-[10px] text-slate-700">
            Helix v0.2.0 • Powered by Amazon Nova
          </p>
        </div>
      </div>
    </aside>
  );
}
