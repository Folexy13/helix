"use client";

import { useState, useMemo, useEffect, useRef } from 'react';
import { useHelixStore, HitlCheckpoint, AgentPersona, NextStepOption } from '@/store/helixStore';
import { useRouter } from 'next/navigation';
import { useHelixSocket } from '@/hooks/useHelixSocket';
import ReactMarkdown from 'react-markdown';
import { 
  CheckCircle2, 
  XCircle, 
  Edit3, 
  UserCheck, 
  ChevronRight,
  MessageSquare,
  ClipboardList,
  Sparkles,
  Send,
  User,
  Bot,
  ArrowRight,
  Lightbulb,
  History,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Agent avatar component
function AgentAvatar({ persona, size = 'md' }: { persona?: AgentPersona; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-6 h-6 text-sm',
    md: 'w-10 h-10 text-lg',
    lg: 'w-14 h-14 text-2xl',
  };
  
  return (
    <div 
      className={cn(
        "rounded-2xl flex items-center justify-center font-bold shrink-0",
        sizeClasses[size]
      )}
      style={{ 
        backgroundColor: persona?.color ? `${persona.color}20` : '#64748b20',
        borderColor: persona?.color ? `${persona.color}40` : '#64748b40',
        borderWidth: 1,
      }}
    >
      {persona?.avatar || '🤖'}
    </div>
  );
}

// Conversation bubble component
function ConversationBubble({ 
  speaker, 
  content, 
  isUser,
  persona,
}: { 
  speaker: string; 
  content: string; 
  isUser: boolean;
  persona?: AgentPersona;
}) {
  return (
    <div className={cn(
      "flex gap-3 animate-in slide-in-from-bottom-2 duration-300",
      isUser ? "flex-row-reverse" : "flex-row"
    )}>
      {isUser ? (
        <div className="w-8 h-8 rounded-full bg-blue-500/20 border border-blue-500/30 flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-blue-400" />
        </div>
      ) : (
        <AgentAvatar persona={persona} size="sm" />
      )}
      <div className={cn(
        "max-w-[80%] rounded-2xl px-4 py-3 text-sm",
        isUser 
          ? "bg-blue-600 text-white rounded-br-md" 
          : "bg-slate-800 text-slate-200 rounded-bl-md border border-slate-700"
      )}>
        <p className="leading-relaxed">{content}</p>
      </div>
    </div>
  );
}

// Smart suggestion chip
function SuggestionChip({ text, onClick }: { text: string; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:bg-slate-700 hover:border-slate-600 transition-all flex items-center gap-1.5 group"
    >
      <Lightbulb className="w-3 h-3 text-yellow-500 group-hover:text-yellow-400" />
      {text}
    </button>
  );
}

// Next step option card for smart navigation
function NextStepCard({ 
  option, 
  onClick 
}: { 
  option: { id: string; label: string; description: string; color: string }; 
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full p-5 rounded-2xl border-2 text-left transition-all duration-300 hover:scale-[1.02] active:scale-[0.98] group"
      style={{
        backgroundColor: `${option.color}10`,
        borderColor: `${option.color}30`,
      }}
    >
      <div className="flex items-center gap-3">
        <div 
          className="text-2xl"
          style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))' }}
        >
          {option.label.split(' ')[0]}
        </div>
        <div className="flex-1">
          <h3 
            className="font-bold text-base mb-0.5 group-hover:translate-x-1 transition-transform"
            style={{ color: option.color }}
          >
            {option.label.split(' ').slice(1).join(' ')}
          </h3>
          <p className="text-xs text-slate-400">{option.description}</p>
        </div>
        <ArrowRight 
          className="w-5 h-5 opacity-0 group-hover:opacity-100 group-hover:translate-x-1 transition-all"
          style={{ color: option.color }}
        />
      </div>
    </button>
  );
}

