"use client";

import { useEffect, useRef, useState } from 'react';
import { useHelixStore, AgentPersona, ConversationMessage } from '@/store/helixStore';
import ReactMarkdown from 'react-markdown';
import { 
  Brain, 
  Zap, 
  CheckCircle, 
  AlertCircle, 
  ArrowRight,
  User,
  Loader2,
  ChevronDown,
  ChevronRight,
  Copy,
  Check,
  FileCode,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Collapsible code block component
function CollapsibleCodeBlock({ 
  content, 
  language = 'text',
  filename,
  defaultExpanded = false 
}: { 
  content: string; 
  language?: string;
  filename?: string;
  defaultExpanded?: boolean;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [copied, setCopied] = useState(false);
  
  const lines = content.split('\n');
  const lineCount = lines.length;
  const preview = lines.slice(0, 3).join('\n');
  
  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className="my-2 rounded-lg border border-slate-700 overflow-hidden bg-slate-900/80">
      {/* Header */}
      <div 
        className="flex items-center justify-between px-3 py-2 bg-slate-800/50 cursor-pointer hover:bg-slate-800/70 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-slate-400" />
          ) : (
            <ChevronRight className="w-4 h-4 text-slate-400" />
          )}
          <FileCode className="w-4 h-4 text-blue-400" />
          <span className="text-xs font-medium text-slate-300">
            {filename || language || 'Code'}
          </span>
          <span className="text-[10px] text-slate-500">
            {lineCount} lines
          </span>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation();
            handleCopy();
          }}
          className="p-1 rounded hover:bg-slate-700 transition-colors"
          title="Copy code"
        >
          {copied ? (
            <Check className="w-3.5 h-3.5 text-green-400" />
          ) : (
            <Copy className="w-3.5 h-3.5 text-slate-400" />
          )}
        </button>
      </div>
      
      {/* Code content */}
      <div className={cn(
        "overflow-hidden transition-all duration-200",
        isExpanded ? "max-h-[500px]" : "max-h-20"
      )}>
        <pre className="p-3 text-xs font-mono text-slate-300 overflow-x-auto">
          <code>{isExpanded ? content : preview + (lineCount > 3 ? '\n...' : '')}</code>
        </pre>
      </div>
      
      {/* Expand hint */}
      {!isExpanded && lineCount > 3 && (
        <div className="px-3 py-1.5 text-[10px] text-slate-500 bg-slate-800/30 border-t border-slate-700/50">
          Click to expand ({lineCount - 3} more lines)
        </div>
      )}
    </div>
  );
}

// Parse content for code blocks and render them collapsible
function RichContent({ content, isResult }: { content: string; isResult: boolean }) {
  // Check if content has code blocks
  const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g;
  const hasCodeBlocks = codeBlockRegex.test(content);
  
  if (!hasCodeBlocks || !isResult) {
    // No code blocks or not a result - render as markdown
    return (
      <div className="prose prose-invert prose-sm max-w-none prose-headings:text-blue-400 prose-headings:font-bold prose-h1:text-lg prose-h2:text-base prose-h3:text-sm prose-code:text-blue-200 prose-code:bg-blue-500/10 prose-code:px-1 prose-code:rounded prose-hr:border-slate-700">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    );
  }
  
  // Split content by code blocks and render each part
  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match;
  let partIndex = 0;
  
  // Reset regex
  codeBlockRegex.lastIndex = 0;
  
  while ((match = codeBlockRegex.exec(content)) !== null) {
    // Add text before code block
    if (match.index > lastIndex) {
      const textBefore = content.slice(lastIndex, match.index);
      if (textBefore.trim()) {
        parts.push(
          <div key={`text-${partIndex}`} className="prose prose-invert prose-sm max-w-none prose-headings:text-blue-400 prose-headings:font-bold prose-code:text-blue-200 prose-code:bg-blue-500/10 prose-code:px-1 prose-code:rounded">
            <ReactMarkdown>{textBefore}</ReactMarkdown>
          </div>
        );
      }
    }
    
    // Add collapsible code block
    const language = match[1] || 'text';
    const code = match[2].trim();
    parts.push(
      <CollapsibleCodeBlock 
        key={`code-${partIndex}`}
        content={code}
        language={language}
        defaultExpanded={code.split('\n').length <= 10}
      />
    );
    
    lastIndex = match.index + match[0].length;
    partIndex++;
  }
  
  // Add remaining text after last code block
  if (lastIndex < content.length) {
    const textAfter = content.slice(lastIndex);
    if (textAfter.trim()) {
      parts.push(
        <div key={`text-${partIndex}`} className="prose prose-invert prose-sm max-w-none prose-headings:text-blue-400 prose-headings:font-bold prose-code:text-blue-200 prose-code:bg-blue-500/10 prose-code:px-1 prose-code:rounded">
          <ReactMarkdown>{textAfter}</ReactMarkdown>
        </div>
      );
    }
  }
  
  return <>{parts}</>;
}

