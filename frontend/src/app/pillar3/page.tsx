"use client";

import { useState, useRef, useEffect } from "react";
import { useHelixSocket } from "@/hooks/useHelixSocket";
import { useHelixStore } from "@/store/helixStore";
import AgentLogStream from "@/components/AgentLogStream";
import { 
  Play, 
  Database, 
  Loader2, 
  Send,
  Mic,
  Search,
  FolderTree,
  GitBranch,
  FileQuestion,
  Brain,
  Upload,
  Link,
} from "lucide-react";
import { cn } from "@/lib/utils";

// Quick question suggestions
const QUICK_QUESTIONS = [
  "Where is authentication handled?",
  "Explain the data flow from API to database",
  "What design patterns are used?",
  "Are there any security vulnerabilities?",
  "How do I add a new feature?",
  "What will break if I delete this file?",
];

export default function Pillar3Page() {
  const { isConnected, startPipeline, sendUserMessage } = useHelixSocket();
  const { currentStage, stageDescription, activeAgent, pipelineProgress, isProcessing } = useHelixStore();
  
  const [questionInput, setQuestionInput] = useState("");
  const [repoUrl, setRepoUrl] = useState("");
  const [isRepoConnected, setIsRepoConnected] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleAsk = () => {
    if (questionInput.trim()) {
      startPipeline(3, questionInput, repoUrl || undefined);
      setQuestionInput("");
    }
  };

  const handleQuickQuestion = (question: string) => {
    setQuestionInput(question);
    inputRef.current?.focus();
  };

  const handleConnectRepo = () => {
    if (repoUrl.trim()) {
      setIsRepoConnected(true);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      action();
    }
  };

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[#0a0f1a]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-gradient-to-r from-slate-900/80 to-slate-900/40">
        <div className="flex items-center gap-4">
          <div className="p-2.5 rounded-xl bg-purple-500/20 border border-purple-500/30">
            <Database className="w-6 h-6 text-purple-400" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">
              Codebase Intelligence
            </h1>
            <p className="text-xs text-slate-500">Ask questions about your code</p>
          </div>
          <span className="text-xs px-2.5 py-1 rounded-full bg-purple-500/20 text-purple-400 border border-purple-500/30 font-bold">
            Pillar 3
          </span>
        </div>
        
        <div className="flex items-center gap-4">
          {isProcessing && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/20">
              <Loader2 className="w-3 h-3 text-purple-400 animate-spin" />
              <span className="text-xs text-purple-400 font-medium">
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
        {/* Left Sidebar - Repository & Context */}
        <div className="w-80 border-r border-slate-800 flex flex-col bg-slate-900/30">
          {/* Repository Connection */}
          <div className="p-4 border-b border-slate-800">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-3">
              Repository
            </h2>
            
            {!isRepoConnected ? (
              <div className="space-y-3">
                <div className="relative">
                  <Link className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2.5 text-sm focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none text-slate-200 placeholder:text-slate-600"
                    placeholder="GitHub URL or local path..."
                    value={repoUrl}
                    onChange={(e) => setRepoUrl(e.target.value)}
                    onKeyDown={(e) => handleKeyDown(e, handleConnectRepo)}
                  />
                </div>
                <button
                  onClick={handleConnectRepo}
                  disabled={!repoUrl.trim()}
                  className="w-full bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium text-sm flex items-center justify-center gap-2 transition-all"
                >
                  <GitBranch className="w-4 h-4" />
                  Connect Repository
                </button>
                <p className="text-[10px] text-slate-600 text-center">
                  Or drag & drop a folder to analyze
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <div className="flex items-center gap-2 mb-1">
                    <GitBranch className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-medium text-emerald-400">Connected</span>
                  </div>
                  <p className="text-xs text-slate-400 truncate">{repoUrl}</p>
                </div>
                <button
                  onClick={() => setIsRepoConnected(false)}
                  className="w-full text-xs text-slate-500 hover:text-slate-400 transition-colors"
                >
                  Disconnect
                </button>
              </div>
            )}
          </div>

          {/* SAGE Agent Info */}
          <div className="p-4 border-b border-slate-800">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 rounded-lg bg-purple-500/20 border border-purple-500/30">
                <Brain className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h3 className="font-bold text-sm text-purple-400">SAGE</h3>
                <p className="text-[10px] text-slate-500">Codebase Oracle</p>
              </div>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              I can answer questions about your codebase, explain code patterns, 
              identify potential issues, and help onboard new developers.
            </p>
          </div>

          {/* Quick Questions */}
          <div className="flex-1 overflow-y-auto p-4">
            <h2 className="text-xs font-bold text-slate-400 uppercase tracking-[0.2em] mb-3">
              Quick Questions
            </h2>
            <div className="space-y-2">
              {QUICK_QUESTIONS.map((question, idx) => (
                <button
                  key={idx}
                  onClick={() => handleQuickQuestion(question)}
                  className="w-full text-left p-3 rounded-lg bg-slate-900/50 border border-slate-800 hover:border-purple-500/30 hover:bg-purple-500/5 transition-all group"
                >
                  <div className="flex items-start gap-2">
                    <FileQuestion className="w-4 h-4 text-slate-500 group-hover:text-purple-400 shrink-0 mt-0.5" />
                    <span className="text-xs text-slate-400 group-hover:text-slate-300 leading-relaxed">
                      {question}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Upload Area */}
          <div className="p-4 border-t border-slate-800">
            <div className="p-4 rounded-lg border-2 border-dashed border-slate-700 hover:border-purple-500/30 transition-colors cursor-pointer text-center">
              <Upload className="w-6 h-6 text-slate-500 mx-auto mb-2" />
              <p className="text-xs text-slate-500">
                Drop an image or error screenshot
              </p>
            </div>
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
            <div className="flex gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  ref={inputRef}
                  type="text"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-11 pr-12 py-4 text-sm focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none text-slate-200 placeholder:text-slate-600"
                  placeholder="Ask anything about your codebase..."
                  value={questionInput}
                  onChange={(e) => setQuestionInput(e.target.value)}
                  onKeyDown={(e) => handleKeyDown(e, handleAsk)}
                />
                <button
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-300 transition-all"
                  title="Voice input (coming soon)"
                >
                  <Mic className="w-4 h-4" />
                </button>
              </div>
              <button 
                onClick={handleAsk}
                disabled={!questionInput.trim() || !isConnected}
                className="bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-500 hover:to-violet-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-6 py-4 rounded-xl font-bold text-sm flex items-center gap-2 transition-all shadow-lg shadow-purple-900/30 active:scale-95"
              >
                <Send className="w-4 h-4" />
                Ask
              </button>
            </div>
            <p className="text-[10px] text-slate-600 mt-2">
              Press Enter to ask • SAGE uses RAG to ground answers in your actual code
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
