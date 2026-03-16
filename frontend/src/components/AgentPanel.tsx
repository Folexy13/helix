"use client";

import { useState } from 'react';
import { 
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  DollarSign,
  Megaphone,
  Gavel,
  Code2,
  FileText,
  TestTube,
  GitPullRequest,
  Brain,
  Search,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Agent definitions for each pillar
const pillar1Agents = [
  {
    id: 'aria',
    name: 'ARIA',
    role: 'CTO',
    description: 'Technical feasibility & architecture',
    icon: TrendingUp,
    color: '#3b82f6',
  },
  {
    id: 'felix',
    name: 'FELIX',
    role: 'CFO',
    description: 'Financial projections & runway',
    icon: DollarSign,
    color: '#22c55e',
  },
  {
    id: 'nova',
    name: 'NOVA',
    role: 'CMO',
    description: 'Go-to-market strategy',
    icon: Megaphone,
    color: '#ec4899',
  },
  {
    id: 'judge',
    name: 'JUDGE',
    role: 'Investor',
    description: 'Fundability assessment',
    icon: Gavel,
    color: '#8b5cf6',
  },
];

const pillar2Agents = [
  {
    id: 'planner',
    name: 'PLANNER',
    role: 'Architect',
    description: 'Engineering spec generation',
    icon: FileText,
    color: '#06b6d4',
  },
  {
    id: 'coder',
    name: 'CODER',
    role: 'Developer',
    description: 'Code implementation',
    icon: Code2,
    color: '#10b981',
  },
  {
    id: 'tester',
    name: 'TESTER',
    role: 'QA',
    description: 'Automated testing',
    icon: TestTube,
    color: '#f59e0b',
  },
  {
    id: 'reviewer',
    name: 'REVIEWER',
    role: 'Senior Dev',
    description: 'Code review & PR',
    icon: GitPullRequest,
    color: '#ef4444',
  },
];

const pillar3Agents = [
  {
    id: 'indexer',
    name: 'INDEXER',
    role: 'Analyzer',
    description: 'Codebase indexing',
    icon: Search,
    color: '#8b5cf6',
  },
  {
    id: 'sage',
    name: 'SAGE',
    role: 'Expert',
    description: 'Code Q&A & insights',
    icon: Brain,
    color: '#06b6d4',
  },
];

interface AgentPanelProps {
  pillar: 1 | 2 | 3;
  isCollapsed: boolean;
  onToggle: () => void;
  activeAgent?: string;
  completedAgents?: string[];
}

export default function AgentPanel({ 
  pillar, 
  isCollapsed, 
  onToggle,
  activeAgent,
  completedAgents = [],
}: AgentPanelProps) {
  const agents = pillar === 1 ? pillar1Agents : pillar === 2 ? pillar2Agents : pillar3Agents;
  
  const pillarColors = {
    1: '#f97316',
    2: '#06b6d4',
    3: '#8b5cf6',
  };

  const pillarNames = {
    1: 'Founding Team',
    2: 'Engineering',
    3: 'Codebase Intel',
  };

  return (
    <aside
      className={cn(
        "bg-[#171717] border-l border-[#333] flex flex-col transition-all duration-300 ease-in-out relative",
        isCollapsed ? "w-16" : "w-72"
      )}
    >
      {/* Toggle Button */}
      <button
        onClick={onToggle}
        className="absolute -left-3 top-6 z-50 p-1.5 rounded-full bg-[#2f2f2f] border border-[#444] hover:bg-[#3a3a3a] transition-colors shadow-lg"
        aria-label={isCollapsed ? "Expand panel" : "Collapse panel"}
      >
        {isCollapsed ? (
          <ChevronLeft className="w-3.5 h-3.5 text-slate-400" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
        )}
      </button>

      {/* Header */}
      <div className={cn(
        "border-b border-[#333] transition-all duration-300",
        isCollapsed ? "p-3" : "p-4"
      )}>
        <div className="flex items-center gap-3">
          <div 
            className="p-2 rounded-lg"
            style={{ backgroundColor: `${pillarColors[pillar]}15` }}
          >
            <Users 
              className="w-5 h-5" 
              style={{ color: pillarColors[pillar] }}
            />
          </div>
          {!isCollapsed && (
            <div className="animate-fade-in">
              <h2 className="text-sm font-bold text-white">
                {pillarNames[pillar]}
              </h2>
              <p className="text-[10px] text-slate-500">
                {agents.length} agents available
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Agents List */}
      <div className={cn(
        "flex-1 overflow-y-auto",
        isCollapsed ? "p-2" : "p-3"
      )}>
        {!isCollapsed && (
          <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] px-2 mb-3 animate-fade-in">
            Active Agents
          </p>
        )}
        
        <div className="space-y-2">
          {agents.map((agent) => {
            const isActive = activeAgent?.toUpperCase() === agent.id.toUpperCase();
            const isComplete = completedAgents.includes(agent.id.toUpperCase());
            
            return (
              <div
                key={agent.id}
                className={cn(
                  "rounded-xl transition-all duration-300",
                  isCollapsed ? "p-2" : "p-3",
                  isActive 
                    ? "bg-[#2a2a2a] border-2 shadow-lg" 
                    : isComplete
                    ? "bg-emerald-500/5 border border-emerald-500/20"
                    : "bg-[#222] border border-transparent hover:border-[#3a3a3a]"
                )}
                style={isActive ? { 
                  borderColor: agent.color,
                  boxShadow: `0 0 20px ${agent.color}40, inset 0 0 0 1px ${agent.color}30`
                } : undefined}
                title={isCollapsed ? `${agent.name} - ${agent.role}` : undefined}
              >
                <div className={cn(
                  "flex items-center",
                  isCollapsed ? "justify-center" : "gap-3"
                )}>
                  <div 
                    className={cn(
                      "rounded-lg flex items-center justify-center transition-all",
                      isCollapsed ? "p-0" : "p-2",
                      isActive ? "animate-pulse" : ""
                    )}
                    style={{ 
                      backgroundColor: isCollapsed ? 'transparent' : `${agent.color}15`,
                    }}
                  >
                    <agent.icon 
                      className={cn(
                        "transition-all",
                        isCollapsed ? "w-5 h-5" : "w-4 h-4"
                      )}
                      style={{ color: agent.color }}
                    />
                  </div>
                  
                  {!isCollapsed && (
                    <div className="flex-1 min-w-0 animate-fade-in">
                      <div className="flex items-center gap-2">
                        <span 
                          className="text-sm font-bold"
                          style={{ color: agent.color }}
                        >
                          {agent.name}
                        </span>
                        {isActive && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/10 text-white animate-pulse">
                            Active
                          </span>
                        )}
                        {isComplete && !isActive && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                            Done
                          </span>
                        )}
                      </div>
                      <p className="text-[10px] text-slate-500 font-medium uppercase tracking-wider">
                        {agent.role}
                      </p>
                      <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                        {agent.description}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Status Footer */}
      {!isCollapsed && (
        <div className="p-3 border-t border-[#2a2a2a] animate-fade-in">
          <div className="flex items-center justify-between text-[10px]">
            <span className="text-slate-500">
              {completedAgents.length} / {agents.length} complete
            </span>
            <div className="flex items-center gap-1">
              <span 
                className="w-2 h-2 rounded-full"
                style={{ 
                  backgroundColor: activeAgent ? pillarColors[pillar] : '#4a4a4a',
                  boxShadow: activeAgent ? `0 0 8px ${pillarColors[pillar]}` : 'none',
                }}
              />
              <span className="text-slate-400">
                {activeAgent ? 'Processing' : 'Idle'}
              </span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