// Agent avatar component
function AgentAvatar({ persona, size = 'md' }: { persona?: AgentPersona; size?: 'sm' | 'md' }) {
  const sizeClasses = {
    sm: 'w-8 h-8 text-base',
    md: 'w-10 h-10 text-lg',
  };
  
  return (
    <div 
      className={cn(
        "rounded-xl flex items-center justify-center font-bold shrink-0 shadow-lg",
        sizeClasses[size]
      )}
      style={{ 
        backgroundColor: persona?.color ? `${persona.color}15` : '#64748b15',
        borderColor: persona?.color ? `${persona.color}30` : '#64748b30',
        borderWidth: 1,
      }}
    >
      {persona?.avatar || '🤖'}
    </div>
  );
}

// Typing indicator
function TypingIndicator({ agent, persona }: { agent: string; persona?: AgentPersona }) {
  return (
    <div className="flex items-start gap-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
      <AgentAvatar persona={persona} size="sm" />
      <div className="flex-1">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold" style={{ color: persona?.color || '#94a3b8' }}>
            {persona?.name || agent}
          </span>
          <span className="text-[10px] text-slate-600">{persona?.title}</span>
        </div>
        <div className="inline-flex items-center gap-1 px-3 py-2 rounded-xl bg-slate-800/50 border border-slate-700/50">
          <div className="flex gap-1">
            <span className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '0ms' }} />
            <span className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '150ms' }} />
            <span className="w-2 h-2 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
          <span className="text-xs text-slate-500 ml-2">thinking...</span>
        </div>
      </div>
    </div>
  );
}

// Message type icon
function MessageTypeIcon({ type }: { type: string }) {
  switch (type) {
    case 'thought':
      return <Brain className="w-3 h-3 text-purple-400" />;
    case 'action':
      return <Zap className="w-3 h-3 text-yellow-400" />;
    case 'result':
      return <CheckCircle className="w-3 h-3 text-emerald-400" />;
    case 'error':
      return <AlertCircle className="w-3 h-3 text-rose-400" />;
    case 'handoff':
      return <ArrowRight className="w-3 h-3 text-blue-400" />;
    default:
      return null;
  }
}

