"use client";

import { useState, useLayoutEffect } from 'react';
import CollapsibleSidebar from './CollapsibleSidebar';
import AgentPanel from './AgentPanel';
import ChatInterface from './ChatInterface';
import { useHelixStore, ConversationMessage } from '@/store/helixStore';
import { useHelixSocket } from '@/hooks/useHelixSocket';
import { cn } from '@/lib/utils';

interface ChatLayoutProps {
  pillar: 1 | 2 | 3;
  children?: React.ReactNode;
}

export default function ChatLayout({ pillar, children }: ChatLayoutProps) {
  // Initialize state from localStorage synchronously
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
  
  const { 
    getPillarConversation,
    isProcessing, 
    activeAgent,
    currentStage,
  } = useHelixStore();
  
  const { startPipeline, sendUserMessage, isConnected } = useHelixSocket();

  // Get messages for current pillar
  const pillarMessages: ConversationMessage[] = getPillarConversation(pillar);

  // Determine completed agents based on conversation
  const getCompletedAgents = (): string[] => {
    const completed: string[] = [];
    const agentOrder = pillar === 1 
      ? ['ROUTER', 'ARIA', 'FELIX', 'NOVA', 'JUDGE']
      : pillar === 2
      ? ['PLANNER', 'CODER', 'TESTER', 'REVIEWER']
      : ['INDEXER', 'SAGE'];
    
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
    if (!isConnected) {
      console.warn('Cannot send message: not connected to backend');
      return;
    }
    
    // If not processing and no messages yet, start a new pipeline
    if (!isProcessing && pillarMessages.length === 0) {
      console.log('Starting new pipeline for pillar', pillar);
      startPipeline(pillar, message);
    } else if (!isProcessing) {
      // Send as follow-up message when not processing
      console.log('Sending follow-up message');
      sendUserMessage(message, undefined, pillar);
    }
    // If processing, the input is disabled so this shouldn't be called
  };

  const placeholders = {
    1: "Describe your startup idea... What problem are you solving?",
    2: "Describe the feature you want to build...",
    3: "Ask a question about your codebase...",
  };

  // Save sidebar state to localStorage
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
    <div className="flex h-screen bg-[#212121] overflow-hidden">
      {/* Left Sidebar */}
      <CollapsibleSidebar 
        isCollapsed={leftSidebarCollapsed}
        onToggle={handleLeftToggle}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 relative">
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

        {/* Chat Interface or Custom Content */}
        {children || (
          <ChatInterface
            messages={pillarMessages}
            onSendMessage={handleSendMessage}
            isProcessing={isProcessing}
            activeAgent={activeAgent ?? undefined}
            placeholder={placeholders[pillar]}
            pillar={pillar}
          />
        )}
      </main>

      {/* Right Panel - Agent Cards */}
      <AgentPanel
        pillar={pillar}
        isCollapsed={rightPanelCollapsed}
        onToggle={handleRightToggle}
        activeAgent={activeAgent ?? undefined}
        completedAgents={getCompletedAgents()}
      />
    </div>
  );
}
