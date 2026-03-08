"use client";

import { useState } from "react";
import { useHelixSocket } from "@/hooks/useHelixSocket";
import { useHelixStore } from "@/store/helixStore";
import AgentLogStream from "@/components/AgentLogStream";
import HitlInteractionPanel from "@/components/HitlInteractionPanel";
import { Play, Rocket, Users, Lightbulb, Scale, SquareSquare } from "lucide-react";

export default function Pillar1Page() {
  const { isConnected, startPipeline } = useHelixSocket();
  const { pendingCheckpoints, activeAgent } = useHelixStore();
  
  const [ideaInput, setIdeaInput] = useState("");

  const handleStart = () => {
    if (ideaInput.trim()) {
      startPipeline(1, ideaInput);
      setIdeaInput("");
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 gap-6 bg-slate-950">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Rocket className="w-6 h-6 text-orange-400" />
            Founding Team <span className="text-sm font-normal px-2 py-0.5 rounded bg-orange-500/20 text-orange-400">Pillar 1</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">AI-powered startup ideation, validation, and go-to-market strategy.</p>
        </div>
        
        <div className="flex items-center gap-4">
           <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border ${isConnected ? 'bg-green-500/10 text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}></span>
              {isConnected ? 'Backend Connected' : 'Disconnected'}
           </div>
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex gap-4 items-start shadow-sm">
         <div className="flex-1 space-y-3">
             <div>
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 block">Startup Idea</label>
                <textarea 
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none resize-none h-24 text-slate-200 placeholder:text-slate-600"
                    placeholder="Describe your startup idea or problem you want to solve..."
                    value={ideaInput}
                    onChange={(e) => setIdeaInput(e.target.value)}
                />
             </div>
         </div>
         <button 
            onClick={handleStart}
            disabled={!ideaInput.trim() || !isConnected}
            className="h-full mt-6 bg-orange-600 hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg font-medium flex flex-col items-center justify-center gap-2 transition-colors"
         >
            <Play className="w-5 h-5" />
            <span>Launch<br/>Analysis</span>
         </button>
      </div>

      {/* Agent Cards */}
      <div className="grid grid-cols-3 gap-4">
        <AgentCard 
          icon={<Lightbulb className="w-5 h-5" />}
          name="ARIA"
          role="Idea Analyst"
          description="Analyzes market potential and validates startup ideas"
          color="yellow"
        />
        <AgentCard 
          icon={<Users className="w-5 h-5" />}
          name="FELIX"
          role="Financial Strategist"
          description="Creates financial models and funding strategies"
          color="green"
        />
        <AgentCard 
          icon={<Scale className="w-5 h-5" />}
          name="JUDGE"
          role="Critical Evaluator"
          description="Provides objective assessment and risk analysis"
          color="purple"
        />
      </div>

      {/* Main Dashboard Area */}
      <div className="flex-1 flex gap-6 min-h-0">
        
        {/* Left Column: HITL Panel */}
        <div className="w-1/2 flex flex-col gap-6 min-h-0">
            {pendingCheckpoints.length > 0 ? (
              <div className="flex-1 flex flex-col min-h-0">
                <h2 className="text-sm font-semibold text-orange-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                   <SquareSquare className="w-4 h-4" /> Human-in-the-Loop Checkpoint
                </h2>
                <HitlInteractionPanel />
              </div>
            ) : (
              <div className="flex-1 flex items-center justify-center border border-slate-800 rounded-xl bg-slate-900/50">
                <div className="text-center text-slate-500">
                  <Rocket className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p className="text-sm">Enter a startup idea to begin analysis</p>
                </div>
              </div>
            )}
        </div>

        {/* Right Column: Agent Activity Log */}
        <div className="w-1/2 flex flex-col min-h-0">
             <AgentLogStream />
        </div>

      </div>
    </div>
  );
}

function AgentCard({ icon, name, role, description, color }: { 
  icon: React.ReactNode; 
  name: string; 
  role: string; 
  description: string;
  color: string;
}) {
  const colorClasses: Record<string, string> = {
    yellow: 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400',
    green: 'bg-green-500/10 border-green-500/20 text-green-400',
    purple: 'bg-purple-500/10 border-purple-500/20 text-purple-400',
  };
  
  return (
    <div className={`p-4 rounded-xl border ${colorClasses[color]} bg-slate-900`}>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className="font-bold">{name}</span>
        <span className="text-xs text-slate-500">• {role}</span>
      </div>
      <p className="text-xs text-slate-400">{description}</p>
    </div>
  );
}
