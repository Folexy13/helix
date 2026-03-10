"use client";

import { useState, useEffect, useRef } from 'react';
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
  ArrowRight,
  Lightbulb,
  GitPullRequest,
  Eye,
  PenLine,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// Agent avatar component
function AgentAvatar({ persona, size = 'md' }: { persona?: AgentPersona; size?: 'sm' | 'md' | 'lg' }) {
  const sizeClasses = {
    sm: 'w-8 h-8 text-base',
    md: 'w-10 h-10 text-lg',
    lg: 'w-12 h-12 text-xl',
  };
  
  return (
    <div 
      className={cn(
        "rounded-xl flex items-center justify-center font-bold shrink-0 shadow-md",
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

interface HitlInlineCardProps {
  checkpoint: HitlCheckpoint;
  isLatest?: boolean;
}

export default function HitlInlineCard({ checkpoint, isLatest = false }: HitlInlineCardProps) {
  const { agentPersonas } = useHelixStore();
  const { sendHitlDecision, sendUserMessage } = useHelixSocket();
  const router = useRouter();
  
  // Form state
  const [generalFeedback, setGeneralFeedback] = useState('');
  const [questionAnswers, setQuestionAnswers] = useState<Record<string, string>>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isResolved, setIsResolved] = useState(false);
  
  const cardRef = useRef<HTMLDivElement>(null);
  const persona = checkpoint.agent_persona || agentPersonas[checkpoint.agent?.toUpperCase() || ''];

  // Parse questions from checkpoint
  const questions = checkpoint.questions || [];

  // Scroll into view when this is the latest checkpoint
  useEffect(() => {
    if (isLatest && cardRef.current) {
      cardRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [isLatest]);

  const handleDecision = async (decision: string) => {
    setIsSubmitting(true);
    
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
    
    sendHitlDecision(checkpoint.id, decision, finalInput, fieldResponses);
    setIsResolved(true);
    setIsSubmitting(false);
  };

  const handleNextStepAction = (option: NextStepOption) => {
    setIsSubmitting(true);
    sendHitlDecision(checkpoint.id, option.id, `Selected: ${option.label}`, {});
    setIsResolved(true);
    
    // Handle navigation
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
    }
    setIsSubmitting(false);
  };

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'create_pr': return <GitPullRequest className="w-4 h-4" />;
      case 'review_code': return <Eye className="w-4 h-4" />;
      case 'request_changes': return <PenLine className="w-4 h-4" />;
      case 'navigate_pillar2': return <ArrowRight className="w-4 h-4" />;
      default: return <ArrowRight className="w-4 h-4" />;
    }
  };

  // Check if this is a "next steps" checkpoint
  const isNextSteps = (checkpoint as { checkpoint_type?: string }).checkpoint_type === 'next_steps' || 
                      (checkpoint.next_step_options && checkpoint.next_step_options.length > 0);

  if (isResolved) {
    return (
      <div 
        ref={cardRef}
        className="flex gap-3 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl"
      >
        <AgentAvatar persona={persona} size="sm" />
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-emerald-400">{persona?.name || checkpoint.agent}</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            <span className="text-xs text-emerald-400/70">Approved</span>
          </div>
          <p className="text-sm text-slate-400">Decision submitted. Continuing...</p>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={cardRef}
      className={cn(
        "rounded-xl border-2 overflow-hidden transition-all duration-300",
        isLatest 
          ? "border-amber-500/50 bg-gradient-to-br from-slate-800/90 to-slate-900/90 shadow-lg shadow-amber-500/10" 
          : "border-slate-700/50 bg-slate-800/50"
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b border-slate-700/50 bg-slate-800/50">
        <AgentAvatar persona={persona} size="md" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-white">{persona?.name || checkpoint.agent}</span>
            {isLatest && (
              <span className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                <Clock className="w-3 h-3" />
                Waiting for input
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400">{persona?.title || 'AI Agent'}</p>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Agent's Message */}
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown>{checkpoint.prompt}</ReactMarkdown>
        </div>

        {/* Context Summary */}
        {checkpoint.context_summary && (
          <div className="flex items-start gap-2 p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
            <Lightbulb className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
            <p className="text-sm text-blue-200">{checkpoint.context_summary}</p>
          </div>
        )}

        {/* Next Steps Options */}
        {isNextSteps && checkpoint.next_step_options && (
          <div className="space-y-2">
            {checkpoint.next_step_options.map((option) => (
              <button
                key={option.id}
                onClick={() => handleNextStepAction(option)}
                disabled={isSubmitting}
                className={cn(
                  "w-full p-3 rounded-lg text-white text-left transition-all duration-200 flex items-center gap-3 group",
                  "bg-slate-700/50 hover:bg-slate-700 border border-slate-600/50 hover:border-slate-500",
                  isSubmitting && "opacity-50 cursor-not-allowed"
                )}
                style={{ borderLeftColor: option.color, borderLeftWidth: 3 }}
              >
                <div 
                  className="p-2 rounded-lg"
                  style={{ backgroundColor: `${option.color}20` }}
                >
                  {getActionIcon(option.action)}
                </div>
                <div className="flex-1">
                  <div className="font-medium text-sm">{option.label}</div>
                  <div className="text-xs text-slate-400">{option.description}</div>
                </div>
                <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-white group-hover:translate-x-1 transition-all" />
              </button>
            ))}
          </div>
        )}

        {/* Questions */}
        {questions.length > 0 && (
          <div className="space-y-3">
            {questions.map((q) => (
              <div key={q.id} className="space-y-1.5">
                <label className="text-sm font-medium text-slate-300">
                  {q.text}
                  {q.required && <span className="text-rose-400 ml-1">*</span>}
                </label>
                {q.type === 'select' && q.options ? (
                  <select
                    value={questionAnswers[q.id] || ''}
                    onChange={(e) => setQuestionAnswers(prev => ({ ...prev, [q.id]: e.target.value }))}
                    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 outline-none"
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
                    className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 outline-none resize-none h-16"
                  />
                )}
              </div>
            ))}
          </div>
        )}

        {/* General Feedback */}
        {!isNextSteps && (
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              Additional feedback (optional)
            </label>
            <textarea
              value={generalFeedback}
              onChange={(e) => setGeneralFeedback(e.target.value)}
              placeholder="Any specific instructions or concerns..."
              className="w-full bg-slate-900/50 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:ring-2 focus:ring-amber-500/50 focus:border-amber-500/50 outline-none resize-none h-16"
            />
          </div>
        )}
      </div>

      {/* Action Buttons */}
      {!isNextSteps && checkpoint.options && (
        <div className="flex gap-2 p-4 border-t border-slate-700/50 bg-slate-900/30">
          {checkpoint.options.map((option) => {
            const isApprove = option.toLowerCase() === 'approve';
            const isReject = option.toLowerCase() === 'reject';
            const isModify = option.toLowerCase() === 'modify';
            
            return (
              <button
                key={option}
                onClick={() => handleDecision(option)}
                disabled={isSubmitting}
                className={cn(
                  "flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all duration-200 flex items-center justify-center gap-2",
                  isApprove && "bg-emerald-600 hover:bg-emerald-500 text-white",
                  isReject && "bg-rose-600/20 hover:bg-rose-600/30 text-rose-400 border border-rose-600/30",
                  isModify && "bg-amber-600/20 hover:bg-amber-600/30 text-amber-400 border border-amber-600/30",
                  !isApprove && !isReject && !isModify && "bg-slate-700 hover:bg-slate-600 text-white",
                  isSubmitting && "opacity-50 cursor-not-allowed"
                )}
              >
                {isApprove && <CheckCircle2 className="w-4 h-4" />}
                {isReject && <XCircle className="w-4 h-4" />}
                {isModify && <Edit3 className="w-4 h-4" />}
                {isApprove ? 'Approve & Continue' : option.charAt(0).toUpperCase() + option.slice(1)}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
