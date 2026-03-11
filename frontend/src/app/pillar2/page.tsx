"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import dynamic from "next/dynamic";
import { useHelixSocket } from "@/hooks/useHelixSocket";
import { useHelixStore, ConversationMessage } from "@/store/helixStore";
import { fileSystemService } from "@/services/FileSystemService";
import CollapsibleSidebar from "@/components/CollapsibleSidebar";
import AgentPanel from "@/components/AgentPanel";
import ChatInterface from "@/components/ChatInterface";
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
  Monitor,
  Maximize2,
  Minimize2,
  FolderOpen,
  PanelRightClose,
  PanelRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Dynamic import for WebContainer (client-side only)
const LivePreview = dynamic(() => import("@/components/LivePreview"), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center bg-[#252525] rounded-xl">
      <div className="text-center text-slate-500">
        <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
        <p>Loading preview environment...</p>
      </div>
    </div>
  ),
});

export default function Pillar2Page() {
  const { isConnected, startPipeline, sendUserMessage } = useHelixSocket();
  const { 
    currentStage, 
    activeAgent, 
    pipelineProgress, 
    isProcessing,
    getPillarConversation,
    generatedFiles,
  } = useHelixStore();
  
  const [leftSidebarCollapsed, setLeftSidebarCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('helix_left_sidebar_collapsed') === 'true';
    }
    return false;
  });
  
  const [rightPanelCollapsed, setRightPanelCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('helix_right_panel_collapsed') === 'true';
    }
    return false;
  });
  
  const [showPreview, setShowPreview] = useState(true);
  const [previewExpanded, setPreviewExpanded] = useState(false);

  // Get messages for pillar 2
  const pillarMessages: ConversationMessage[] = getPillarConversation(2);

  // Determine completed agents
  const getCompletedAgents = (): string[] => {
    const completed: string[] = [];
    const agentOrder = ['PLANNER', 'CODER', 'TESTER', 'REVIEWER'];
    
    if (activeAgent) {
      const currentIdx = agentOrder.indexOf(activeAgent.toUpperCase());
      if (currentIdx > 0) {
        completed.push(...agentOrder.slice(0, currentIdx));
      }
    }
    
    if (currentStage === 'complete') {
      completed.push(...agentOrder);
    }
    
    return completed;
  };

  const handleSendMessage = (message: string) => {
    if (!isConnected) return;
    
    if (!isProcessing && pillarMessages.length === 0) {
      startPipeline(2, message);
    } else if (!isProcessing) {
      sendUserMessage(message, undefined, 2);
    }
  };

  const handleLeftToggle = () => {
    const newState = !leftSidebarCollapsed;
    setLeftSidebarCollapsed(newState);
    localStorage.setItem('helix_left_sidebar_collapsed', String(newState));
  };

  const handleRightToggle = () => {
    const newState = !rightPanelCollapsed;
    setRightPanelCollapsed(newState);
    localStorage.setItem('helix_right_panel_collapsed', String(newState));
  };

  return (
    <div className="flex h-screen bg-[#1a1a1a] overflow-hidden">
      {/* Left Sidebar */}
      <CollapsibleSidebar 
        isCollapsed={leftSidebarCollapsed}
        onToggle={handleLeftToggle}
      />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        {/* Connection Status */}
        <div className={cn(
          "absolute top-4 right-4 z-10 flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all",
          isConnected 
            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" 
            : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
        )}>
          <span className={cn(
            "w-2 h-2 rounded-full",
            isConnected ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-rose-500"
          )} />
          {isConnected ? 'Connected' : 'Disconnected'}
        </div>

        {/* Split View: Chat + Preview */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Section */}
          <div className={cn(
            "flex flex-col transition-all duration-300",
            showPreview && !previewExpanded ? "w-1/2" : previewExpanded ? "w-0 hidden" : "flex-1"
          )}>
            <ChatInterface
              messages={pillarMessages}
              onSendMessage={handleSendMessage}
              isProcessing={isProcessing}
              activeAgent={activeAgent ?? undefined}
              placeholder="Describe the feature you want to build..."
              pillar={2}
            />
          </div>

          {/* Preview Section */}
          {showPreview && (
            <div className={cn(
              "border-l border-[#2a2a2a] flex flex-col transition-all duration-300",
              previewExpanded ? "flex-1" : "w-1/2"
            )}>
              {/* Preview Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a2a] bg-[#1a1a1a]">
                <div className="flex items-center gap-2">
                  <Monitor className="w-4 h-4 text-cyan-400" />
                  <span className="text-sm font-medium text-white">Live Preview</span>
                  {generatedFiles.length > 0 && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-400">
                      {generatedFiles.length} files
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPreviewExpanded(!previewExpanded)}
                    className="p-1.5 rounded-lg hover:bg-[#2a2a2a] text-slate-400 hover:text-white transition-colors"
                    title={previewExpanded ? "Minimize" : "Maximize"}
                  >
                    {previewExpanded ? (
                      <Minimize2 className="w-4 h-4" />
                    ) : (
                      <Maximize2 className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={() => setShowPreview(false)}
                    className="p-1.5 rounded-lg hover:bg-[#2a2a2a] text-slate-400 hover:text-white transition-colors"
                    title="Hide preview"
                  >
                    <PanelRightClose className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* Preview Content */}
              <div className="flex-1 overflow-hidden">
                <LivePreview files={generatedFiles} />
              </div>
            </div>
          )}

          {/* Show Preview Button (when hidden) */}
          {!showPreview && (
            <button
              onClick={() => setShowPreview(true)}
              className="absolute right-4 bottom-24 p-3 rounded-xl bg-[#2a2a2a] border border-[#3a3a3a] hover:bg-[#3a3a3a] text-slate-400 hover:text-white transition-all shadow-lg"
              title="Show preview"
            >
              <PanelRight className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* Right Panel - Agent Cards */}
      <AgentPanel
        pillar={2}
        isCollapsed={rightPanelCollapsed}
        onToggle={handleRightToggle}
        activeAgent={activeAgent ?? undefined}
        completedAgents={getCompletedAgents()}
      />
    </div>
  );
}
