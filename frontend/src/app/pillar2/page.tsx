"use client";

import { useState, useRef, useEffect } from "react";
import { useHelixSocket } from "@/hooks/useHelixSocket";
import { useHelixStore } from "@/store/helixStore";
import AgentLogStream from "@/components/AgentLogStream";
import { 
  Play, 
  Code2, 
  Loader2, 
  Send,
  Mic,
  FileCode,
  TestTube,
  BookOpen,
  Search,
  GitPullRequest,
  Workflow,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Agent card with status
function AgentCard({ 
  icon, 
  name, 
  role, 
  description, 
  color,
  isActive,
  isComplete,
}: { 
  icon: React.ReactNode; 
  name: string; 
  role: string; 
  description: string;
  color: string;
  isActive: boolean;
  isComplete: boolean;
}) {
  return (
    <div className={cn(
      "p-3 rounded-xl border transition-all duration-500",
      isActive 
        ? "border-white/30 bg-white/5 shadow-lg scale-[1.02]" 
        : isComplete
        ? "border-emerald-500/30 bg-emerald-500/5"
        : "border-slate-800 bg-slate-900/30 opacity-60"
    )}>
      <div className="flex items-center gap-3">
        <div 
          className={cn(
            "p-2 rounded-lg border transition-all shrink-0",
            isActive ? "animate-pulse" : ""
          )}
          style={{ 
            backgroundColor: `${color}15`,
            borderColor: `${color}30`,
          }}
        >
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-bold text-xs tracking-tight" style={{ color }}>
              {name}
            </span>
            {isActive && (
              <span className="text-[8px] px-1 py-0.5 rounded bg-white/10 text-white animate-pulse">
                Active
              </span>
            )}
            {isComplete && (
              <span className="text-[8px] px-1 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                Done
              </span>
            )}
          </div>
          <div className="text-[9px] text-slate-500 truncate">{role}</div>
        </div>
      </div>
    </div>
  );
}

// Pipeline stage indicator
function PipelineStage({ 
  name, 
  icon, 
  isActive, 
  isComplete,
  color,
}: { 
  name: string; 
  icon: React.ReactNode; 
  isActive: boolean; 
  isComplete: boolean;
  color: string;
}) {
  return (
    <div className={cn(
      "flex items-center gap-2 px-3 py-2 rounded-lg transition-all",
      isActive 
        ? "bg-white/10 border border-white/20" 
        : isComplete
        ? "bg-emerald-500/10 border border-emerald-500/20"
        : "bg-slate-900/50 border border-slate-800 opacity-50"
    )}>
      <div 
        className={cn("p-1 rounded", isActive ? "animate-pulse" : "")}
        style={{ backgroundColor: isActive || isComplete ? `${color}20` : 'transparent' }}
      >
        {icon}
      </div>
      <span className={cn(
        "text-xs font-medium",
        isActive ? "text-white" : isComplete ? "text-emerald-400" : "text-slate-500"
      )}>
        {name}
      </span>
    </div>
  );
}

export default function Pillar2Page() {
  const { isConnected, startPipeline, sendUserMessage } = useHelixSocket();
  const { currentStage, stageDescription, activeAgent, pipelineProgress, isProcessing, resetPipeline, activePillar } = useHelixStore();
  
  const [featureInput, setFeatureInput] = useState("");
  const [followUpInput, setFollowUpInput] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Reset pipeline state when entering Pillar 2 (if coming from another pillar)
  useEffect(() => {
    if (activePillar !== 2 && currentStage === 'complete') {
      resetPipeline();
    }
    inputRef.current?.focus();
  }, [activePillar, currentStage, resetPipeline]);

  const handleStart = () => {
    if (featureInput.trim()) {
      startPipeline(2, featureInput);
      setFeatureInput("");
    }
  };

  const handleFollowUp = () => {
    if (followUpInput.trim()) {
      sendUserMessage(followUpInput);
      setFollowUpInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      action();
    }
  };

  // Determine agent status
  const getAgentStatus = (agentName: string) => {
    const isActive = activeAgent?.toUpperCase() === agentName;
    const agentOrder = ['ORCHESTRATOR', 'PLANNER', 'CODER', 'TESTER', 'DOCS', 'REVIEWER'];
    const currentIdx = agentOrder.indexOf(activeAgent?.toUpperCase() || '');
    const agentIdx = agentOrder.indexOf(agentName);
    const isComplete = currentStage === 'complete' || (currentIdx > agentIdx && currentIdx !== -1);
    return { isActive, isComplete };
  };

  // Pipeline stages
  const stages = [
    { name: 'Intake', stage: 'intake', icon: <Workflow className="w-3 h-3 text-slate-400" />, color: '#64748b' },
    { name: 'Planning', stage: 'planning', icon: <FileCode className="w-3 h-3 text-cyan-400" />, color: '#06b6d4' },
    { name: 'Coding', stage: 'coding', icon: <Code2 className="w-3 h-3 text-emerald-400" />, color: '#10b981' },
    { name: 'Testing', stage: 'testing', icon: <TestTube className="w-3 h-3 text-amber-400" />, color: '#f59e0b' },
    { name: 'Docs', stage: 'documenting', icon: <BookOpen className="w-3 h-3 text-indigo-400" />, color: '#6366f1' },
    { name: 'Review', stage: 'reviewing', icon: <Search className="w-3 h-3 text-rose-400" />, color: '#ef4444' },
    { name: 'PR', stage: 'finalizing', icon: <GitPullRequest className="w-3 h-3 text-purple-400" />, color: '#8b5cf6' },
  ];

  const getStageStatus = (stageName: string) => {
    const stageOrder = stages.map(s => s.stage);
    const currentIdx = stageOrder.indexOf(currentStage);
    const stageIdx = stageOrder.indexOf(stageName);
    return {
      isActive: currentStage === stageName,
      isComplete: currentStage === 'complete' || (currentIdx > stageIdx && currentIdx !== -1),
    };
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[#0a0f1a]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-gradient-to-r from-slate-900/80 to-slate-900/40">
        <div className="flex items-center gap-4">
          <div className="p-2.5 rounded-xl bg-cyan-500/20 border border-cyan-500/30">
            <Code2 className="w-6 h-6 text-cyan-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Engineering Workforce
            </h1>
            <p className="text-xs text-slate-500">Autonomous code generation pipeline</p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 font-bold">
            Pillar 2
          </span>
        </div>
        
        <div className="flex items-center gap-4">
          {isProcessing && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20">
              <Loader2 className="w-3 h-3 text-cyan-400 animate-spin" />
              <span className="text-xs text-cyan-400 font-medium">
                {activeAgent ? `${activeAgent} working...` : 'Processing...'}
              </span>
            </div>
          )}
          <div className={cn(
            "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium",
            isConnected ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
          )}>
            <span className={cn("w-2 h-2 rounded-full", isConnected ? 'bg-emerald-500' : 'bg-rose-500')} />
            {isConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
      </div>

      {/* Pipeline Progress Bar */}
      {isProcessing && (
        <div className="px-6 py-3 border-b border-slate-800 bg-slate-900/30">
          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {stages.map((stage, idx) => {
              const status = getStageStatus(stage.stage);
              return (
                <div key={stage.stage} className="flex items-center">
                  <PipelineStage 
                    name={stage.name}
                    icon={stage.icon}
                    color={stage.color}
                    {...status}
                  />
                  {idx < stages.length - 1 && (
                    <div className={cn(
                      "w-8 h-0.5 mx-1",
                      status.isComplete ? "bg-emerald-500/50" : "bg-slate-700"
                    )} />
                  )}
                </div>
              );
            })}
          </div>
          {stageDescription && (
            <p className="text-[10px] text-slate-500 mt-2">{stageDescription}</p>
          )}
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Agent Overview */}
        <div className="w-64 border-r border-slate-800 flex flex-col bg-slate-900/30">
          <div className="p-4 border-b border-slate-800">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-1">
              Engineering Team
            </h2>
            <p className="text-[10px] text-slate-600">
              Autonomous development agents
            </p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            <AgentCard 
              icon={<FileCode className="w-4 h-4 text-cyan-400" />}
              name="PLANNER"
              role="Technical Architect"
              description="Creates engineering specs"
              color="#06b6d4"
              {...getAgentStatus('PLANNER')}
            />
            <AgentCard 
              icon={<Code2 className="w-4 h-4 text-emerald-400" />}
              name="CODER"
              role="Senior Developer"
              description="Implements features"
              color="#10b981"
              {...getAgentStatus('CODER')}
            />
            <AgentCard 
              icon={<TestTube className="w-4 h-4 text-amber-400" />}
              name="TESTER"
              role="QA Engineer"
              description="Creates and runs tests"
              color="#f59e0b"
              {...getAgentStatus('TESTER')}
            />
            <AgentCard 
              icon={<BookOpen className="w-4 h-4 text-indigo-400" />}
              name="DOCS"
              role="Technical Writer"
              description="Generates documentation"
              color="#6366f1"
              {...getAgentStatus('DOCS')}
            />
            <AgentCard 
              icon={<Search className="w-4 h-4 text-rose-400" />}
              name="REVIEWER"
              role="Code Reviewer"
              description="Reviews quality & security"
              color="#ef4444"
              {...getAgentStatus('REVIEWER')}
            />
          </div>
        </div>

        {/* Main Area - Conversation */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Conversation Stream */}
          <div className="flex-1 overflow-hidden p-6">
            <AgentLogStream />
          </div>

          {/* Input Area */}
          <div className="p-4 border-t border-slate-800 bg-slate-900/50">
            {!isProcessing ? (
              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                  Describe Your Feature Request
                </label>
                <div className="flex gap-3">
                  <div className="flex-1 relative">
                    <textarea 
                      ref={inputRef}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 pr-12 text-sm focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 outline-none resize-none h-20 text-slate-200 placeholder:text-slate-600"
                      placeholder="Describe the feature you want to build. Include expected inputs, outputs, and any constraints..."
                      value={featureInput}
                      onChange={(e) => setFeatureInput(e.target.value)}
                      onKeyDown={(e) => handleKeyDown(e, handleStart)}
                    />
                    <button
                      className="absolute right-3 bottom-3 p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-300 transition-all"
                      title="Voice input (coming soon)"
                    >
                      <Mic className="w-4 h-4" />
                    </button>
                  </div>
                  <button 
                    onClick={handleStart}
                    disabled={!featureInput.trim() || !isConnected}
                    className="bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-4 rounded-xl font-bold text-sm flex items-center gap-2 transition-all shadow-lg shadow-cyan-900/30 active:scale-95 self-end"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    Build
                  </button>
                </div>
                <p className="text-[10px] text-slate-600">
                  Press Enter to submit • Shift+Enter for new line
                </p>
              </div>
            ) : (
              <div className="flex gap-3">
                <input
                  type="text"
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-cyan-500/50 focus:border-cyan-500/50 outline-none text-slate-200 placeholder:text-slate-600"
                  placeholder="Add context or interrupt with changes..."
                  value={followUpInput}
                  onChange={(e) => setFollowUpInput(e.target.value)}
                  onKeyDown={(e) => handleKeyDown(e, handleFollowUp)}
                />
                <button
                  onClick={handleFollowUp}
                  disabled={!followUpInput.trim()}
                  className="bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-3 rounded-xl transition-all"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
