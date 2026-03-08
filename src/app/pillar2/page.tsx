"use client";

import { useState } from "react";
import { Panel } from "@/components/Panel";
import PipelineVisualizer from "@/components/PipelineVisualizer";
import AgentLogStream from "@/components/AgentLogStream";
import HitlInteractionPanel from "@/components/HitlInteractionPanel";
import { useHelixSocket } from "@/hooks/useHelixSocket";
import { useHelixStore } from "@/store/helixStore";
import { Play, SquareSquare, GitBranch, Code2 } from "lucide-react";

export default function Pillar2Page() {
  const { isConnected, startPipeline } = useHelixSocket();
  const { pendingCheckpoints, currentStage, activeAgent } = useHelixStore();
  
  const [featureInput, setFeatureInput] = useState("");
  const [repoInput, setRepoInput] = useState("");

  const handleStart = () => {
    if (featureInput.trim()) {
      startPipeline(2, featureInput, repoInput);
      setFeatureInput("");
    }
  };

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 gap-6 bg-slate-950">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <Code2 className="w-6 h-6 text-blue-400" />
            Engineering Workforce <span className="text-sm font-normal px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">Pillar 2</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">Autonomous coding agents orchestrated by Strands.</p>
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
                <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 block">Feature Request</label>
                <textarea 
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none h-20 text-slate-200 placeholder:text-slate-600"
                    placeholder="Describe what you want to build in plain English..."
                    value={featureInput}
                    onChange={(e) => setFeatureInput(e.target.value)}
                />
             </div>
             <div className="flex gap-4">
                <div className="flex-1">
                    <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5 block">Target Repository (Optional)</label>
                    <div className="relative">
                        <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                        <input 
                            type="text" 
                            className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2 pl-9 pr-3 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none text-slate-200 placeholder:text-slate-600"
                            placeholder="./my-project or username/repo"
                            value={repoInput}
                            onChange={(e) => setRepoInput(e.target.value)}
                        />
                    </div>
                </div>
             </div>
         </div>
         <button 
            onClick={handleStart}
            disabled={!featureInput.trim() || !isConnected}
            className="h-full mt-6 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-2 rounded-lg font-medium flex flex-col items-center justify-center gap-2 transition-colors"
         >
            <Play className="w-5 h-5" />
            <span>Deploy<br/>Workforce</span>
         </button>
      </div>

      {/* Main Dashboard Area */}
      <div className="flex-1 flex gap-6 min-h-0">
        
        {/* Left Column: Visualizer & HITL */}
        <div className="w-1/2 flex flex-col gap-6 min-h-0">
            {/* Pipeline Visualizer */}
            <div className="h-1/2 flex flex-col min-h-0">
                <h2 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-2 flex justify-between items-end">
                    <span>Active Pipeline</span>
                    {activeAgent && (
                        <span className="text-blue-400 text-xs normal-case bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">
                           {activeAgent} is working...
                        </span>
                    )}
                </h2>
                <div className="flex-1 rounded-xl overflow-hidden border border-slate-800 bg-slate-900 shadow-sm">
                    <PipelineVisualizer />
                </div>
            </div>

            {/* HITL Panel (Conditionally rendered, takes up space when active) */}
            <div className={`flex flex-col transition-all duration-300 min-h-0 ${pendingCheckpoints.length > 0 ? 'h-1/2 opacity-100' : 'h-0 opacity-0 overflow-hidden'}`}>
                {pendingCheckpoints.length > 0 && (
                   <>
                     <h2 className="text-sm font-semibold text-orange-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                        <SquareSquare className="w-4 h-4" /> Human-in-the-Loop Checkpoint
                     </h2>
                     <HitlInteractionPanel />
                   </>
                )}
            </div>
        </div>

        {/* Right Column: Agent Activity Log */}
        <div className="w-1/2 flex flex-col min-h-0">
             <AgentLogStream />
        </div>

      </div>
    </div>
  );
}
