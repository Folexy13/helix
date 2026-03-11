"use client";

import { useEffect, useRef, useState } from 'react';
import { useHelixStore, AgentPersona, ConversationMessage, HitlCheckpoint } from '@/store/helixStore';
import ReactMarkdown from 'react-markdown';
import HitlInlineCard from './HitlInlineCard';
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

// Collapsible section component for structured content
function CollapsibleSection({
  title,
  icon,
  children,
  preview,
  defaultExpanded = true,
  color = '#06b6d4',
}: {
  title: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
  preview?: string;
  defaultExpanded?: boolean;
  color?: string;
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  
  return (
    <div className="my-6 rounded-2xl border border-slate-700/50 overflow-hidden bg-slate-900/40 backdrop-blur-xl shadow-xl transition-all duration-300 hover:border-slate-600 hover:shadow-2xl">
      <div 
        className="flex items-center gap-4 px-6 py-5 cursor-pointer hover:bg-slate-800/60 transition-colors group relative overflow-hidden"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        {/* Colorful accent bar */}
        <div 
          className="absolute left-0 top-0 bottom-0 w-1.5 transition-all duration-300 group-hover:w-2" 
          style={{ backgroundColor: color }}
        />
        
        {/* Glow effect behind icon */}
        <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-slate-800/80 border border-slate-700/50 shadow-inner z-10">
          <div 
            className="absolute inset-0 opacity-20 blur-md rounded-xl transition-opacity group-hover:opacity-40"
            style={{ backgroundColor: color }}
          />
          {icon}
        </div>
        
        <div className="flex-1 min-w-0">
          <span className="text-base font-bold text-slate-100 tracking-wide">{title}</span>
          {!isExpanded && preview && (
            <p className="text-sm text-slate-400 truncate mt-1 opacity-80 group-hover:opacity-100 transition-opacity">
              {preview}
            </p>
          )}
        </div>
        
        <div className={`p-2 rounded-full transition-all duration-300 ${isExpanded ? 'bg-slate-800 text-slate-300' : 'text-slate-500 group-hover:bg-slate-800 group-hover:text-slate-300'}`}>
          {isExpanded ? (
            <ChevronDown className="w-5 h-5" />
          ) : (
            <ChevronRight className="w-5 h-5" />
          )}
        </div>
      </div>
      
      <div 
        className={`transition-all duration-500 ease-in-out origin-top ${
          isExpanded ? 'max-h-[8000px] opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-8 pb-8 pt-4 border-t border-slate-700/40 bg-slate-900/20">
          {children}
        </div>
      </div>
    </div>
  );
}

// Engineering Specification Display Component
function EngineeringSpecDisplay({ content }: { content: string }) {
  // Parse the specification content into sections
  const sections: { title: string; content: string; icon: string; color: string }[] = [];
  
  // Common section patterns in engineering specs
  const sectionPatterns = [
    { pattern: /🧱\s*Engineering Specification[^\n]*/i, title: 'Engineering Specification', icon: '🧱', color: '#06b6d4' },
    { pattern: /🏗️\s*(?:Frontend\s+)?Architecture Overview[^\n]*/i, title: 'Architecture Overview', icon: '🏗️', color: '#8b5cf6' },
    { pattern: /📊\s*(?:Data Models|Database Schema)[^\n]*/i, title: 'Data Models', icon: '📊', color: '#10b981' },
    { pattern: /📁\s*Project Structure[^\n]*/i, title: 'Project Structure', icon: '📁', color: '#f59e0b' },
    { pattern: /📦\s*Dependencies[^\n]*/i, title: 'Dependencies', icon: '📦', color: '#ef4444' },
    { pattern: /⚙️\s*Environment Variables[^\n]*/i, title: 'Environment Variables', icon: '⚙️', color: '#6366f1' },
    { pattern: /🔌\s*Mock Data[^\n]*/i, title: 'Mock Data & API Patterns', icon: '🔌', color: '#22c55e' },
    { pattern: /🎨\s*UI\/UX Design[^\n]*/i, title: 'UI/UX Design', icon: '🎨', color: '#ec4899' },
    { pattern: /📋\s*Implementation Tasks[^\n]*/i, title: 'Implementation Tasks', icon: '📋', color: '#06b6d4' },
    { pattern: /🔍\s*Potential Issues[^\n]*/i, title: 'Potential Issues & Solutions', icon: '🔍', color: '#f59e0b' },
    { pattern: /🧪\s*Testing Strategy[^\n]*/i, title: 'Testing Strategy', icon: '🧪', color: '#10b981' },
  ];
  
  // Split content by major sections
  const foundSections: { title: string; content: string; icon: string; color: string; startIndex: number }[] = [];
  
  sectionPatterns.forEach(({ pattern, title, icon, color }) => {
    const match = content.match(pattern);
    if (match && match.index !== undefined) {
      foundSections.push({
        title,
        content: '',
        icon,
        color,
        startIndex: match.index,
      });
    }
  });
  
  // Sort by start index
  foundSections.sort((a, b) => a.startIndex - b.startIndex);
  
  // Extract content for each section
  for (let i = 0; i < foundSections.length; i++) {
    const currentSection = foundSections[i];
    const nextSection = foundSections[i + 1];
    const startIdx = currentSection.startIndex;
    const endIdx = nextSection ? nextSection.startIndex : content.length;
    
    // Get section content, removing the header line
    let sectionContent = content.slice(startIdx, endIdx);
    const headerMatch = sectionContent.match(/^[^\n]+\n/);
    if (headerMatch) {
      sectionContent = sectionContent.slice(headerMatch[0].length);
    }
    
    sections.push({
      title: currentSection.title,
      content: sectionContent.trim(),
      icon: currentSection.icon,
      color: currentSection.color,
    });
  }
  
  // If no sections found, return regular markdown
  if (sections.length === 0) {
    return (
      <div className="prose prose-invert prose-sm max-w-none">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    );
  }
  
  // Helper to extract preview text from section content
  const getPreview = (content: string): string => {
    // Remove markdown formatting and get first meaningful line
    const lines = content
      .replace(/[#*`]/g, '')
      .split('\n')
      .map(l => l.trim())
      .filter(l => l.length > 0 && !l.startsWith('|') && !l.startsWith('-'));
    
    if (lines.length > 0) {
      const preview = lines[0].slice(0, 50);
      return preview.length < lines[0].length ? preview + '...' : preview;
    }
    return '';
  };

  return (
    <div className="space-y-4">
      {sections.map((section, idx) => (
        <CollapsibleSection
          key={idx}
          title={section.title}
          icon={<span className="text-xl">{section.icon}</span>}
          color={section.color}
          preview={getPreview(section.content)}
          defaultExpanded={idx < 2} // First 2 sections expanded by default
        >
          <div className="prose prose-invert prose-base max-w-none 
            prose-headings:text-slate-100 prose-headings:font-bold prose-headings:text-lg prose-headings:border-b prose-headings:border-slate-800 prose-headings:pb-3 prose-headings:mb-4
            prose-p:text-slate-300 prose-p:text-base prose-p:leading-relaxed prose-p:mb-5
            prose-li:text-slate-300 prose-li:text-base prose-li:marker:text-slate-500
            prose-ul:space-y-2 prose-ol:space-y-2
            prose-strong:text-slate-200 prose-strong:font-semibold
            prose-table:text-base prose-table:border-collapse prose-table:w-full prose-table:rounded-xl prose-table:overflow-hidden
            prose-th:text-slate-200 prose-th:bg-slate-800/80 prose-th:px-5 prose-th:py-3 prose-th:text-left prose-th:font-semibold
            prose-td:text-slate-300 prose-td:px-5 prose-td:py-3 prose-td:border-b prose-td:border-slate-800/50
            prose-code:text-cyan-300 prose-code:bg-cyan-900/20 prose-code:px-2 prose-code:py-1 prose-code:rounded-md prose-code:font-mono prose-code:font-medium prose-code:before:content-none prose-code:after:content-none
            prose-pre:bg-[#0d1117] prose-pre:border prose-pre:border-slate-800/80 prose-pre:shadow-2xl prose-pre:rounded-2xl prose-pre:p-5
            prose-a:text-cyan-400 prose-a:no-underline hover:prose-a:underline
            [&>*:first-child]:mt-0 [&>*:last-child]:mb-0"
          >
            <ReactMarkdown>{section.content}</ReactMarkdown>
          </div>
        </CollapsibleSection>
      ))}
    </div>
  );
}

// Check if content looks like an engineering specification
function isEngineeringSpec(content: string): boolean {
  const specIndicators = [
    '🧱 Engineering Specification',
    '🏗️ Architecture Overview',
    '📊 Database Schema',
    '📁 Project Structure',
    '📦 Dependencies',
    '📋 Implementation Tasks',
  ];
  
  let matchCount = 0;
  for (const indicator of specIndicators) {
    if (content.includes(indicator)) {
      matchCount++;
    }
  }
  
  return matchCount >= 2; // At least 2 indicators suggest it's a spec
}

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
function RichContent({ content, isResult, speaker }: { content: string; isResult: boolean; speaker?: string }) {
  // Check if this is an engineering specification from the planner
  const isPlannerSpec = (speaker?.toUpperCase() === 'PLANNER' || speaker?.toUpperCase() === 'ORCHESTRATOR') && isEngineeringSpec(content);
  
  if (isPlannerSpec) {
    return <EngineeringSpecDisplay content={content} />;
  }
  
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
      <div className="flex items-start gap-4 justify-end animate-in fade-in slide-in-from-right-2 duration-500 mb-6">
        <div className="max-w-[85%] lg:max-w-[75%]">
          <div className="flex items-center gap-2 mb-1.5 justify-end">
            <span className="text-xs text-slate-500 font-medium">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
            <span className="text-sm font-bold text-blue-400">You</span>
          </div>
          <div className="px-5 py-4 rounded-3xl rounded-tr-sm bg-gradient-to-br from-blue-600 to-blue-700 text-white text-base leading-relaxed shadow-lg shadow-blue-900/20">
            {message.content}
          </div>
        </div>
        <div className="w-10 h-10 rounded-full bg-blue-500/20 border border-blue-500/30 flex items-center justify-center shrink-0 mt-6 shadow-inner">
          <User className="w-5 h-5 text-blue-400" />
        </div>
      </div>
    );
  }
  
  // Agent/System messages
  return (
    <div className="flex items-start gap-4 animate-in fade-in slide-in-from-left-2 duration-500 mb-6">
      <div className="mt-6">
        <AgentAvatar persona={persona} size="md" />
      </div>
      <div className="flex-1 min-w-0 max-w-[95%] lg:max-w-[85%]">
        <div className="flex items-center gap-3 mb-1.5">
          <span className="text-sm font-bold tracking-wide" style={{ color: persona?.color || '#94a3b8' }}>
            {persona?.name || message.speaker.toUpperCase()}
          </span>
          {!isSystem && (
            <span className="text-xs text-slate-500 font-medium">{persona?.title}</span>
          )}
          <div className="flex items-center gap-2 ml-auto">
            <MessageTypeIcon type={logType} />
            <span className="text-xs text-slate-500 font-medium">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        </div>
        
        <div className={cn(
          "rounded-3xl rounded-tl-sm text-base leading-relaxed shadow-lg",
          isResult 
            ? "bg-[#0b101a] border border-slate-700/80 p-6" 
            : logType === 'thought'
            ? "bg-purple-500/10 border border-purple-500/20 px-5 py-4 text-purple-100"
            : logType === 'action'
            ? "bg-yellow-500/10 border border-yellow-500/20 px-5 py-4 text-yellow-100"
            : logType === 'error'
            ? "bg-rose-500/10 border border-rose-500/20 px-5 py-4 text-rose-100"
            : "bg-slate-800/40 border border-slate-700/50 px-5 py-4 text-slate-200"
        )}>
          {isResult ? (
            <RichContent content={message.content} isResult={true} speaker={message.speaker} />
          ) : (
            <p>{message.content}</p>
          )}
        </div>
      </div>
    </div>
  );
}