// Single conversation message
function ConversationItem({ message, persona }: { message: ConversationMessage; persona?: AgentPersona }) {
  const isUser = message.speaker === 'user';
  const isSystem = message.speaker === 'system';
  const isHandoff = message.type === 'handoff';
  const isResult = message.type === 'result';
  const logType = (message.metadata?.logType as string) || message.type;
  
  // Handoff messages get special treatment
  if (isHandoff) {
    return (
      <div className="flex items-center justify-center gap-2 py-2 animate-in fade-in duration-300">
        <div className="h-px flex-1 bg-gradient-to-r from-transparent to-slate-700" />
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800/50 border border-slate-700/50">
          <ArrowRight className="w-3 h-3 text-blue-400" />
          <span className="text-[10px] font-medium text-slate-400">{message.content}</span>
        </div>
        <div className="h-px flex-1 bg-gradient-to-l from-transparent to-slate-700" />
      </div>
    );
  }
  
  // User messages
  if (isUser) {
    return (
      <div className="flex items-start gap-3 justify-end animate-in fade-in slide-in-from-right-2 duration-300">
        <div className="max-w-[85%]">
          <div className="flex items-center gap-2 mb-1 justify-end">
            <span className="text-[10px] text-slate-600">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span className="text-xs font-bold text-blue-400">You</span>
          </div>
          <div className="px-4 py-3 rounded-2xl rounded-br-md bg-blue-600 text-white text-sm leading-relaxed">
            {message.content}
          </div>
        </div>
        <div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500/30 flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-blue-400" />
        </div>
      </div>
    );
  }
  
  // Agent/System messages
  return (
    <div className="flex items-start gap-3 animate-in fade-in slide-in-from-left-2 duration-300">
      <AgentAvatar persona={persona} size="sm" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-bold" style={{ color: persona?.color || '#94a3b8' }}>
            {persona?.name || message.speaker.toUpperCase()}
          </span>
          {!isSystem && (
            <span className="text-[10px] text-slate-600">{persona?.title}</span>
          )}
          <div className="flex items-center gap-1 ml-auto">
            <MessageTypeIcon type={logType} />
            <span className="text-[10px] text-slate-600">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </div>
        
        <div className={cn(
          "rounded-2xl rounded-tl-md text-sm leading-relaxed",
          isResult 
            ? "bg-slate-900/80 border border-slate-700 p-4" 
            : logType === 'thought'
            ? "bg-purple-500/10 border border-purple-500/20 px-4 py-2 text-purple-200"
            : logType === 'action'
            ? "bg-yellow-500/10 border border-yellow-500/20 px-4 py-2 text-yellow-200"
            : logType === 'error'
            ? "bg-rose-500/10 border border-rose-500/20 px-4 py-2 text-rose-200"
            : "bg-slate-800/50 border border-slate-700/50 px-4 py-2 text-slate-300"
        )}>
          {isResult ? (
            <RichContent content={message.content} isResult={true} />
          ) : (
            <p>{message.content}</p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AgentLogStream() {
  const { conversation, agentPersonas, typingAgents, isProcessing } = useHelixStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation.length, typingAgents.size]);

  // Get persona for a speaker
  const getPersona = (speaker: string): AgentPersona | undefined => {
    return agentPersonas[speaker.toUpperCase()];
  };

  // Convert typing agents Set to array
  const typingAgentsArray = Array.from(typingAgents);

  if (conversation.length === 0 && !isProcessing) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-600 p-8">
        <div className="w-16 h-16 rounded-2xl bg-slate-800/50 border border-slate-700/50 flex items-center justify-center mb-4">
          <Brain className="w-8 h-8 text-slate-600" />
        </div>
        <p className="text-sm font-medium text-center">
          Start a conversation to see agent activity
        </p>
        <p className="text-xs text-slate-700 mt-1 text-center">
          Enter your idea or request above
        </p>
      </div>
    );
  }

  return (
    <div 
      ref={scrollRef}
      className="h-full overflow-y-auto space-y-4 pr-2 custom-scrollbar"
    >
      {/* Conversation messages */}
      {conversation.map((message) => (
        <ConversationItem 
          key={message.id} 
          message={message} 
          persona={getPersona(message.speaker)}
        />
      ))}
      
      {/* Typing indicators */}
      {typingAgentsArray.map((agent) => (
        <TypingIndicator 
          key={agent} 
          agent={agent} 
          persona={getPersona(agent)}
        />
      ))}
      
      {/* Processing indicator when no typing agents */}
      {isProcessing && typingAgentsArray.length === 0 && conversation.length > 0 && (
        <div className="flex items-center justify-center gap-2 py-4">
          <Loader2 className="w-4 h-4 text-slate-500 animate-spin" />
          <span className="text-xs text-slate-500">Processing...</span>
        </div>
      )}
      
      <div ref={bottomRef} />
    </div>
  );
}
