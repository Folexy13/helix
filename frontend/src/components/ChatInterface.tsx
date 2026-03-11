"use client";

import { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Plus,
  ChevronRight,
  Sparkles,
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
  Zap,
  ArrowUp,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ConversationMessage, HitlCheckpoint, useHelixStore } from '@/store/helixStore';
import { useHelixSocket } from '@/hooks/useHelixSocket';
import ReactMarkdown from 'react-markdown';

// Agent avatar mapping
const agentAvatars: Record<string, { icon: React.ElementType; color: string; name: string }> = {
  'ROUTER': { icon: Zap, color: '#f97316', name: 'Router' },
  'ARIA': { icon: TrendingUp, color: '#3b82f6', name: 'Aria' },
  'FELIX': { icon: DollarSign, color: '#22c55e', name: 'Felix' },
  'NOVA': { icon: Megaphone, color: '#ec4899', name: 'Nova' },
  'JUDGE': { icon: Gavel, color: '#8b5cf6', name: 'Judge' },
  'PLANNER': { icon: FileText, color: '#06b6d4', name: 'Planner' },
  'CODER': { icon: Code2, color: '#10b981', name: 'Coder' },
  'TESTER': { icon: TestTube, color: '#f59e0b', name: 'Tester' },
  'REVIEWER': { icon: GitPullRequest, color: '#ef4444', name: 'Reviewer' },
  'INDEXER': { icon: Search, color: '#8b5cf6', name: 'Indexer' },
  'SAGE': { icon: Brain, color: '#06b6d4', name: 'Sage' },
};

// Typing indicator - Claude.ai style (subtle)
function TypingIndicator({ agentName }: { agentName: string }) {
  return (
    <div className="text-slate-500 text-sm">
      <span>{agentName} is thinking...</span>
    </div>
  );
}

// User message - simple right-aligned text
function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex justify-end mb-6">
      <div className="max-w-[85%] text-slate-100 text-[15px] leading-relaxed">
        {content}
      </div>
    </div>
  );
}

