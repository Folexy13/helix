"use client";

import { useState } from 'react';
import { useHelixStore } from '@/store/helixStore';
import { useHelixSocket } from '@/hooks/useHelixSocket';
import ReactMarkdown from 'react-markdown';
import { CheckCircle2, XCircle, Edit3, MessageSquareWarning, ArrowRight, UserCheck } from 'lucide-react';
import { cn } from '@/lib/utils';

export default function HitlInteractionPanel() {
  const { pendingCheckpoints } = useHelixStore();
  const { sendHitlDecision } = useHelixSocket();
  const [userInput, setUserInput] = useState('');

  if (pendingCheckpoints.length === 0) return null;

  const currentCheckpoint = pendingCheckpoints[0];

  const handleDecision = (decision: string) => {
    sendHitlDecision(currentCheckpoint.id, decision, userInput);
    setUserInput('');
  };

  const renderIcon = (option: string) => {
    switch (option.toLowerCase()) {
      case 'approve': return <CheckCircle2 className="w-4 h-4" />;
      case 'reject': return <XCircle className="w-4 h-4" />;
      case 'edit': return <Edit3 className="w-4 h-4" />;
      default: return <ArrowRight className="w-4 h-4" />;
    }
  };

  const getButtonClass = (option: string) => {
    switch (option.toLowerCase()) {
      case 'approve': return 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-[0_0_15px_rgba(16,185,129,0.2)]';
      case 'reject': return 'bg-rose-600 hover:bg-rose-500 text-white shadow-[0_0_15px_rgba(244,63,94,0.2)]';
      case 'edit': return 'bg-blue-600 hover:bg-blue-500 text-white shadow-[0_0_15px_rgba(59,130,246,0.2)]';
      default: return 'bg-slate-700 hover:bg-slate-600 text-white';
    }
  };

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-orange-500/30 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95 duration-300">
      <div className="bg-orange-500/10 border-b border-orange-500/20 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-orange-500/20 border border-orange-500/30">
            <UserCheck className="text-orange-500 w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-orange-500 tracking-tight">
              Human Intervention Required
            </h3>
            <p className="text-[10px] text-orange-500/70 font-bold uppercase tracking-widest">
              Gate: {currentCheckpoint.gate_type.replace(/_/g, ' ')}
            </p>
          </div>
        </div>
        <div className="px-3 py-1 rounded-full bg-slate-950 border border-white/10 text-[10px] font-bold text-slate-400">
          AGENT: {currentCheckpoint.agent.toUpperCase()}
        </div>
      </div>

      <div className="p-6">
        <div className="prose prose-invert prose-sm max-w-none mb-6 bg-slate-950/50 p-4 rounded-xl border border-white/5 leading-relaxed text-slate-300">
          <ReactMarkdown>{currentCheckpoint.prompt}</ReactMarkdown>
        </div>

        {currentCheckpoint.options.some(opt => ['edit', 'explain', 'feedback'].includes(opt.toLowerCase())) && (
           <div className="mb-6 animate-in fade-in slide-in-from-top-2 duration-500">
               <label className="block text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-2 ml-1">Additional Instructions / Feedback</label>
               <textarea 
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-4 text-sm focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500/50 outline-none resize-none h-28 text-slate-200 placeholder:text-slate-700 transition-all"
                  placeholder="Provide details or specific changes you'd like to see..."
                  value={userInput}
                  onChange={(e) => setUserInput(e.target.value)}
               />
           </div>
        )}

        <div className="flex flex-wrap gap-3">
           {currentCheckpoint.options.map((option) => (
               <button
                 key={option}
                 onClick={() => handleDecision(option)}
                 className={cn(
                   "flex-1 flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-bold text-xs transition-all duration-200 active:scale-95 uppercase tracking-wider",
                   getButtonClass(option)
                 )}
               >
                   {renderIcon(option)}
                   {option}
               </button>
           ))}
        </div>
      </div>
    </div>
  );
}