export default function HitlDrawer() {
  const { pendingCheckpoints, agentPersonas, conversation } = useHelixStore();
  const { sendHitlDecision, sendUserMessage } = useHelixSocket();
  const router = useRouter();
  
  // Form state
  const [generalFeedback, setGeneralFeedback] = useState('');
  const [questionAnswers, setQuestionAnswers] = useState<Record<string, string>>({});
  const [followUpMessage, setFollowUpMessage] = useState('');
  const [showConversationHistory, setShowConversationHistory] = useState(false);
  
  const conversationEndRef = useRef<HTMLDivElement>(null);

  const isOpen = pendingCheckpoints.length > 0;
  const currentCheckpoint = pendingCheckpoints[0];
  const persona = currentCheckpoint?.agent_persona || agentPersonas[currentCheckpoint?.agent?.toUpperCase() || ''];

  // Parse questions from prompt or use structured questions
  const questions = useMemo(() => {
    if (!currentCheckpoint) return [];
    
    // Use structured questions if available
    if (currentCheckpoint.questions && currentCheckpoint.questions.length > 0) {
      return currentCheckpoint.questions;
    }
    
    // Fall back to parsing from prompt
    const prompt = currentCheckpoint.prompt;
    if (!prompt || !prompt.includes('\n-')) return [];
    
    return prompt
      .split('\n')
      .filter(line => line.trim().startsWith('-'))
      .map((line, idx) => ({
        id: `q_${idx}`,
        text: line.replace(/^- /, '').trim(),
        type: 'text' as const,
        required: true,
        placeholder: 'Your answer...',
      }));
  }, [currentCheckpoint]);

  // Get recent conversation for context
  const recentConversation = useMemo(() => {
    if (!currentCheckpoint?.conversation_history) return [];
    return currentCheckpoint.conversation_history.slice(-5);
  }, [currentCheckpoint]);

  // Scroll to bottom of conversation
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation]);

  // Reset form when checkpoint changes - using key pattern instead of effect
  const checkpointId = currentCheckpoint?.id;
  const prevCheckpointIdRef = useRef(checkpointId);
  
  if (checkpointId !== prevCheckpointIdRef.current) {
    prevCheckpointIdRef.current = checkpointId;
    // These will be reset on next render cycle
  }

  if (!isOpen || !currentCheckpoint) return null;

  const handleDecision = (decision: string) => {
    // Combine all answers into structured format
    const fieldResponses: Record<string, string> = {};
    
    questions.forEach((q) => {
      fieldResponses[q.id] = questionAnswers[q.id] || '';
    });
    
    // Build user input string
    let finalInput = "";
    
    if (questions.length > 0) {
      finalInput += "--- ANSWERS ---\n";
      questions.forEach((q) => {
        const answer = questionAnswers[q.id] || "No answer provided.";
        finalInput += `Q: ${q.text}\nA: ${answer}\n\n`;
      });
    }

    if (generalFeedback.trim()) {
      finalInput += "--- FEEDBACK ---\n";
      finalInput += generalFeedback;
    }

    sendHitlDecision(currentCheckpoint.id, decision, finalInput.trim(), fieldResponses);
  };

  const handleFollowUp = () => {
    if (followUpMessage.trim()) {
      sendUserMessage(followUpMessage, currentCheckpoint.agent);
      setFollowUpMessage('');
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setGeneralFeedback(prev => prev ? `${prev}\n${suggestion}` : suggestion);
  };

  const handleNextStepAction = (option: NextStepOption) => {
    // Send the decision to backend
    sendHitlDecision(currentCheckpoint.id, option.id, `Selected: ${option.label}`, {});
    
    // Handle navigation based on action
    switch (option.action) {
      case 'navigate_pillar2':
        // Navigate to Pillar 2
        router.push('/pillar2');
        break;
      case 'restart_pillar1':
        // Stay on Pillar 1 for refinement
        router.push('/pillar1');
        break;
      case 'save_and_exit':
        // Go to home
        router.push('/');
        break;
      case 'create_pr':
        // Navigate to Pillar 3 for Nova Act
        router.push('/pillar3');
        break;
      case 'review_code':
        // Stay on current page
        break;
      case 'request_changes':
        // Stay on current page for modifications
        break;
      default:
        console.log('Unknown action:', option.action);
    }
  };

  const getButtonStyles = (option: string) => {
    switch (option.toLowerCase()) {
      case 'approve': return 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-400/20 shadow-emerald-900/20';
      case 'reject': return 'bg-rose-600 hover:bg-rose-500 text-white border-rose-400/20 shadow-rose-900/20';
      case 'edit': return 'bg-blue-600 hover:bg-blue-500 text-white border-blue-400/20 shadow-blue-900/20';
      case 'fix': return 'bg-amber-600 hover:bg-amber-500 text-white border-amber-400/20 shadow-amber-900/20';
      case 'ignore': return 'bg-slate-600 hover:bg-slate-500 text-white border-slate-400/20 shadow-slate-900/20';
      case 'explain': return 'bg-purple-600 hover:bg-purple-500 text-white border-purple-400/20 shadow-purple-900/20';
      default: return 'bg-slate-800 hover:bg-slate-700 text-white border-slate-600/20';
    }
  };

  const getIcon = (option: string) => {
    switch (option.toLowerCase()) {
      case 'approve': return <CheckCircle2 className="w-4 h-4" />;
      case 'reject': return <XCircle className="w-4 h-4" />;
      case 'edit': return <Edit3 className="w-4 h-4" />;
      case 'fix': return <Sparkles className="w-4 h-4" />;
      case 'ignore': return <ArrowRight className="w-4 h-4" />;
      case 'explain': return <MessageSquare className="w-4 h-4" />;
      default: return <ChevronRight className="w-4 h-4" />;
    }
  };

  return (
    <div className="fixed inset-0 z-50 pointer-events-none">
      {/* Backdrop */}
      <div className={cn(
        "absolute inset-0 bg-black/70 backdrop-blur-sm transition-opacity duration-500 pointer-events-auto",
        isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
      )} />

      {/* Drawer */}
      <div className={cn(
        "absolute top-0 right-0 h-full w-[600px] bg-[#0a0f1a] border-l border-slate-800 shadow-2xl transition-transform duration-500 ease-out pointer-events-auto flex flex-col",
        isOpen ? "translate-x-0" : "translate-x-full"
      )}>
        {/* Header */}
        <div className="p-5 border-b border-slate-800 bg-gradient-to-r from-slate-900/80 to-slate-900/40 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            <AgentAvatar persona={persona} size="lg" />
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                {persona?.name || currentCheckpoint.agent.toUpperCase()}
                <span className="text-xs font-normal text-slate-500">needs your input</span>
              </h2>
              <p className="text-xs text-slate-400">{persona?.title || 'AI Agent'}</p>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[10px] font-bold text-orange-500 uppercase tracking-widest bg-orange-500/10 px-2 py-0.5 rounded border border-orange-500/20">
                  {currentCheckpoint.gate_type.replace(/_/g, ' ').replace('gate ', '')}
                </span>
              </div>
            </div>
          </div>
          
          {/* Context toggle */}
          {recentConversation.length > 0 && (
            <button
              onClick={() => setShowConversationHistory(!showConversationHistory)}
              className={cn(
                "p-2 rounded-lg transition-all",
                showConversationHistory 
                  ? "bg-blue-500/20 text-blue-400" 
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              )}
              title="Show conversation history"
            >
              <History className="w-5 h-5" />
            </button>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 custom-scrollbar">
          
          {/* Conversation History (collapsible) */}
          {showConversationHistory && recentConversation.length > 0 && (
            <div className="space-y-4 pb-4 border-b border-slate-800/50 animate-in slide-in-from-top-2 duration-300">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-[0.2em]">
                <History className="w-3 h-3" />
                Recent Context
              </div>
              <div className="space-y-3">
                {recentConversation.map((turn, idx) => (
                  <ConversationBubble
                    key={idx}
                    speaker={turn.speaker}
                    content={turn.content}
                    isUser={turn.speaker === 'user'}
                    persona={agentPersonas[turn.speaker.toUpperCase()]}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Context Summary */}
          {currentCheckpoint.context_summary && (
            <div className="p-4 rounded-xl bg-slate-900/50 border border-slate-800 text-xs text-slate-400">
              <span className="font-bold text-slate-500">Context: </span>
              {currentCheckpoint.context_summary}
            </div>
          )}

          {/* Main Content */}
          <div className="space-y-6">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-[0.2em]">
              <ClipboardList className="w-3 h-3 text-blue-400" />
              {questions.length > 0 ? 'Questions for You' : 'Information'}
            </div>
            
            {/* Questions or Prompt */}
            {questions.length > 0 ? (
              <div className="space-y-6">
                {questions.map((q, i) => (
                  <div key={q.id} className="space-y-3 animate-in slide-in-from-right-4 duration-500" style={{ animationDelay: `${i * 100}ms` }}>
                    <div className="flex gap-3">
                      <div className="mt-0.5 w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0 border border-blue-500/30">
                        <span className="text-[10px] font-bold text-blue-400">{i+1}</span>
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-semibold text-slate-200 leading-relaxed mb-2">
                          {q.text}
                          {q.required && <span className="text-rose-400 ml-1">*</span>}
                        </p>
                        <textarea 
                          className="w-full bg-slate-900 border border-slate-800 rounded-xl p-4 text-sm focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 outline-none resize-none h-24 text-slate-200 placeholder:text-slate-600 transition-all shadow-inner"
                          placeholder={q.placeholder || "Type your answer here..."}
                          value={questionAnswers[q.id] || ''}
                          onChange={(e) => setQuestionAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="prose prose-invert prose-sm max-w-none bg-slate-900/50 p-6 rounded-2xl border border-slate-800 leading-relaxed text-slate-300 shadow-inner prose-headings:text-blue-400 prose-headings:font-bold prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-hr:border-slate-800 prose-code:text-blue-200 prose-code:bg-blue-500/10 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded">
                <ReactMarkdown>{currentCheckpoint.prompt}</ReactMarkdown>
              </div>
            )}
          </div>

          {/* Smart Suggestions */}
          {currentCheckpoint.suggestions && currentCheckpoint.suggestions.length > 0 && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-[0.2em]">
                <Sparkles className="w-3 h-3 text-yellow-500" />
                Suggestions
              </div>
              <div className="flex flex-wrap gap-2">
                {currentCheckpoint.suggestions.map((suggestion, idx) => (
                  <SuggestionChip 
                    key={idx} 
                    text={suggestion} 
                    onClick={() => handleSuggestionClick(suggestion)} 
                  />
                ))}
              </div>
            </div>
          )}

          {/* General Feedback */}
          <div className="space-y-4 pt-4 border-t border-slate-800/50">
            <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-[0.2em]">
              <MessageSquare className="w-3 h-3" />
              Additional Feedback <span className="text-[10px] lowercase font-normal opacity-50 ml-1">(optional)</span>
            </div>
            <textarea 
              className="w-full bg-slate-950 border border-slate-800 rounded-2xl p-5 text-sm focus:ring-2 focus:ring-orange-500/30 focus:border-orange-500/30 outline-none resize-none h-28 text-slate-200 placeholder:text-slate-700 transition-all shadow-inner"
              placeholder="Any other specific instructions, concerns, or context..."
              value={generalFeedback}
              onChange={(e) => setGeneralFeedback(e.target.value)}
            />
          </div>

          {/* Follow-up Question (if allowed) */}
          {currentCheckpoint.allows_follow_up && (
            <div className="space-y-3 pt-4 border-t border-slate-800/50">
              <div className="flex items-center gap-2 text-xs font-bold text-slate-500 uppercase tracking-[0.2em]">
                <Bot className="w-3 h-3 text-purple-400" />
                Ask {persona?.name || currentCheckpoint.agent.toUpperCase()} a Question
              </div>
              <div className="flex gap-2">
                <input
                  type="text"
                  className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-sm focus:ring-2 focus:ring-purple-500/30 focus:border-purple-500/30 outline-none text-slate-200 placeholder:text-slate-600"
                  placeholder={`Ask ${persona?.name || 'the agent'} for clarification...`}
                  value={followUpMessage}
                  onChange={(e) => setFollowUpMessage(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleFollowUp()}
                />
                <button
                  onClick={handleFollowUp}
                  disabled={!followUpMessage.trim()}
                  className="px-4 py-3 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-all"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
          
          <div ref={conversationEndRef} />
        </div>

        {/* Footer Actions */}
        <div className="p-5 border-t border-slate-800 bg-gradient-to-t from-slate-900/80 to-transparent shrink-0">
          {/* Special rendering for next_steps checkpoints */}
          {currentCheckpoint.is_next_steps && currentCheckpoint.next_step_options ? (
            <div className="space-y-3">
              {currentCheckpoint.next_step_options.map((option) => (
                <NextStepCard
                  key={option.id}
                  option={option}
                  onClick={() => handleNextStepAction(option)}
                />
              ))}
            </div>
          ) : (
            <div className={cn(
              "grid gap-3",
              currentCheckpoint.options.length === 2 ? "grid-cols-2" : 
              currentCheckpoint.options.length === 3 ? "grid-cols-3" : "grid-cols-2"
            )}>
              {currentCheckpoint.options.map((option) => (
                <button
                  key={option}
                  onClick={() => handleDecision(option)}
                  className={cn(
                    "flex items-center justify-center gap-2 px-5 py-4 rounded-2xl font-bold text-sm transition-all duration-200 active:scale-95 border uppercase tracking-wider shadow-lg",
                    getButtonStyles(option)
                  )}
                >
                  {getIcon(option)}
                  {option}
                </button>
              ))}
            </div>
          )}
          <div className="mt-4 text-center">
            <p className="text-[10px] text-slate-600 font-medium">
              {currentCheckpoint.is_next_steps 
                ? 'Choose your next step to continue' 
                : `${persona?.name || 'Agent'} is waiting for your decision to continue`}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