// Agent message - Claude.ai style (clean text, NO box)
function AgentMessage({ 
  speaker, 
  content,
}: { 
  speaker: string;
  content: string;
}) {
  const agent = agentAvatars[speaker.toUpperCase()];
  
  return (
    <div className="mb-6">
      {/* Message content - clean text like Claude.ai */}
      <div className="text-slate-200 text-[15px] leading-[1.7] prose prose-invert prose-sm max-w-none
        prose-p:my-3 prose-p:leading-[1.7]
        prose-headings:text-slate-100 prose-headings:font-semibold prose-headings:mt-6 prose-headings:mb-3
        prose-strong:text-slate-100 prose-strong:font-semibold
        prose-code:text-orange-300 prose-code:bg-[#2a2a2a] prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-sm prose-code:font-normal prose-code:before:content-none prose-code:after:content-none
        prose-pre:bg-[#1e1e1e] prose-pre:border prose-pre:border-[#333] prose-pre:rounded-lg
        prose-ul:my-3 prose-ol:my-3 prose-li:my-1
        prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline
      ">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </div>
  );
}

// HITL Checkpoint - inline question style like Claude
function HitlCheckpointInline({ 
  checkpoint,
  onSubmit,
}: { 
  checkpoint: HitlCheckpoint;
  onSubmit: (decision: string, input: string) => void;
}) {
  const [input, setInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  
  useEffect(() => {
    inputRef.current?.focus();
  }, []);
  
  const handleSubmit = () => {
    if (input.trim()) {
      setIsSubmitting(true);
      onSubmit('approve', input.trim());
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="mb-6">
      {/* Question content - same style as agent message */}
      <div className="text-slate-200 text-[15px] leading-[1.7] prose prose-invert prose-sm max-w-none mb-4
        prose-p:my-3 prose-p:leading-[1.7]
        prose-strong:text-slate-100
      ">
        <ReactMarkdown>{checkpoint.prompt}</ReactMarkdown>
      </div>
      
      {/* Suggestions as quick replies */}
      {checkpoint.suggestions && checkpoint.suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {checkpoint.suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => setInput(s)}
              className="text-sm px-3 py-1.5 rounded-full border border-[#444] text-slate-400 hover:text-white hover:border-[#666] hover:bg-[#333] transition-all"
            >
              {s}
            </button>
          ))}
        </div>
      )}
      
      {/* Inline input - minimal style */}
      <div className="flex items-center gap-3">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your response..."
          disabled={isSubmitting}
          className="flex-1 bg-transparent border-b border-[#444] focus:border-[#666] px-0 py-2 text-[15px] text-slate-200 placeholder:text-slate-600 outline-none disabled:opacity-50 transition-colors"
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || isSubmitting}
          className={cn(
            "p-2 rounded-full transition-all",
            input.trim() && !isSubmitting
              ? "bg-white text-black hover:bg-slate-200"
              : "bg-[#333] text-slate-600 cursor-not-allowed"
          )}
        >
          <ArrowUp className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

interface ChatInterfaceProps {
  messages: ConversationMessage[];
  onSendMessage: (message: string) => void;
  isProcessing?: boolean;
  activeAgent?: string;
  placeholder?: string;
  pillar?: number;
}

export default function ChatInterface({
  messages,
  onSendMessage,
  isProcessing = false,
  activeAgent,
  placeholder = "Reply...",
  pillar = 1,
}: ChatInterfaceProps) {
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  
  // Get pending checkpoints from store
  const { pendingCheckpoints } = useHelixStore();
  const { sendHitlDecision } = useHelixSocket();
  
  // Filter checkpoints for current pillar
  const pillarCheckpoints = pendingCheckpoints.filter(cp => cp.pillar === pillar);
  const latestCheckpoint = pillarCheckpoints[pillarCheckpoints.length - 1];

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing, latestCheckpoint]);

  // Auto-focus input
  useEffect(() => {
    if (!latestCheckpoint) {
      inputRef.current?.focus();
    }
  }, [latestCheckpoint]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSend = () => {
    if (input.trim() && !isProcessing) {
      onSendMessage(input.trim());
      setInput('');
      if (inputRef.current) {
        inputRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCheckpointSubmit = (decision: string, userInput: string) => {
    if (latestCheckpoint) {
      sendHitlDecision(latestCheckpoint.id, decision, userInput);
    }
  };

  const agent = activeAgent ? agentAvatars[activeAgent.toUpperCase()] : null;

  return (
    <div className="flex flex-col h-full bg-[#212121]">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-[48rem] mx-auto px-4 py-6">
          {messages.length === 0 && !latestCheckpoint ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
              <h1 className="text-2xl font-normal text-slate-200 mb-2">
                {pillar === 1 && "What startup idea can I help you analyze?"}
                {pillar === 2 && "What feature would you like to build?"}
                {pillar === 3 && "What would you like to know about your codebase?"}
              </h1>
              <p className="text-sm text-slate-500">
                {pillar === 1 && "I'll coordinate the founding team to evaluate your concept."}
                {pillar === 2 && "The engineering team will plan and implement it."}
                {pillar === 3 && "Ask anything about your code architecture."}
              </p>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <div key={message.id}>
                  {message.speaker === 'user' ? (
                    <UserMessage content={message.content} />
                  ) : (
                    <AgentMessage 
                      speaker={message.speaker}
                      content={message.content}
                    />
                  )}
                </div>
              ))}
              
              {/* Show HITL checkpoint if pending */}
              {latestCheckpoint && (
                <HitlCheckpointInline 
                  checkpoint={latestCheckpoint}
                  onSubmit={handleCheckpointSubmit}
                />
              )}
              
              {/* Typing indicator */}
              {isProcessing && activeAgent && agent && !latestCheckpoint && (
                <TypingIndicator agentName={agent.name} />
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area - Claude.ai style */}
      <div className="border-t border-[#333] bg-[#212121]">
        <div className="max-w-[48rem] mx-auto px-4 py-4">
          <div className="relative flex items-end bg-[#2f2f2f] rounded-2xl border border-[#444] focus-within:border-[#666] transition-colors">
            {/* Plus button */}
            <button 
              className="p-3 text-slate-400 hover:text-slate-300 transition-colors"
              title="Attach"
            >
              <Plus className="w-5 h-5" />
            </button>

            {/* Text input */}
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={isProcessing && !latestCheckpoint}
              rows={1}
              className="flex-1 bg-transparent py-3 text-[15px] text-slate-200 placeholder:text-slate-500 resize-none outline-none max-h-[200px] disabled:opacity-50"
            />

            {/* Send button */}
            <button
              onClick={handleSend}
              disabled={!input.trim() || (isProcessing && !latestCheckpoint)}
              className={cn(
                "m-2 p-2 rounded-full transition-all",
                input.trim() && !(isProcessing && !latestCheckpoint)
                  ? "bg-white text-black hover:bg-slate-200"
                  : "bg-[#444] text-slate-600 cursor-not-allowed"
              )}
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>

          {/* Helper text */}
          <p className="text-[11px] text-slate-600 text-center mt-2">
            Helix can make mistakes. Please verify important information.
          </p>
        </div>
      </div>
    </div>
  );
}
