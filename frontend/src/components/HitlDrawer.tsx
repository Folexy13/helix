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
  ChevronRight,
  MessageSquare,
  Sparkles,
  Send,
  User,
  ArrowRight,
  X,
  Lightbulb,
  GitPullRequest,
  Eye,
  PenLine,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Agent avatar component
function AgentAvatar({ persona, size = 'md' }: { persona?: AgentPersona; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-8 h-8 text-base',
    md: 'w-12 h-12 text-xl',
    lg: 'w-16 h-16 text-2xl',
  };
  
  return (
    <div 
      className={cn(
        "rounded-2xl flex items-center justify-center font-bold shrink-0 shadow-lg",
        sizeClasses[size]
      )}
      style={{ 
        backgroundColor: persona?.color ? `${persona.color}20` : '#64748b20',
        borderColor: persona?.color ? `${persona.color}40` : '#64748b40',
        borderWidth: 2,
      }}
    >
      {persona?.avatar || '🤖'}
    </div>
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
    
    return [];
  }, [currentCheckpoint]);

  // Get recent conversation for context
  const recentConversation = useMemo(() => {
    if (currentCheckpoint?.conversation_history && currentCheckpoint.conversation_history.length > 0) {
      return currentCheckpoint.conversation_history.slice(-5);
    }
    if (conversation && conversation.length > 0) {
      return conversation.slice(-5).map(msg => ({
        speaker: msg.speaker,
        content: msg.content,
      }));
    }
    return [];
  }, [currentCheckpoint, conversation]);

  // Scroll to bottom of conversation
  useEffect(() => {
    conversationEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation]);

  // Reset form when checkpoint changes
  const checkpointId = currentCheckpoint?.id;
  const prevCheckpointIdRef = useRef(checkpointId);
  
  if (checkpointId !== prevCheckpointIdRef.current) {
    prevCheckpointIdRef.current = checkpointId;
  }

  if (!isOpen || !currentCheckpoint) return null;

  const handleDecision = (decision: string) => {
    const fieldResponses: Record<string, string> = {};
    
    questions.forEach((q) => {
      fieldResponses[q.id] = questionAnswers[q.id] || '';
    });
    
    let finalInput = "";
    
    if (questions.length > 0) {
      finalInput += "--- ANSWERS ---\n";
      questions.forEach((q) => {
        const answer = questionAnswers[q.id] || "No answer provided.";
        finalInput += `${q.text}: ${answer}\n`;
      });
      finalInput += "---\n";
    }
    
    if (generalFeedback.trim()) {
      finalInput += `\nFeedback: ${generalFeedback}`;
    }
    
    sendHitlDecision(currentCheckpoint.id, decision, finalInput, fieldResponses);
    
    // Reset form
    setGeneralFeedback('');
    setQuestionAnswers({});
    setFollowUpMessage('');
  };

  const handleFollowUp = () => {
    if (followUpMessage.trim()) {
      sendUserMessage(followUpMessage, currentCheckpoint.agent);
      setFollowUpMessage('');
    }
  };

  const handleNextStepAction = (option: NextStepOption) => {
    sendHitlDecision(currentCheckpoint.id, option.id, `Selected: ${option.label}`, {});
    
    switch (option.action) {
      case 'navigate_pillar2':
        router.push('/pillar2');
        break;
      case 'restart_pillar1':
        router.push('/pillar1');
        break;
      case 'save_and_exit':
        router.push('/');
        break;
      case 'create_pr':
        router.push('/pillar3');
        break;
      case 'review_code':
      case 'request_changes':
        break;
      default:
        console.log('Unknown action:', option.action);
    }
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'create_pr': return <GitPullRequest className="w-5 h-5" />;
      case 'review_code': return <Eye className="w-5 h-5" />;
      case 'request_changes': return <PenLine className="w-5 h-5" />;
      default: return <ArrowRight className="w-5 h-5" />;
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'create_pr': return 'from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600';
      case 'review_code': return 'from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600';
      case 'request_changes': return 'from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600';
      default: return 'from-purple-600 to-purple-700 hover:from-purple-500 hover:to-purple-600';
    }
  };

  // Check if this is a "next steps" checkpoint
  const isNextSteps = (currentCheckpoint as { checkpoint_type?: string }).checkpoint_type === 'next_steps' || 
                      (currentCheckpoint.next_step_options && currentCheckpoint.next_step_options.length > 0);

  return (
    <>
      {/* Backdrop - subtle, doesn't block interaction */}
      <div 
        className={cn(
          "fixed inset-0 z-40 bg-black/20 transition-opacity duration-300",
          isOpen ? "opacity-100" : "opacity-0 pointer-events-none"
        )}
        onClick={() => {}} // Don't close on backdrop click
      />

      {/* Drawer Panel */}
      <div className={cn(
        "fixed top-0 right-0 h-full w-[420px] z-50 bg-gradient-to-b from-slate-900 to-slate-950 border-l border-slate-700/50 shadow-2xl transition-transform duration-300 ease-out flex flex-col",
        isOpen ? "translate-x-0" : "translate-x-full"
      )}>
        {/* Header */}
        <div className="p-5 border-b border-slate-800 bg-slate-900/80 backdrop-blur-sm">
          <div className="flex items-start gap-4">
            <AgentAvatar persona={persona} size="md" />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white">
                  {persona?.name || currentCheckpoint.agent}
                </h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                  Needs Input
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-0.5">
                {persona?.title || 'AI Agent'}
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Agent's Message */}
          <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700/50">
            <div className="prose prose-invert prose-sm max-w-none">
              <ReactMarkdown>{currentCheckpoint.prompt}</ReactMarkdown>
            </div>
          </div>

          {/* Context Summary */}
          {currentCheckpoint.context_summary && (
            <div className="bg-blue-500/10 rounded-xl p-4 border border-blue-500/20">
              <div className="flex items-center gap-2 mb-2">
                <Lightbulb className="w-4 h-4 text-blue-400" />
                <span className="text-xs font-semibold text-blue-400 uppercase tracking-wider">Context</span>
              </div>
              <p className="text-sm text-blue-200">{currentCheckpoint.context_summary}</p>
            </div>
          )}

          {/* Next Steps Options */}
          {isNextSteps && currentCheckpoint.next_step_options && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                Choose Your Next Step
              </h3>
              {currentCheckpoint.next_step_options.map((option) => (
                <button
                  key={option.id}
                  onClick={() => handleNextStepAction(option)}
                  className={cn(
                    "w-full p-4 rounded-xl bg-gradient-to-r text-white text-left transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-[1.02] group",
                    getActionColor(option.action)
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-white/10">
                      {getActionIcon(option.action)}
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold">{option.label}</div>
                      <div className="text-sm opacity-80">{option.description}</div>
                    </div>
                    <ChevronRight className="w-5 h-5 opacity-50 group-hover:opacity-100 group-hover:translate-x-1 transition-all" />
                  </div>
                </button>
              ))}
            </div>
          )}

          {/* Questions */}
          {questions.length > 0 && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                Please Answer
              </h3>
              {questions.map((q) => (
                <div key={q.id} className="space-y-2">
                  <label className="text-sm font-medium text-slate-300">
                    {q.text}
                    {q.required && <span className="text-rose-400 ml-1">*</span>}
                  </label>
                  {q.type === 'select' && q.options ? (
                    <select
                      value={questionAnswers[q.id] || ''}
                      onChange={(e) => setQuestionAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none"
                    >
                      <option value="">Select an option...</option>
                      {q.options.map((opt) => (
                        <option key={opt} value={opt}>{opt}</option>
                      ))}
                    </select>
                  ) : (
                    <textarea
                      value={questionAnswers[q.id] || ''}
                      onChange={(e) => setQuestionAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                      placeholder={q.placeholder || 'Your answer...'}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none resize-none h-20"
                    />
                  )}
                </div>
              ))}
            </div>
          )}

          {/* General Feedback */}
          {!isNextSteps && (
            <div className="space-y-2">
              <label className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
                Additional Feedback
              </label>
              <textarea
                value={generalFeedback}
                onChange={(e) => setGeneralFeedback(e.target.value)}
                placeholder="Any specific instructions, concerns, or context..."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-3 text-sm text-white placeholder:text-slate-500 focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none resize-none h-24"
              />
            </div>
          )}

          {/* Ask a Question */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Ask for Clarification
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={followUpMessage}
                onChange={(e) => setFollowUpMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleFollowUp()}
                placeholder="Ask a question..."
                className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500/50 outline-none"
              />
              <button
                onClick={handleFollowUp}
                disabled={!followUpMessage.trim()}
                className="p-2.5 rounded-lg bg-purple-600 hover:bg-purple-500 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div ref={conversationEndRef} />
        </div>

        {/* Action Buttons */}
        {!isNextSteps && currentCheckpoint.options && (
          <div className="p-5 border-t border-slate-800 bg-slate-900/80 backdrop-blur-sm">
            <div className="flex gap-3">
              {currentCheckpoint.options.map((option) => {
                const isApprove = option.toLowerCase() === 'approve';
                const isReject = option.toLowerCase() === 'reject';
                const isEdit = option.toLowerCase() === 'edit';
                
                return (
                  <button
                    key={option}
                    onClick={() => handleDecision(option)}
                    className={cn(
                      "flex-1 py-3 px-4 rounded-xl font-semibold text-sm transition-all duration-200 flex items-center justify-center gap-2",
                      isApprove && "bg-gradient-to-r from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 text-white shadow-lg shadow-emerald-900/30",
                      isReject && "bg-gradient-to-r from-rose-600 to-rose-700 hover:from-rose-500 hover:to-rose-600 text-white shadow-lg shadow-rose-900/30",
                      isEdit && "bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white shadow-lg shadow-blue-900/30",
                      !isApprove && !isReject && !isEdit && "bg-slate-700 hover:bg-slate-600 text-white"
                    )}
                  >
                    {isApprove && <CheckCircle2 className="w-4 h-4" />}
                    {isReject && <XCircle className="w-4 h-4" />}
                    {isEdit && <Edit3 className="w-4 h-4" />}
                    {option}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
