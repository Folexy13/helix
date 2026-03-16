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
    <div className="flex h-screen bg-[#0d0d0d] overflow-hidden text-slate-300">
      {/* Left Sidebar */}
      <CollapsibleSidebar
        isCollapsed={leftSidebarCollapsed}
        onToggle={handleLeftToggle}
      />

      {/* Main Content Area - Sophisticated Split View */}
      <div className="flex-1 flex min-w-0 relative">
        {/* Chat Section */}
        <div className="flex-1 flex flex-col min-w-0 relative bg-gradient-to-br from-[#121212] to-[#1a1a1a] border-r border-[#2a2a2a]">
          {/* Status Bar */}
          <div className="absolute top-4 left-4 z-10 flex gap-2">
            <div className={cn(
              "flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-wide backdrop-blur-md transition-all shadow-lg border",
              isConnected
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-rose-500/10 text-rose-400 border-rose-500/20"
            )}>
              <span className={cn(
                "w-2 h-2 rounded-full",
                isConnected ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" : "bg-rose-500"
              )} />
              {isConnected ? 'LIVE PIPELINE' : 'DISCONNECTED'}
            </div>
            {isLocalConnected && (
              <div className="flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-wide bg-purple-500/10 text-purple-400 border border-purple-500/20 backdrop-blur-md shadow-lg">
                <Database className="w-3 h-3" />
                {indexedCount} FILES INDEXED
              </div>
            )}
          </div>

          <ChatInterface
            messages={pillarMessages}
            onSendMessage={handleSendMessage}
            isProcessing={isProcessing}
            activeAgent={activeAgent ?? undefined}
            placeholder="Ask Sage anything about your codebase architecture..."
            pillar={3}
          />
        </div>

        {/* Intelligence / Code Explorer Panel */}
        {showFileTree && (
          <div className="w-[400px] flex flex-col bg-[#141414] shadow-2xl z-20 transition-all duration-300">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-5 border-b border-[#2a2a2a] bg-[#1a1a1a]">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/10 rounded-lg">
                  <Brain className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-white">Code Intelligence</h2>
                  <p className="text-xs text-slate-500">Semantic Search & RAG</p>
                </div>
              </div>
              <button
                onClick={() => setShowFileTree(false)}
                className="p-2 rounded-lg hover:bg-[#2a2a2a] text-slate-400 hover:text-white transition-colors"
                title="Hide panel"
              >
                <PanelLeftClose className="w-4 h-4" />
              </button>
            </div>

            {/* Connection Actions */}
            <div className="p-6 border-b border-[#2a2a2a] bg-gradient-to-b from-[#1a1a1a] to-transparent">
              {isIndexing ? (
                <div className="flex flex-col items-center justify-center py-6 text-cyan-400 bg-cyan-500/5 rounded-xl border border-cyan-500/10">
                  <Loader2 className="w-6 h-6 animate-spin mb-3" />
                  <span className="text-sm font-medium">Indexing Workspace...</span>
                  <span className="text-xs text-cyan-500/70 mt-1">Generating multimodal embeddings</span>
                </div>
              ) : !isLocalConnected ? (
                <button
                  onClick={handleConnectLocal}
                  className="w-full group flex flex-col items-center justify-center py-8 px-4 rounded-xl border-2 border-dashed border-[#333] hover:border-purple-500/50 hover:bg-purple-500/5 transition-all"
                >
                  <div className="p-3 bg-[#222] rounded-full group-hover:bg-purple-500/20 group-hover:scale-110 transition-all mb-3">
                    <FolderOpen className="w-6 h-6 text-slate-400 group-hover:text-purple-400" />
                  </div>
                  <span className="text-sm font-medium text-slate-300 mb-1">Connect Local Workspace</span>
                  <span className="text-xs text-slate-500 text-center">Allow Sage to index your code for deep semantic search</span>
                </button>
              ) : (
                <div className="flex flex-col gap-3">
                  <div className="flex items-center justify-between p-3 bg-emerald-500/5 border border-emerald-500/10 rounded-lg">
                    <div className="flex items-center gap-3">
                      <CheckCircle className="w-5 h-5 text-emerald-500" />
                      <div>
                        <p className="text-sm font-medium text-emerald-400">Workspace Connected</p>
                        <p className="text-xs text-emerald-500/70">{indexedCount} files loaded securely</p>
                      </div>
                    </div>
                    <button
                      onClick={handleConnectLocal}
                      className="p-1.5 hover:bg-emerald-500/20 rounded-md text-emerald-500 transition-colors"
                      title="Reload Workspace"
                    >
                      <RefreshCw className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Deep Insights Quick Questions */}
            <div className="px-6 py-5">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-4 flex items-center gap-2">
                <Search className="w-3 h-3" /> Explore Architecture
              </h3>
              <div className="flex flex-col gap-2">
                {QUICK_QUESTIONS.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSendMessage(q)}
                    disabled={isProcessing}
                    className="flex items-center justify-between w-full text-left text-sm text-slate-300 bg-[#1e1e1e] hover:bg-[#2a2a2a] border border-[#333] hover:border-purple-500/30 px-4 py-3 rounded-xl transition-all disabled:opacity-50 group"
                  >
                    <span>{q}</span>
                    <Send className="w-3 h-3 text-slate-600 group-hover:text-purple-400 transition-colors" />
                  </button>
                ))}
              </div>
            </div>

            {/* File Tree Browser */}
            <div className="flex-1 flex flex-col min-h-0 border-t border-[#2a2a2a]">
              <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider p-6 pb-2 flex items-center gap-2">
                <FolderTree className="w-3 h-3" /> Indexed Files
              </h3>
              <div className="flex-1 overflow-y-auto px-4 pb-4 custom-scrollbar">
                {localFiles.length > 0 ? (
                  localFiles.map((entry, i) => (
                    <FileTreeItem key={i} entry={entry} />
                  ))
                ) : (
                  <div className="text-center text-slate-500 text-sm py-8 px-4">
                    <p>Connect a workspace to browse the source tree</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Show Panel Button (when hidden) */}
        {!showFileTree && (
          <button
            onClick={() => setShowFileTree(true)}
            className="absolute right-4 top-4 z-10 p-3 rounded-xl bg-[#1e1e1e] border border-[#333] shadow-xl hover:bg-[#2a2a2a] hover:border-purple-500/50 text-slate-400 hover:text-purple-400 transition-all group"
            title="Show Code Intelligence Panel"
          >
            <Brain className="w-5 h-5 group-hover:scale-110 transition-transform" />
          </button>
        )}
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
