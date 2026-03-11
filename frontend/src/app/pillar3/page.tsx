"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { useHelixSocket } from "@/hooks/useHelixSocket";
import { useHelixStore, ConversationMessage } from "@/store/helixStore";
import { fileSystemService, FileEntry } from "@/services/FileSystemService";
import CollapsibleSidebar from "@/components/CollapsibleSidebar";
import AgentPanel from "@/components/AgentPanel";
import ChatInterface from "@/components/ChatInterface";
import { 
  Database, 
  Loader2, 
  Send,
  Mic,
  FolderTree,
  GitBranch,
  FileQuestion,
  Brain,
  Link,
  FolderOpen,
  RefreshCw,
  CheckCircle,
  File,
  Folder,
  Upload,
  Search,
  PanelLeftClose,
  PanelLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Quick question suggestions
const QUICK_QUESTIONS = [
  "Where is authentication handled?",
  "Explain the data flow",
  "What design patterns are used?",
  "Are there security vulnerabilities?",
  "How do I add a new feature?",
];

// File tree component
function FileTreeItem({ entry, depth = 0 }: { entry: FileEntry; depth?: number }) {
  const [isOpen, setIsOpen] = useState(depth < 2);
  
  if (entry.type === 'directory') {
    return (
      <div>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-2 w-full px-2 py-1 hover:bg-[#2a2a2a] rounded text-left text-sm"
          style={{ paddingLeft: `${depth * 12 + 8}px` }}
        >
          <Folder className={cn("w-4 h-4 text-cyan-400", isOpen && "text-cyan-300")} />
          <span className="text-slate-300 truncate">{entry.name}</span>
        </button>
        {isOpen && entry.children && (
          <div>
            {entry.children.map((child, i) => (
              <FileTreeItem key={i} entry={child} depth={depth + 1} />
            ))}
          </div>
        )}
      </div>
    );
  }
  
  return (
    <div
      className="flex items-center gap-2 px-2 py-1 hover:bg-[#2a2a2a] rounded text-sm"
      style={{ paddingLeft: `${depth * 12 + 8}px` }}
    >
      <File className="w-4 h-4 text-slate-500" />
      <span className="text-slate-400 truncate">{entry.name}</span>
    </div>
  );
}

export default function Pillar3Page() {
  const { isConnected, startPipeline, sendUserMessage } = useHelixSocket();
  const { 
    currentStage, 
    activeAgent, 
    pipelineProgress, 
    isProcessing, 
    workspace,
    getPillarConversation,
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
  
  const [showFileTree, setShowFileTree] = useState(true);
  const [localFiles, setLocalFiles] = useState<FileEntry[]>([]);
  const [isLocalConnected, setIsLocalConnected] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [indexedCount, setIndexedCount] = useState(0);

  // Get messages for pillar 3
  const pillarMessages: ConversationMessage[] = getPillarConversation(3);

  // Check if local workspace is available
  const hasLocalWorkspace = useMemo(() => {
    return !!fileSystemService.getRootHandle() || !!workspace;
  }, [workspace]);

  useEffect(() => {
    if (hasLocalWorkspace && !isLocalConnected) {
      handleConnectLocal();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasLocalWorkspace]);

  // Determine completed agents
  const getCompletedAgents = (): string[] => {
    const completed: string[] = [];
    const agentOrder = ['INDEXER', 'SAGE'];
    
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

  const handleConnectLocal = useCallback(async () => {
    try {
      setIsIndexing(true);
      setIndexedCount(0);
      
      if (!fileSystemService.getRootHandle()) {
        const handle = await fileSystemService.openFolderPicker();
        if (!handle) {
          setIsIndexing(false);
          return;
        }
      }

      const files = await fileSystemService.readWorkspace();
      setLocalFiles(files);
      setIsLocalConnected(true);
      setIndexedCount(files.length);
      setIsIndexing(false);
    } catch (error) {
      console.error('Error connecting to local workspace:', error);
      setIsIndexing(false);
    }
  }, []);

  const handleSendMessage = (message: string) => {
    if (!isConnected) return;
    
    if (!isProcessing && pillarMessages.length === 0) {
      startPipeline(3, message);
    } else if (!isProcessing) {
      sendUserMessage(message, undefined, 3);
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
      <div className="flex-1 flex min-w-0 relative">
        {/* File Tree Panel */}
        {showFileTree && (
          <div className="w-64 border-r border-[#2a2a2a] flex flex-col bg-[#1a1a1a]">
            {/* File Tree Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#2a2a2a]">
              <div className="flex items-center gap-2">
                <FolderTree className="w-4 h-4 text-purple-400" />
                <span className="text-sm font-medium text-white">Codebase</span>
              </div>
              <button
                onClick={() => setShowFileTree(false)}
                className="p-1 rounded hover:bg-[#2a2a2a] text-slate-400"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

            {/* Connection Status */}
            <div className="px-4 py-2 border-b border-[#2a2a2a]">
              {isLocalConnected ? (
                <div className="flex items-center gap-2 text-xs text-emerald-400">
                  <CheckCircle className="w-3 h-3" />
                  <span>{indexedCount} files indexed</span>
                </div>
              ) : isIndexing ? (
                <div className="flex items-center gap-2 text-xs text-cyan-400">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  <span>Indexing...</span>
                </div>
              ) : (
                <button
                  onClick={handleConnectLocal}
                  className="flex items-center gap-2 text-xs text-slate-400 hover:text-white"
                >
                  <FolderOpen className="w-3 h-3" />
                  <span>Connect folder</span>
                </button>
              )}
            </div>

            {/* File Tree */}
            <div className="flex-1 overflow-y-auto p-2">
              {localFiles.length > 0 ? (
                localFiles.map((entry, i) => (
                  <FileTreeItem key={i} entry={entry} />
                ))
              ) : (
                <div className="text-center text-slate-500 text-sm py-8">
                  <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
                  <p>No files loaded</p>
                </div>
              )}
            </div>

            {/* Quick Questions */}
            <div className="p-3 border-t border-[#2a2a2a]">
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider mb-2">
                Quick Questions
              </p>
              <div className="space-y-1">
                {QUICK_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSendMessage(q)}
                    disabled={isProcessing}
                    className="w-full text-left text-xs text-slate-400 hover:text-white hover:bg-[#2a2a2a] px-2 py-1.5 rounded transition-colors disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Show File Tree Button (when hidden) */}
        {!showFileTree && (
          <button
            onClick={() => setShowFileTree(true)}
            className="absolute left-4 top-4 z-10 p-2 rounded-lg bg-[#2a2a2a] border border-[#3a3a3a] hover:bg-[#3a3a3a] text-slate-400 hover:text-white transition-all"
            title="Show file tree"
          >
            <PanelLeft className="w-4 h-4" />
          </button>
        )}

        {/* Chat Section */}
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

          <ChatInterface
            messages={pillarMessages}
            onSendMessage={handleSendMessage}
            isProcessing={isProcessing}
            activeAgent={activeAgent ?? undefined}
            placeholder="Ask a question about your codebase..."
            pillar={3}
          />
        </div>
      </div>

      {/* Right Panel - Agent Cards */}
      <AgentPanel
        pillar={3}
        isCollapsed={rightPanelCollapsed}
        onToggle={handleRightToggle}
        activeAgent={activeAgent ?? undefined}
        completedAgents={getCompletedAgents()}
      />
    </div>
  );
}