interface AgentLogStreamProps {
  agentFilter?: string | null;
  pillar?: number; // Optional pillar to show pillar-specific conversation
}

export default function AgentLogStream({ agentFilter, pillar }: AgentLogStreamProps) {
  const { 
    conversation, 
    pillarConversations,
    activePillar,
    agentPersonas, 
    typingAgents, 
    isProcessing, 
    pendingCheckpoints 
  } = useHelixStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  
  // Determine which conversation to show
  const currentPillar = pillar || activePillar || 1;
  const pillarKey = `pillar${currentPillar}` as keyof typeof pillarConversations;
  
  // Use pillar-specific conversation if pillar is specified, otherwise use unified
  const baseConversation = pillar 
    ? pillarConversations[pillarKey] || []
    : conversation;
  
  // Auto-scroll to bottom on new messages or checkpoints
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [baseConversation.length, typingAgents.size, pendingCheckpoints.length]);

  // Get persona for a speaker
  const getPersona = (speaker: string): AgentPersona | undefined => {
    return agentPersonas[speaker.toUpperCase()];
  };

  // Convert typing agents Set to array
  const typingAgentsArray = Array.from(typingAgents);
  
  // Filter conversation by agent if filter is set
  const filteredConversation = agentFilter 
    ? baseConversation.filter(msg => 
        msg.speaker.toUpperCase() === agentFilter.toUpperCase() || 
        msg.speaker === 'user' || 
        msg.speaker === 'system'
      )
    : baseConversation;

  if (baseConversation.length === 0 && !isProcessing && pendingCheckpoints.length === 0) {
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
      {/* Filter indicator */}
      {agentFilter && (
        <div className="sticky top-0 z-10 px-3 py-2 bg-slate-900/90 backdrop-blur-sm rounded-lg border border-slate-700/50 mb-2">
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">Showing output from:</span>
            <span className="font-bold" style={{ color: getPersona(agentFilter)?.color || '#94a3b8' }}>
              {agentFilter}
            </span>
            <span className="text-slate-500">({filteredConversation.length} messages)</span>
          </div>
        </div>
      )}
      
      {/* Conversation messages */}
      {filteredConversation.map((message) => (
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
      
      {/* Inline HITL Checkpoints - shown directly in the conversation flow */}
      {pendingCheckpoints.map((checkpoint, index) => (
        <HitlInlineCard 
          key={checkpoint.id} 
          checkpoint={checkpoint}
          isLatest={index === pendingCheckpoints.length - 1}
        />
      ))}
      
      {/* Processing indicator when no typing agents and no checkpoints */}
      {isProcessing && typingAgentsArray.length === 0 && pendingCheckpoints.length === 0 && baseConversation.length > 0 && (
        <div className="flex items-center justify-center gap-2 py-4">
          <Loader2 className="w-4 h-4 text-slate-500 animate-spin" />
          <span className="text-xs text-slate-500">Processing...</span>
        </div>
      )}
      
      <div ref={bottomRef} />
    </div>
  );
}
