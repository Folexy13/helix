"use client";

import { useState, useRef, useEffect } from "react";
import { useHelixSocket } from "@/hooks/useHelixSocket";
import { useHelixStore } from "@/store/helixStore";
import AgentLogStream from "@/components/AgentLogStream";
import { 
  Play, 
  Rocket, 
  Users, 
  Lightbulb, 
  Scale, 
  AlertCircle, 
  Loader2, 
  Send,
  Mic,
  TrendingUp,
  DollarSign,
  Megaphone,
  Gavel,
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
      "p-4 rounded-2xl border transition-all duration-500",
      isActive 
        ? "border-white/30 bg-white/5 shadow-lg scale-[1.02]" 
        : isComplete
        ? "border-emerald-500/30 bg-emerald-500/5"
        : "border-slate-800 bg-slate-900/30 opacity-60"
    )}>
      <div className="flex items-center gap-3 mb-2">
        <div 
          className={cn(
            "p-2 rounded-lg border transition-all",
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
            <span className="font-bold text-sm tracking-tight" style={{ color }}>
              {name}
            </span>
            {isActive && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-white animate-pulse">
                Active
              </span>
            )}
            {isComplete && (
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400">
                Done
              </span>
            )}
          </div>
          <div className="text-[10px] uppercase font-bold text-slate-500 tracking-wider">{role}</div>
        </div>
      </div>
      <p className="text-xs text-slate-400 leading-relaxed">{description}</p>
    </div>
  );
}

// Progress indicator
function PipelineProgress({ 
  stage, 
  progress, 
  description 
}: { 
  stage: string; 
  progress: number; 
  description: string;
}) {
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-medium text-slate-400 uppercase tracking-wider">{stage}</span>
        <span className="text-slate-500">{progress}%</span>
      </div>
      <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div 
          className="h-full bg-gradient-to-r from-orange-500 to-amber-500 rounded-full transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>
      {description && (
        <p className="text-[10px] text-slate-500">{description}</p>
      )}
    </div>
  );
}

export default function Pillar1Page() {
  const { isConnected, startPipeline, sendUserMessage } = useHelixSocket();
  const { currentStage, stageDescription, activeAgent, pipelineProgress, isProcessing } = useHelixStore();
  
  const [ideaInput, setIdeaInput] = useState("");
  const [followUpInput, setFollowUpInput] = useState("");
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus input
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleStart = () => {
    if (ideaInput.trim()) {
      startPipeline(1, ideaInput);
      setIdeaInput("");
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

  // Determine which agents are active/complete based on stage
  const getAgentStatus = (agentName: string) => {
    const isActive = activeAgent?.toUpperCase() === agentName;
    const agentOrder = ['ROUTER', 'ARIA', 'FELIX', 'NOVA', 'JUDGE'];
    const currentIdx = agentOrder.indexOf(activeAgent?.toUpperCase() || '');
    const agentIdx = agentOrder.indexOf(agentName);
    const isComplete = currentStage === 'complete' || (currentIdx > agentIdx && currentIdx !== -1);
    return { isActive, isComplete };
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[#0a0f1a]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-gradient-to-r from-slate-900/80 to-slate-900/40">
        <div className="flex items-center gap-4">
          <div className="p-2.5 rounded-xl bg-orange-500/20 border border-orange-500/30">
            <Rocket className="w-6 h-6 text-orange-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Founding Team
            </h1>
            <p className="text-xs text-slate-500">AI-powered startup analysis</p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-orange-500/20 text-orange-400 border border-orange-500/30 font-bold">
            Pillar 1
          </span>
        </div>
        
        <div className="flex items-center gap-4">
          {isProcessing && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-orange-500/10 border border-orange-500/20">
              <Loader2 className="w-3 h-3 text-orange-400 animate-spin" />
              <span className="text-xs text-orange-400 font-medium">
                {activeAgent ? `${activeAgent} analyzing...` : 'Processing...'}
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

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar - Agent Overview */}
        <div className="w-80 border-r border-slate-800 flex flex-col bg-slate-900/30">
          <div className="p-4 border-b border-slate-800">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-1">
              Strategic Workforce
            </h2>
            <p className="text-[10px] text-slate-600">
              Your AI founding team analyzing your idea
            </p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <AgentCard 
              icon={<TrendingUp className="w-5 h-5 text-blue-400" />}
              name="ARIA"
              role="Chief Technology Officer"
              description="Technical feasibility, architecture, and stack recommendations"
              color="#3b82f6"
              {...getAgentStatus('ARIA')}
            />
            <AgentCard 
              icon={<DollarSign className="w-5 h-5 text-emerald-400" />}
              name="FELIX"
              role="Chief Financial Officer"
              description="Financial projections, burn rate, and runway analysis"
              color="#22c55e"
              {...getAgentStatus('FELIX')}
            />
            <AgentCard 
              icon={<Megaphone className="w-5 h-5 text-pink-400" />}
              name="NOVA"
              role="Chief Marketing Officer"
              description="Go-to-market strategy and value proposition"
              color="#ec4899"
              {...getAgentStatus('NOVA')}
            />
            <AgentCard 
              icon={<Gavel className="w-5 h-5 text-purple-400" />}
              name="JUDGE"
              role="Investor Advisor"
              description="Critical evaluation and fundability assessment"
              color="#8b5cf6"
              {...getAgentStatus('JUDGE')}
            />
          </div>
          
          {/* Progress */}
          {isProcessing && (
            <div className="p-4 border-t border-slate-800">
              <PipelineProgress 
                stage={currentStage}
                progress={pipelineProgress}
                description={stageDescription}
              />
            </div>
          )}
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
              // Initial input
              <div className="space-y-3">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
                  Describe Your Startup Idea
                </label>
                <div className="flex gap-3">
                  <div className="flex-1 relative">
                    <textarea 
                      ref={inputRef}
                      className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 pr-12 text-sm focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 outline-none resize-none h-20 text-slate-200 placeholder:text-slate-600"
                      placeholder="What problem are you solving? Who is your target audience? What makes your solution unique?"
                      value={ideaInput}
                      onChange={(e) => setIdeaInput(e.target.value)}
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
                    disabled={!ideaInput.trim() || !isConnected}
                    className="bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-500 hover:to-amber-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-4 rounded-xl font-bold text-sm flex items-center gap-2 transition-all shadow-lg shadow-orange-900/30 active:scale-95 self-end"
                  >
                    <Play className="w-4 h-4 fill-current" />
                    Analyze
                  </button>
                </div>
                <p className="text-[10px] text-slate-600">
                  Press Enter to submit • Shift+Enter for new line
                </p>
              </div>
            ) : (
              // Follow-up input during processing
              <div className="flex gap-3">
                <input
                  type="text"
                  className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 outline-none text-slate-200 placeholder:text-slate-600"
                  placeholder="Add context or ask a follow-up question..."
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
