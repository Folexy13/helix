"use client";

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  Rocket, 
  Code2, 
  Database, 
  Settings, 
  Zap,
  ChevronLeft,
  ChevronRight,
  PanelLeftClose,
  PanelLeft,
  Plus,
  MessageSquare,
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

interface CollapsibleSidebarProps {
  isCollapsed: boolean;
  onToggle: () => void;
}

export default function CollapsibleSidebar({ isCollapsed, onToggle }: CollapsibleSidebarProps) {
  const pathname = usePathname();
  const { isProcessing, activePillar, pipelineProgress } = useHelixStore();

  return (
    <aside
      className={cn(
        "bg-[#171717] border-r border-[#333] flex flex-col transition-all duration-300 ease-in-out relative",
        isCollapsed ? "w-16" : "w-64"
      )}
    >
      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="absolute -right-3 top-6 z-50 p-1.5 rounded-full bg-[#2f2f2f] border border-[#444] hover:bg-[#3a3a3a] transition-colors shadow-lg"
        aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {isCollapsed ? (
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
        ) : (
          <ChevronLeft className="w-3.5 h-3.5 text-slate-400" />
        )}
      </button>

      {/* Logo */}
      <div className={cn(
        "border-b border-[#333] transition-all duration-300",
        isCollapsed ? "p-3" : "p-4"
      )}>
        <Link href="/" className="flex items-center gap-3 group">
          <div className={cn(
            "rounded-xl bg-gradient-to-br from-orange-500/20 to-purple-500/20 border border-white/10 group-hover:border-white/20 transition-all flex items-center justify-center",
            isCollapsed ? "p-2" : "p-2"
          )}>
            <Zap className={cn(
              "text-orange-400 transition-all",
              isCollapsed ? "w-5 h-5" : "w-5 h-5"
            )} />
          </div>
          {!isCollapsed && (
            <div className="animate-fade-in">
              <h1 className="text-lg font-bold text-white tracking-tight">
                Helix
              </h1>
              <p className="text-[10px] text-slate-500 font-medium">
                AI Workspace
              </p>
            </div>
          )}
        </Link>
      </div>

      {/* New Chat Button */}
      <div className={cn(
        "border-b border-[#2a2a2a] transition-all duration-300",
        isCollapsed ? "p-2" : "p-3"
      )}>
        <button
          className={cn(
            "w-full flex items-center gap-2 rounded-lg bg-[#2a2a2a] hover:bg-[#3a3a3a] border border-[#3a3a3a] hover:border-[#4a4a4a] transition-all text-slate-300 hover:text-white",
            isCollapsed ? "p-2 justify-center" : "px-3 py-2.5"
          )}
        >
          <Plus className="w-4 h-4" />
          {!isCollapsed && (
            <span className="text-sm font-medium animate-fade-in">New Chat</span>
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className={cn(
        "flex-1 space-y-1 overflow-y-auto",
        isCollapsed ? "p-2" : "p-3"
      )}>
        {!isCollapsed && (
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] px-2 mb-3 animate-fade-in">
            Pillars
          </p>
        )}
        
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const isPillarProcessing = isProcessing && activePillar === item.pillar;
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg transition-all group relative overflow-hidden",
                isCollapsed ? "p-2 justify-center" : "px-3 py-2.5",
                isActive 
                  ? "bg-[#2a2a2a] border border-[#3a3a3a]" 
                  : "hover:bg-[#252525] border border-transparent"
              )}
              title={isCollapsed ? item.label : undefined}
            >
              {/* Progress bar for active pillar */}
              {isPillarProcessing && (
                <div 
                  className="absolute bottom-0 left-0 h-0.5 transition-all duration-500"
                  style={{ 
                    width: `${pipelineProgress}%`,
                    background: `linear-gradient(to right, transparent, ${item.color})`,
                  }}
                />
              )}
              
              <div 
                className={cn(
                  "rounded-lg transition-all flex items-center justify-center",
                  isCollapsed ? "p-0" : "p-1.5",
                  isActive ? "bg-white/5" : ""
                )}
              >
                <item.icon 
                  className={cn(
                    "transition-colors",
                    isCollapsed ? "w-5 h-5" : "w-4 h-4"
                  )}
                  style={{ color: isActive ? item.color : '#9ca3af' }}
                />
              </div>
              
              {!isCollapsed && (
                <div className="flex-1 min-w-0 animate-fade-in">
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
              )}
            </Link>
          );
        })}
      </nav>

      {/* Recent Chats (when expanded) */}
      {!isCollapsed && (
        <div className="px-3 pb-2 animate-fade-in">
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] px-2 mb-2">
            Recent
          </p>
          <div className="space-y-1">
            {['Startup Analysis', 'Feature Build', 'Code Review'].map((chat, i) => (
              <button
                key={i}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left hover:bg-[#252525] transition-colors group"
              >
                <MessageSquare className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-500" />
                <span className="text-xs text-slate-500 group-hover:text-slate-400 truncate">
                  {chat}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className={cn(
        "border-t border-[#2a2a2a]",
        isCollapsed ? "p-2" : "p-3"
      )}>
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 rounded-lg transition-all group",
            isCollapsed ? "p-2 justify-center" : "px-3 py-2",
            pathname === '/settings' 
              ? "bg-[#2a2a2a] border border-[#3a3a3a]" 
              : "hover:bg-[#252525] border border-transparent"
          )}
          title={isCollapsed ? "Settings" : undefined}
        >
          <Settings className={cn(
            "transition-colors",
            isCollapsed ? "w-5 h-5" : "w-4 h-4",
            pathname === '/settings' ? "text-slate-300" : "text-slate-500 group-hover:text-slate-400"
          )} />
          {!isCollapsed && (
            <span className={cn(
              "text-sm font-medium transition-colors animate-fade-in",
              pathname === '/settings' ? "text-white" : "text-slate-400 group-hover:text-slate-300"
            )}>
              Settings
            </span>
          )}
        </Link>
        
        {/* Version */}
        {!isCollapsed && (
          <div className="mt-3 px-3 animate-fade-in">
            <p className="text-[10px] text-slate-700">
              Helix v0.2.0
            </p>
          </div>
        )}
      </div>
    </aside>
  );
}
